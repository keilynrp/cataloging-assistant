import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.agent.constants import (
    MAX_MESSAGES_PER_CONVERSATION,
    MAX_TOOL_CALLS_PER_TURN,
    MAX_TOOL_RESULT_CHARS,
    SYSTEM_PROMPT,
)
from cataloging_api.agent.provider import AgentProvider, TextDelta, TurnDone
from cataloging_api.agent.tools import TOOLS_BY_NAME, tool_schemas
from cataloging_api.db.models import AgentConversation, AgentMessage, AgentMessageRole


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


def _history_as_wire_messages(messages: list[AgentMessage]) -> list[dict[str, Any]]:
    return [{"role": message.role.value, "content": message.content} for message in messages]


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
    provider: AgentProvider,
) -> AsyncIterator[dict[str, Any]]:
    """Runs one turn of the conversation, yielding SSE-ready event dicts.

    The user message is persisted before the provider is ever called (flow
    step 1 of VERTICAL-015), so a provider failure never loses it. The
    assistant message is only persisted once the turn finishes successfully.
    """
    conversation = await get_conversation(session, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError
    if len(conversation.messages) >= MAX_MESSAGES_PER_CONVERSATION:
        raise ConversationLimitExceededError

    history = _history_as_wire_messages(conversation.messages)

    user_message = AgentMessage(
        conversation_id=conversation_id,
        role=AgentMessageRole.user,
        content=content.strip(),
    )
    session.add(user_message)
    await session.flush()
    await session.commit()

    messages: list[dict[str, Any]] = [*history, {"role": "user", "content": content.strip()}]
    tools = tool_schemas()

    tool_calls_log: list[dict[str, Any]] = []
    citations: list[dict[str, str]] = []
    text_parts: list[str] = []
    total_input_tokens = 0
    total_output_tokens = 0
    calls_made = 0

    try:
        while True:
            done: TurnDone | None = None
            async for event in provider.stream_step(
                system=SYSTEM_PROMPT, messages=messages, tools=tools
            ):
                if isinstance(event, TextDelta):
                    text_parts.append(event.text)
                    yield {"event": "text_delta", "data": {"text": event.text}}
                elif isinstance(event, TurnDone):
                    done = event
            assert done is not None
            total_input_tokens += done.usage["input_tokens"]
            total_output_tokens += done.usage["output_tokens"]

            tool_use_blocks = [block for block in done.content_blocks if block.type == "tool_use"]
            if not tool_use_blocks or done.stop_reason != "tool_use":
                break
            if calls_made + len(tool_use_blocks) > MAX_TOOL_CALLS_PER_TURN:
                text_parts.append(
                    "\n\n(Se alcanzó el límite de consultas a herramientas para este turno.)"
                )
                break

            messages.append({"role": "assistant", "content": done.content_blocks})
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                calls_made += 1
                spec = TOOLS_BY_NAME.get(block.name)
                yield {
                    "event": "tool_call",
                    "data": {"tool": block.name, "input": dict(block.input)},
                }
                if spec is None:
                    result_output: dict[str, Any] = {"error": "herramienta desconocida"}
                    result_citations: list[dict[str, str]] = []
                else:
                    result = await spec.handler(session, dict(block.input))
                    result_output = result.output
                    result_citations = result.citations
                tool_calls_log.append({"tool": block.name, "input": dict(block.input)})
                citations.extend(result_citations)
                serialized = json.dumps(result_output, ensure_ascii=False, default=str)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": serialized[:MAX_TOOL_RESULT_CHARS],
                    }
                )
            messages.append({"role": "user", "content": tool_results})
    except Exception as error:  # noqa: BLE001 - surfaced to the client, not swallowed
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
