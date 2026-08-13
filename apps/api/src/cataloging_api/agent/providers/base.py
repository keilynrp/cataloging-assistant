"""Provider-agnostic contract for the agent's tool-use loop (ADR-011).

`cataloging_api/agent/service.py` only ever sees the types defined here. Each
concrete provider (`anthropic_provider.py`, `openai_provider.py`) translates
its own SDK's wire format — including how a follow-up turn re-encodes prior
tool calls and results, which differs structurally between providers — into
this shared shape, and owns that state internally behind `ProviderTurn`.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PlainMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ToolCallRequested:
    call_id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class ToolCallResultPayload:
    call_id: str
    name: str
    output: str


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolCallEvent:
    call: ToolCallRequested


@dataclass(frozen=True)
class TurnFinished:
    stop_reason: str  # "tool_use" | "end_turn"
    usage: dict[str, int]


ProviderEvent = TextDelta | ToolCallEvent | TurnFinished


class ProviderTurn(Protocol):
    def start(
        self,
        *,
        system: str,
        history: list[PlainMessage],
        user_content: str,
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[ProviderEvent]: ...

    def continue_with_tool_results(
        self, results: list[ToolCallResultPayload]
    ) -> AsyncIterator[ProviderEvent]: ...


class Provider(Protocol):
    name: str
    model: str

    def new_turn(self) -> ProviderTurn: ...
