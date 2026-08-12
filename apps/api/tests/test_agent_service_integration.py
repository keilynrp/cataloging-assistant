import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.constants import MAX_MESSAGES_PER_CONVERSATION
from cataloging_api.agent.provider import TextDelta, TurnDone
from cataloging_api.agent.service import (
    ConversationLimitExceededError,
    ConversationNotFoundError,
    create_conversation,
    stream_message,
)
from cataloging_api.db.models import AgentMessage, AgentMessageRole
from cataloging_api.db.session import engine


class FakeProvider:
    """Duck-types AgentProvider without touching the real SDK or network."""

    def __init__(self, steps: list[list[object]]) -> None:
        self._steps = steps
        self._call_index = 0
        self.model = "fake-model"

    async def stream_step(self, *, system, messages, tools) -> AsyncIterator[object]:  # noqa: ANN001
        step = self._steps[self._call_index]
        self._call_index += 1
        for event in step:
            yield event


class FailingProvider:
    model = "fake-model"

    async def stream_step(self, *, system, messages, tools) -> AsyncIterator[object]:  # noqa: ANN001
        raise RuntimeError("proveedor no disponible")
        yield  # pragma: no cover - makes this an async generator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_message_runs_a_tool_and_persists_the_answer() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        conversation = await create_conversation(
            session, started_by="Catalogadora", collection_uuid=uuid.uuid4()
        )
        await session.commit()

        provider = FakeProvider(
            [
                [
                    TurnDone(
                        content_blocks=[
                            SimpleNamespace(
                                type="tool_use",
                                id="toolu_1",
                                name="search_items",
                                input={"q": "no debería importar"},
                            )
                        ],
                        stop_reason="tool_use",
                        usage={"input_tokens": 12, "output_tokens": 4},
                    )
                ],
                [
                    TextDelta(text="No encontré"),
                    TextDelta(text=" ítems con ese nombre."),
                    TurnDone(
                        content_blocks=[
                            SimpleNamespace(type="text", text="No encontré ítems con ese nombre.")
                        ],
                        stop_reason="end_turn",
                        usage={"input_tokens": 20, "output_tokens": 8},
                    ),
                ],
            ]
        )

        events = [
            event
            async for event in stream_message(
                session,
                conversation_id=conversation.conversation_id,
                content="¿Hay ítems llamados 'no debería importar'?",
                provider=provider,
            )
        ]

        event_names = [event["event"] for event in events]
        assert event_names == ["tool_call", "text_delta", "text_delta", "done"]
        assert events[0]["data"]["tool"] == "search_items"

        done_event = events[-1]
        assert done_event["data"]["content"] == "No encontré ítems con ese nombre."

        messages = list(
            await session.scalars(
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conversation.conversation_id)
                .order_by(AgentMessage.created_at)
            )
        )
        assert [m.role for m in messages] == [AgentMessageRole.user, AgentMessageRole.assistant]
        assistant = messages[1]
        assert assistant.content == "No encontré ítems con ese nombre."
        assert assistant.model == "fake-model"
        assert assistant.tool_calls == [
            {"tool": "search_items", "input": {"q": "no debería importar"}}
        ]
        assert assistant.usage == {"input_tokens": 32, "output_tokens": 12}
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_message_survives_a_provider_failure() -> None:
    """A provider failure must not lose the user's message (VERTICAL-015
    acceptance criterion 3), and must not persist a broken assistant reply."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        conversation = await create_conversation(
            session, started_by="Catalogador", collection_uuid=uuid.uuid4()
        )
        await session.commit()

        events = [
            event
            async for event in stream_message(
                session,
                conversation_id=conversation.conversation_id,
                content="¿Cuál es la cobertura de idioma?",
                provider=FailingProvider(),
            )
        ]

        assert [event["event"] for event in events] == ["error"]

        messages = list(
            await session.scalars(
                select(AgentMessage).where(
                    AgentMessage.conversation_id == conversation.conversation_id
                )
            )
        )
        assert len(messages) == 1
        assert messages[0].role == AgentMessageRole.user
        assert messages[0].content == "¿Cuál es la cobertura de idioma?"
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_message_rejects_unknown_conversation() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        with pytest.raises(ConversationNotFoundError):
            async for _ in stream_message(
                session,
                conversation_id=uuid.uuid4(),
                content="hola",
                provider=FakeProvider([]),
            ):
                pass
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stream_message_enforces_the_conversation_message_cap() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        conversation = await create_conversation(
            session, started_by="Catalogadora", collection_uuid=uuid.uuid4()
        )
        for index in range(MAX_MESSAGES_PER_CONVERSATION):
            session.add(
                AgentMessage(
                    conversation_id=conversation.conversation_id,
                    role=AgentMessageRole.user if index % 2 == 0 else AgentMessageRole.assistant,
                    content=f"mensaje {index}",
                )
            )
        await session.commit()

        with pytest.raises(ConversationLimitExceededError):
            async for _ in stream_message(
                session,
                conversation_id=conversation.conversation_id,
                content="uno más",
                provider=FakeProvider([]),
            ):
                pass
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
