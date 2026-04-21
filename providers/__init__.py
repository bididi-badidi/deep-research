"""Provider factory for API and CLI backends."""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from config import Backend


class ProviderRun(Protocol):
    async def __call__(
        self,
        *,
        model: str,
        system: str,
        prompt: str | None = None,
        messages: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, dict], Awaitable[str]] | None = None,
        include_search: bool = True,
        max_tokens: int = 4096,
    ) -> str: ...


def get_provider(backend: Backend, name: str) -> ProviderRun:
    """Return the correct run() function for the given backend and provider name."""
    if backend == Backend.API:
        if name == "anthropic":
            from .anthropic_api import run as anthropic_run

            async def wrapped_anthropic_run(**kwargs):
                # Anthropic API expects 'messages' list, which it mutates.
                # If only 'prompt' is provided, we wrap it.
                if kwargs.get("messages") is None:
                    kwargs["messages"] = [
                        {"role": "user", "content": kwargs.pop("prompt")}
                    ]
                else:
                    kwargs.pop("prompt", None)

                # Filter out kwargs that anthropic_api.run doesn't accept
                valid_keys = {
                    "model",
                    "system",
                    "messages",
                    "tools",
                    "tool_executor",
                    "max_tokens",
                    "client",
                }
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
                return await anthropic_run(**filtered_kwargs)

            return wrapped_anthropic_run

        elif name == "gemini":
            from .gemini_api import run as gemini_run
            from google.genai import types as genai_types

            async def wrapped_gemini_run(**kwargs):
                # Convert common messages format to Gemini types.Content
                if kwargs.get("messages"):
                    api_messages = []
                    for msg in kwargs["messages"]:
                        role = "user" if msg["role"] == "user" else "model"
                        content = msg["content"]

                        # Handle tool results (role: user in Anthropic/OpenAI, role: tool in Gemini)
                        if isinstance(content, list):
                            parts = []
                            for item in content:
                                if item.get("type") == "tool_result":
                                    role = "tool"
                                    parts.append(
                                        genai_types.Part(
                                            function_response=genai_types.FunctionResponse(
                                                name=item["tool_use_id"].split(":")[
                                                    0
                                                ],  # simple fallback
                                                response={"result": item["content"]},
                                                id=item["tool_use_id"],
                                            )
                                        )
                                    )
                                elif item.get("type") == "text":
                                    parts.append(genai_types.Part(text=item["text"]))
                            api_messages.append(
                                genai_types.Content(role=role, parts=parts)
                            )
                        else:
                            # Standard text message
                            api_messages.append(
                                genai_types.Content(
                                    role=role, parts=[genai_types.Part(text=content)]
                                )
                            )
                    kwargs["messages"] = api_messages

                # Filter out kwargs that gemini_api.run doesn't accept
                valid_keys = {
                    "model",
                    "system",
                    "prompt",
                    "messages",
                    "tools",
                    "tool_executor",
                    "include_search",
                }
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
                return await gemini_run(**filtered_kwargs)

            return wrapped_gemini_run

    elif backend == Backend.CLI:
        if name == "anthropic":
            from .claude_cli import run as claude_run

            async def wrapped_claude_run(**kwargs):
                # CLI expects prompt string.
                if kwargs.get("prompt") is None and kwargs.get("messages"):
                    kwargs["prompt"] = kwargs["messages"][-1]["content"]

                # Map tools to allowed_tools names
                tools = kwargs.get("tools", [])
                allowed_tools = [t["name"] for t in tools] if tools else None

                return await claude_run(
                    model=kwargs["model"],
                    system=kwargs["system"],
                    prompt=kwargs["prompt"],
                    allowed_tools=allowed_tools,
                )

            return wrapped_claude_run

        elif name == "gemini":
            from .gemini_cli import run as gemini_run_cli

            async def wrapped_gemini_run_cli(**kwargs):
                # CLI expects prompt string.
                if kwargs.get("prompt") is None and kwargs.get("messages"):
                    kwargs["prompt"] = kwargs["messages"][-1]["content"]

                return await gemini_run_cli(
                    model=kwargs["model"],
                    system=kwargs["system"],
                    prompt=kwargs["prompt"],
                )

            return wrapped_gemini_run_cli

    raise ValueError(f"Unknown provider: {backend.value}/{name}")
