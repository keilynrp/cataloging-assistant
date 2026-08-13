from collections.abc import AsyncIterator
from typing import Any

import anthropic

from cataloging_api.agent.constants import MAX_RESPONSE_TOKENS
from cataloging_api.agent.providers.base import (
    PlainMessage,
    ProviderEvent,
    TextDelta,
    ToolCallEvent,
    ToolCallRequested,
    ToolCallResultPayload,
    TurnFinished,
)


class AnthropicProviderTurn:
    def __init__(self, client: anthropic.AsyncAnthropic, model: str) -> None:
        self._client = client
        self._model = model
        self._system = ""
        self._messages: list[dict[str, Any]] = []
        self._tools: list[dict[str, Any]] = []

    async def start(
        self,
        *,
        system: str,
        history: list[PlainMessage],
        user_content: str,
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[ProviderEvent]:
        self._system = system
        self._tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in tools
        ]
        self._messages = [{"role": m.role, "content": m.content} for m in history]
        self._messages.append({"role": "user", "content": user_content})
        async for event in self._step():
            yield event

    async def continue_with_tool_results(
        self, results: list[ToolCallResultPayload]
    ) -> AsyncIterator[ProviderEvent]:
        self._messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": result.call_id, "content": result.output}
                    for result in results
                ],
            }
        )
        async for event in self._step():
            yield event

    async def _step(self) -> AsyncIterator[ProviderEvent]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=self._system,
            messages=self._messages,
            tools=self._tools,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield TextDelta(text=event.delta.text)
            final = await stream.get_final_message()

        self._messages.append({"role": "assistant", "content": final.content})

        tool_calls = [
            ToolCallRequested(call_id=block.id, name=block.name, input=dict(block.input))
            for block in final.content
            if block.type == "tool_use"
        ]
        for call in tool_calls:
            yield ToolCallEvent(call=call)

        stop_reason = "tool_use" if tool_calls and final.stop_reason == "tool_use" else "end_turn"
        yield TurnFinished(
            stop_reason=stop_reason,
            usage={
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
            },
        )


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    def new_turn(self) -> AnthropicProviderTurn:
        return AnthropicProviderTurn(self._client, self.model)
