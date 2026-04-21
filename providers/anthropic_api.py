"""Anthropic API backend with tool-use loop."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from anthropic import AsyncAnthropic


def to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """Convert common tool definitions to Anthropic API format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": {
                "type": "object",
                "properties": t["parameters"],
                "required": t.get("required", []),
            },
        }
        for t in tools
    ]


async def run(
    *,
    model: str,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_executor: Callable[[str, dict], Awaitable[str]] | None = None,
    max_tokens: int = 16384,
    client: AsyncAnthropic | None = None,
) -> str:
    """Run an autonomous agent loop until the model stops calling tools.

    *messages* is mutated in place so the caller can inspect the full history.
    Returns the final text output from the model.
    """
    client = client or AsyncAnthropic()
    api_tools = to_anthropic_tools(tools) if tools else []

    while True:
        kwargs: dict[str, Any] = dict(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        if api_tools:
            kwargs["tools"] = api_tools

        response = await client.messages.create(**kwargs)
        messages.append({"role": "assistant", "content": response.content})

        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_blocks:
            return "".join(
                b.text for b in response.content if hasattr(b, "text") and b.text
            )

        # Execute all tool calls and feed results back
        results: list[dict] = []
        for block in tool_blocks:
            output = await tool_executor(block.name, block.input)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                }
            )
        messages.append({"role": "user", "content": results})
