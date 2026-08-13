import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

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


class OpenAIProviderTurn:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model
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
        self._tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]
        self._messages = [{"role": "system", "content": system}]
        self._messages.extend({"role": m.role, "content": m.content} for m in history)
        self._messages.append({"role": "user", "content": user_content})
        async for event in self._step():
            yield event

    async def continue_with_tool_results(
        self, results: list[ToolCallResultPayload]
    ) -> AsyncIterator[ProviderEvent]:
        for result in results:
            self._messages.append(
                {"role": "tool", "tool_call_id": result.call_id, "content": result.output}
            )
        async for event in self._step():
            yield event

    async def _step(self) -> AsyncIterator[ProviderEvent]:  # noqa: C901
        stream = await self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=MAX_RESPONSE_TOKENS,
            messages=self._messages,
            tools=self._tools or None,
            stream=True,
            stream_options={"include_usage": True},
        )

        accumulated_calls: dict[int, dict[str, Any]] = {}
        text_parts: list[str] = []
        finish_reason: str | None = None
        usage = {"input_tokens": 0, "output_tokens": 0}

        async for chunk in stream:
            if chunk.usage is not None:
                usage = {
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                }
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            delta = choice.delta
            if delta.content:
                text_parts.append(delta.content)
                yield TextDelta(text=delta.content)
            for tool_call_delta in delta.tool_calls or []:
                slot = accumulated_calls.setdefault(
                    tool_call_delta.index, {"id": None, "name": None, "arguments": ""}
                )
                if tool_call_delta.id:
                    slot["id"] = tool_call_delta.id
                if tool_call_delta.function and tool_call_delta.function.name:
                    slot["name"] = tool_call_delta.function.name
                if tool_call_delta.function and tool_call_delta.function.arguments:
                    slot["arguments"] += tool_call_delta.function.arguments

        tool_calls: list[ToolCallRequested] = []
        if accumulated_calls:
            openai_tool_calls = []
            for index in sorted(accumulated_calls):
                slot = accumulated_calls[index]
                try:
                    parsed_input = json.loads(slot["arguments"] or "{}")
                except ValueError:
                    parsed_input = {}
                tool_calls.append(
                    ToolCallRequested(call_id=slot["id"], name=slot["name"], input=parsed_input)
                )
                openai_tool_calls.append(
                    {
                        "id": slot["id"],
                        "type": "function",
                        "function": {"name": slot["name"], "arguments": slot["arguments"]},
                    }
                )
            self._messages.append(
                {
                    "role": "assistant",
                    "content": "".join(text_parts) or None,
                    "tool_calls": openai_tool_calls,
                }
            )
        else:
            self._messages.append({"role": "assistant", "content": "".join(text_parts)})

        for call in tool_calls:
            yield ToolCallEvent(call=call)

        stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"
        yield TurnFinished(stop_reason=stop_reason, usage=usage)


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model

    def new_turn(self) -> OpenAIProviderTurn:
        return OpenAIProviderTurn(self._client, self.model)
