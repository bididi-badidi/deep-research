"""Provider factory for API and CLI backends."""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol

from config import Backend


# CLI tool mappings (F3.2)
CLAUDE_PROFILE_MAP = {
    "full": ["Read", "Write", "Glob", "Grep"],
    "read_only": ["Read", "Glob", "Grep"],
    "write_only": ["Write"],
    "search_only": [],
}

GEMINI_PROFILE_MAP = {
    "full": "auto_edit",
    "read_only": "default",
    "write_only": "auto_edit",
    "search_only": "default",
}


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
        workspace: str | None = None,
        session_id: str | None = None,
        tool_profile: str | None = None,
        sandbox: bool = False,
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
                    prompt = kwargs.pop("prompt", None)
                    if not prompt:
                        raise ValueError(
                            "At least one of 'prompt' or 'messages' must be provided."
                        )
                    kwargs["messages"] = [{"role": "user", "content": prompt}]
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
                # First pass: map tool_use_id to tool name (Anthropic format)
                tool_names = {}
                if kwargs.get("messages"):
                    for msg in kwargs["messages"]:
                        content = msg["content"]
                        if isinstance(content, list):
                            for item in content:
                                if item.get("type") == "tool_use":
                                    tool_names[item["id"]] = item["name"]

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
                                    tool_id = item["tool_use_id"]
                                    # Use mapped name or fallback to a generic one if missing
                                    name = tool_names.get(tool_id, "unknown_tool")
                                    parts.append(
                                        genai_types.Part(
                                            function_response=genai_types.FunctionResponse(
                                                name=name,
                                                response={"result": item["content"]},
                                                id=tool_id,
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
                # CLI expects prompt string. For multi-turn support in CLI,
                # we use session_id if provided, otherwise we flatten the conversation history.
                session_id = kwargs.get("session_id")
                messages = kwargs.get("messages")
                tool_profile = kwargs.get("tool_profile")

                if kwargs.get("prompt") is None and messages:
                    if session_id:
                        # If we have a session, only send the latest user message
                        # find the last message from user
                        last_user_msg = None
                        for msg in reversed(messages):
                            if msg["role"] == "user":
                                last_user_msg = msg["content"]
                                break
                        if last_user_msg:
                            kwargs["prompt"] = last_user_msg
                        else:
                            # Fallback to flattening if no user message found (shouldn't happen)
                            kwargs["prompt"] = "Please continue."
                    else:
                        # Improved prompt-flattening approach (F1.3)
                        # We use XML-like tags to give more structure to the history
                        prompt_parts = ["Conversation history:"]
                        for msg in messages:
                            role = msg["role"]
                            content = msg["content"]
                            prompt_parts.append(f"<{role}>\n{content}\n</{role}>")
                        prompt_parts.append("Please provide your next response.")
                        kwargs["prompt"] = "\n\n".join(prompt_parts)

                prompt = kwargs.get("prompt")
                if not prompt:
                    raise ValueError(
                        "At least one of 'prompt' or 'messages' must be provided."
                    )

                # Map tools to allowed_tools names (Claude CLI built-ins)
                # Map: read_file -> Read, write_file -> Write, list_files -> Glob
                allowed_tools = []
                if tool_profile and tool_profile in CLAUDE_PROFILE_MAP:
                    allowed_tools = CLAUDE_PROFILE_MAP[tool_profile]
                else:
                    # Fallback to deriving from individual tools if profile not provided
                    tools = kwargs.get("tools", [])
                    for t in tools:
                        tname = t["name"]
                        if tname in ("read_file", "list_references", "read_reference"):
                            allowed_tools.append("Read")
                        elif tname == "write_file":
                            allowed_tools.append("Write")
                        elif tname == "list_files":
                            allowed_tools.append("Glob")
                        elif tname in ("Read", "Write", "Glob", "Bash", "Edit", "Grep"):
                            allowed_tools.append(tname)
                    # Deduplicate
                    allowed_tools = list(set(allowed_tools))

                result = await claude_run(
                    model=kwargs["model"],
                    system=kwargs["system"],
                    prompt=prompt,
                    workspace=kwargs.get("workspace", "./workspace"),
                    allowed_tools=allowed_tools if allowed_tools else None,
                    session_id=session_id,
                )

                if messages is not None:
                    messages.append({"role": "assistant", "content": result})

                return result

            return wrapped_claude_run

        elif name == "gemini":
            from .gemini_cli import run as gemini_run_cli

            async def wrapped_gemini_run_cli(**kwargs):
                # CLI expects prompt string. For multi-turn support in CLI,
                # we flatten the conversation history if messages list is provided.
                messages = kwargs.get("messages")
                tool_profile = kwargs.get("tool_profile", "full")
                approval_mode = GEMINI_PROFILE_MAP.get(tool_profile, "auto-edit")
                session_id = kwargs.get("session_id")
                cli_session_id = kwargs.get("cli_session_id")

                if kwargs.get("prompt") is None and messages:
                    if session_id:
                        # If we have a session, only send the latest user message
                        last_user_msg = None
                        for msg in reversed(messages):
                            if msg["role"] == "user":
                                last_user_msg = msg["content"]
                                break
                        if last_user_msg:
                            kwargs["prompt"] = last_user_msg
                        else:
                            kwargs["prompt"] = "Please continue."
                    else:
                        # Flatten history if no session_id
                        prompt_parts = []
                        for msg in messages:
                            role = "Human" if msg["role"] == "user" else "Assistant"
                            content = msg["content"]
                            prompt_parts.append(f"{role}: {content}")
                        kwargs["prompt"] = "\n\n".join(prompt_parts) + "\n\nAssistant: "

                prompt = kwargs.get("prompt")
                if not prompt:
                    raise ValueError(
                        "At least one of 'prompt' or 'messages' must be provided."
                    )

                result = await gemini_run_cli(
                    model=kwargs["model"],
                    system=kwargs["system"],
                    prompt=prompt,
                    workspace=kwargs.get("workspace", "./workspace"),
                    approval_mode=approval_mode,
                    cli_session_id=cli_session_id,
                    sandbox=kwargs.get("sandbox", False),
                )

                if messages is not None:
                    messages.append({"role": "assistant", "content": result})

                return result

            return wrapped_gemini_run_cli

    raise ValueError(f"Unknown provider: {backend.value}/{name}")
