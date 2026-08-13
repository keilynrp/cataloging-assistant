import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.constants import MAX_MESSAGES_PER_CONVERSATION
from cataloging_api.agent.providers.base import (
    TextDelta,
    ToolCallEvent,
    ToolCallRequested,
    TurnFinished,
)
from cataloging_api.agent.service import (
    ConversationLimitExceededError,
    ConversationNotFoundError,
    create_conversation,
    list_conversations,
    stream_message,
)
from cataloging_api.db.models import AgentMessage, AgentMessageRole, AgentTurnError
from cataloging_api.db.session import engine


class FakeProviderTurn:
    """Duck-types ProviderTurn without touching a real SDK or network."""

    def __init__(self, steps: list[list[object]]) -> None:
        self._steps = steps
        self._call_index = 0

    def _next_step(self) -> list[object]:
        step = self._steps[self._call_index]
        self._call_index += 1
        return step

    async def start(self, *, system, history, user_content, tools) -> AsyncIterator[object]:  # noqa: ANN001
        for event in self._next_step():
            yield event

    async def continue_with_tool_results(self, results) -> AsyncIterator[object]:  # noqa: ANN001
        for event in self._next_step():
            yield event


class FakeProvider:
    def __init__(self, steps: list[list[object]]) -> None:
        self._steps = steps
        self.model = "fake-model"

    def new_turn(self) -> FakeProviderTurn:
        return FakeProviderTurn(self._steps)


class FailingProviderTurn:
    async def start(self, *, system, history, user_content, tools) -> AsyncIterator[object]:  # noqa: ANN001
        raise RuntimeError("proveedor no disponible")
        yield  # pragma: no cover - makes this an async generator

    async def continue_with_tool_results(self, results) -> AsyncIterator[object]:  # noqa: ANN001
        raise RuntimeError("proveedor no disponible")
        yield  # pragma: no cover - makes this an async generator


class FailingProvider:
    model = "fake-model"

    def new_turn(self) -> FailingProviderTurn:
        return FailingProviderTurn()


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
                    ToolCallEvent(
                        call=ToolCallRequested(
                            call_id="toolu_1",
                            name="search_items",
                            input={"q": "no debería importar"},
                        )
                    ),
                    TurnFinished(
                        stop_reason="tool_use", usage={"input_tokens": 12, "output_tokens": 4}
                    ),
                ],
                [
                    TextDelta(text="No encontré"),
                    TextDelta(text=" ítems con ese nombre."),
                    TurnFinished(
                        stop_reason="end_turn", usage={"input_tokens": 20, "output_tokens": 8}
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
        assert isinstance(assistant.latency_ms, int)
        assert assistant.latency_ms >= 0
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

        errors = list(
            await session.scalars(
                select(AgentTurnError).where(
                    AgentTurnError.conversation_id == conversation.conversation_id
                )
            )
        )
        assert len(errors) == 1
        assert "proveedor no disponible" in errors[0].detail
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_conversations_orders_by_most_recent_activity() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        quiet = await create_conversation(
            session, started_by="Sin mensajes", collection_uuid=uuid.uuid4()
        )
        active = await create_conversation(
            session, started_by="Con actividad", collection_uuid=uuid.uuid4()
        )
        # PostgreSQL's now() is fixed for the whole transaction, so relying on
        # server_default=func.now() here would make started_at/created_at tie
        # across every row in this test — pin explicit, strictly increasing
        # Python-side timestamps instead so the ordering assertion is real.
        session.add(
            AgentMessage(
                conversation_id=active.conversation_id,
                role=AgentMessageRole.user,
                content="hola",
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            AgentMessage(
                conversation_id=active.conversation_id,
                role=AgentMessageRole.assistant,
                content="hola de vuelta",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()

        summaries = await list_conversations(session)
        by_id = {summary.conversation.conversation_id: summary for summary in summaries}

        assert by_id[active.conversation_id].message_count == 2
        assert by_id[active.conversation_id].last_message_at is not None
        assert by_id[quiet.conversation_id].message_count == 0
        assert by_id[quiet.conversation_id].last_message_at is None
        assert summaries[0].conversation.conversation_id == active.conversation_id
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
