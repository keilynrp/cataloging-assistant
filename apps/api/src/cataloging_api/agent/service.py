import json
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.agent.constants import (
    MAX_MESSAGES_PER_CONVERSATION,
    MAX_TOOL_CALLS_PER_TURN,
    MAX_TOOL_RESULT_CHARS,
    SYSTEM_PROMPT,
)
from cataloging_api.agent.providers.base import (
    PlainMessage,
    Provider,
    TextDelta,
    ToolCallEvent,
    ToolCallResultPayload,
    TurnFinished,
)
from cataloging_api.agent.tools import TOOLS_BY_NAME, tool_schemas
from cataloging_api.db.models import (
    AgentConversation,
    AgentMessage,
    AgentMessageRole,
    AgentTurnError,
)


class ConversationNotFoundError(Exception):
    pass


class ConversationLimitExceededError(Exception):
    pass


async def create_conversation(
    session: AsyncSession, *, started_by: str, collection_uuid: uuid.UUID
) -> AgentConversation:
    conversation = AgentConversation(collection_uuid=collection_uuid, started_by=started_by.strip())
    session.add(conversation)
    await session.flush()
    return conversation


async def get_conversation(
    session: AsyncSession, conversation_id: uuid.UUID
) -> AgentConversation | None:
    return await session.scalar(
        select(AgentConversation)
        .where(AgentConversation.conversation_id == conversation_id)
        .options(selectinload(AgentConversation.messages))
    )


@dataclass(frozen=True)
class ConversationSummary:
    conversation: AgentConversation
    message_count: int
    last_message_at: Any


async def list_conversations(
    session: AsyncSession, *, limit: int = 20
) -> list[ConversationSummary]:
    """Most recently active conversations first (AGT-007), for the resume list."""
    message_count = func.count(AgentMessage.message_id)
    last_message_at = func.max(AgentMessage.created_at)
    rows = (
        await session.execute(
            select(AgentConversation, message_count, last_message_at)
            .outerjoin(
                AgentMessage, AgentMessage.conversation_id == AgentConversation.conversation_id
            )
            .group_by(AgentConversation.conversation_id)
            .order_by(func.coalesce(last_message_at, AgentConversation.started_at).desc())
            .limit(limit)
        )
    ).all()
    return [
        ConversationSummary(conversation=conversation, message_count=count, last_message_at=last)
        for conversation, count, last in rows
    ]


def _history_as_plain_messages(messages: list[AgentMessage]) -> list[PlainMessage]:
    return [PlainMessage(role=message.role.value, content=message.content) for message in messages]


def _dedupe_citations(citations: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for citation in citations:
        key = (citation.get("label", ""), citation.get("target_path", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(citation)
    return result


async def stream_message(
    session: AsyncSession,
    *,
    conversation_id: uuid.UUID,
    content: str,
    provider: Provider,
) -> AsyncIterator[dict[str, Any]]:
    """Runs one turn of the conversation, yielding SSE-ready event dicts.

    The user message is persisted before the provider is ever called (flow
    step 1 of VERTICAL-015), so a provider failure never loses it. The
    assistant message is only persisted once the turn finishes successfully.

    Delegates the actual model call to a `ProviderTurn` (ADR-011): this
    function only ever sees the provider-agnostic event types from
    `agent.providers.base`, never a specific SDK's wire format.
    """
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError
    if len(conversation.messages) >= MAX_MESSAGES_PER_CONVERSATION:
        raise ConversationLimitExceededError

    history = _history_as_plain_messages(conversation.messages)

    user_message = AgentMessage(
        conversation_id=conversation_id,
        role=AgentMessageRole.user,
        content=content.strip(),
    )
    session.add(user_message)
    await session.flush()
    await session.commit()

    tools = tool_schemas()
    turn = provider.new_turn()

    tool_calls_log: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []
    text_parts: list[str] = []
    total_input_tokens = 0
    total_output_tokens = 0
    calls_made = 0
    turn_started_at = time.monotonic()
    first_chunk_latency_ms: int | None = None

    try:
        events = turn.start(
            system=SYSTEM_PROMPT, history=history, user_content=content.strip(), tools=tools
        )
        while True:
            finished: TurnFinished | None = None
            pending_calls: list[ToolCallEvent] = []
            async for event in events:
                if first_chunk_latency_ms is None:
                    first_chunk_latency_ms = round((time.monotonic() - turn_started_at) * 1000)
                if isinstance(event, TextDelta):
                    text_parts.append(event.text)
                    yield {"event": "text_delta", "data": {"text": event.text}}
                elif isinstance(event, ToolCallEvent):
                    pending_calls.append(event)
                elif isinstance(event, TurnFinished):
                    finished = event
            assert finished is not None
            total_input_tokens += finished.usage["input_tokens"]
            total_output_tokens += finished.usage["output_tokens"]

            if not pending_calls or finished.stop_reason != "tool_use":
                break
            if calls_made + len(pending_calls) > MAX_TOOL_CALLS_PER_TURN:
                text_parts.append(
                    "\n\n(Se alcanzó el límite de consultas a herramientas para este turno.)"
                )
                break

            tool_results: list[ToolCallResultPayload] = []
            for pending in pending_calls:
                call = pending.call
                calls_made += 1
                spec = TOOLS_BY_NAME.get(call.name)
                yield {
                    "event": "tool_call",
                    "data": {"tool": call.name, "input": call.input},
                }
                if spec is None:
                    result_output: dict[str, Any] = {"error": "herramienta desconocida"}
                    result_citations: list[dict[str, str]] = []
                else:
                    result = await spec.handler(session, call.input)
                    result_output = result.output
                    result_citations = result.citations
                tool_calls_log.append({"tool": call.name, "input": call.input})
                citations.extend(result_citations)
                serialized = json.dumps(result_output, ensure_ascii=False, default=str)
                tool_results.append(
                    ToolCallResultPayload(
                        call_id=call.call_id,
                        name=call.name,
                        output=serialized[:MAX_TOOL_RESULT_CHARS],
                    )
                )
            events = turn.continue_with_tool_results(tool_results)
    except Exception as error:  # noqa: BLE001 - surfaced to the client, not swallowed
        session.add(AgentTurnError(conversation_id=conversation_id, detail=str(error)[:4000]))
        await session.commit()
        yield {"event": "error", "data": {"detail": str(error)}}
        return

    final_text = "".join(text_parts).strip()
    deduped_citations = _dedupe_citations(citations)
    assistant_message = AgentMessage(
        conversation_id=conversation_id,
        role=AgentMessageRole.assistant,
        content=final_text,
        tool_calls=tool_calls_log,
        citations=deduped_citations,
        model=provider.model,
        usage={"input_tokens": total_input_tokens, "output_tokens": total_output_tokens},
        latency_ms=first_chunk_latency_ms,
    )
    session.add(assistant_message)
    await session.flush()
    await session.commit()

    yield {
        "event": "done",
        "data": {
            "message_id": str(assistant_message.message_id),
            "content": final_text,
            "citations": deduped_citations,
        },
    }
