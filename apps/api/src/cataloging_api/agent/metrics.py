from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    AgentConversation,
    AgentMessage,
    AgentMessageRole,
    AgentTurnError,
)


async def build_metrics(session: AsyncSession) -> dict[str, object]:
    """Operational counters from VERTICAL-015's Observabilidad section (AGT-008)."""
    conversations_by_status = {
        str(status): count
        for status, count in (
            await session.execute(
                select(AgentConversation.status, func.count()).group_by(AgentConversation.status)
            )
        ).all()
    }
    total_conversations = sum(conversations_by_status.values())

    messages_by_role = {
        str(role): count
        for role, count in (
            await session.execute(
                select(AgentMessage.role, func.count()).group_by(AgentMessage.role)
            )
        ).all()
    }
    total_messages = sum(messages_by_role.values())

    assistant_rows = (
        await session.execute(
            select(AgentMessage.tool_calls, AgentMessage.usage, AgentMessage.latency_ms).where(
                AgentMessage.role == AgentMessageRole.assistant
            )
        )
    ).all()

    tool_calls_by_tool: dict[str, int] = {}
    total_input_tokens = 0
    total_output_tokens = 0
    latencies: list[int] = []
    for tool_calls, usage, latency_ms in assistant_rows:
        for call in tool_calls or []:
            name = call.get("tool")
            if name:
                tool_calls_by_tool[name] = tool_calls_by_tool.get(name, 0) + 1
        if usage:
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
        if latency_ms is not None:
            latencies.append(latency_ms)

    turn_error_count = (await session.scalar(select(func.count()).select_from(AgentTurnError))) or 0
    completed_turns = len(assistant_rows)
    total_turns = completed_turns + turn_error_count

    return {
        "total_conversations": total_conversations,
        "conversations_by_status": conversations_by_status,
        "total_messages": total_messages,
        "messages_by_role": messages_by_role,
        "avg_messages_per_conversation": (
            total_messages / total_conversations if total_conversations else None
        ),
        "tool_calls_by_tool": tool_calls_by_tool,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "avg_first_chunk_latency_ms": (
            round(sum(latencies) / len(latencies)) if latencies else None
        ),
        "turn_error_count": turn_error_count,
        "turn_error_rate": (turn_error_count / total_turns if total_turns else None),
    }
