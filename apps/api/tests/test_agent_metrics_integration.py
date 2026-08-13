import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.metrics import build_metrics
from cataloging_api.agent.service import create_conversation
from cataloging_api.db.models import AgentMessage, AgentMessageRole, AgentTurnError
from cataloging_api.db.session import engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_metrics_aggregates_tokens_tools_latency_and_errors() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        conversation = await create_conversation(
            session, started_by="Catalogadora", collection_uuid=uuid.uuid4()
        )
        session.add(
            AgentMessage(
                conversation_id=conversation.conversation_id,
                role=AgentMessageRole.user,
                content="¿Qué cobertura tiene la familia lingüística?",
            )
        )
        session.add(
            AgentMessage(
                conversation_id=conversation.conversation_id,
                role=AgentMessageRole.assistant,
                content="62% de cobertura.",
                tool_calls=[
                    {"tool": "get_catalog_profile", "input": {}},
                    {"tool": "get_catalog_profile", "input": {}},
                ],
                usage={"input_tokens": 100, "output_tokens": 40},
                latency_ms=250,
            )
        )
        session.add(
            AgentMessage(
                conversation_id=conversation.conversation_id,
                role=AgentMessageRole.assistant,
                content="Otra respuesta.",
                tool_calls=[{"tool": "search_items", "input": {}}],
                usage={"input_tokens": 50, "output_tokens": 20},
                latency_ms=150,
            )
        )
        session.add(
            AgentTurnError(conversation_id=conversation.conversation_id, detail="fallo simulado")
        )
        await session.commit()

        metrics = await build_metrics(session)

        assert metrics["total_conversations"] >= 1
        assert metrics["conversations_by_status"]["open"] >= 1
        assert metrics["total_messages"] >= 3
        assert metrics["messages_by_role"]["assistant"] >= 2
        assert metrics["messages_by_role"]["user"] >= 1
        assert metrics["tool_calls_by_tool"]["get_catalog_profile"] >= 2
        assert metrics["tool_calls_by_tool"]["search_items"] >= 1
        assert metrics["total_input_tokens"] >= 150
        assert metrics["total_output_tokens"] >= 60
        assert metrics["avg_first_chunk_latency_ms"] is not None
        assert metrics["turn_error_count"] >= 1
        assert metrics["turn_error_rate"] is not None
        assert 0 < metrics["turn_error_rate"] <= 1
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_metrics_never_divides_by_zero() -> None:
    """Averages must degrade to None rather than raising, whatever data already
    exists in the database — this doesn't assume an empty table."""
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        metrics = await build_metrics(session)

        assert metrics["total_conversations"] >= 0
        if metrics["total_conversations"] == 0:
            assert metrics["avg_messages_per_conversation"] is None
        else:
            assert metrics["avg_messages_per_conversation"] is None or (
                metrics["avg_messages_per_conversation"] >= 0
            )
        assert metrics["turn_error_rate"] is None or 0 <= metrics["turn_error_rate"] <= 1
        latency = metrics["avg_first_chunk_latency_ms"]
        assert latency is None or latency >= 0
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
