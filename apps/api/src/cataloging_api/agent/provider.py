"""The only module in this repository allowed to import the model provider SDK.

ADR-010 requires the integration to stay isolated behind a small interface so
a future provider change touches only this file.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import anthropic

from cataloging_api.agent.constants import MAX_RESPONSE_TOKENS


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class TurnDone:
    content_blocks: list[Any]
    stop_reason: str
    usage: dict[str, int]


class AgentProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def stream_step(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[TextDelta | TurnDone]:
        """Runs exactly one model turn: streams text as it arrives, then
        yields a single TurnDone with the raw content blocks (needed verbatim
        to echo back as the next assistant turn if the model requested a
        tool) and usage. Does not execute tools or loop — the caller owns
        the tool-call cap and the loop, per VERTICAL-015's flow."""
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=system,
            messages=messages,
            tools=tools,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield TextDelta(text=event.delta.text)
            final = await stream.get_final_message()

        yield TurnDone(
            content_blocks=list(final.content),
            stop_reason=final.stop_reason or "end_turn",
            usage={
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            },
        )
