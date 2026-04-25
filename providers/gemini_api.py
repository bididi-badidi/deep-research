"""Google Gemini API backend with Google Search grounding and tool-use loop."""

from __future__ import annotations

from typing import Awaitable, Callable

from google import genai
from google.genai import types


def to_gemini_tools(
    tools: list[dict], *, include_search: bool = True
) -> list[types.Tool]:
    """Convert common tool definitions to Gemini API format."""
    declarations: list[types.FunctionDeclaration] = []
    if tools:
        for t in tools:
            props: dict[str, types.Schema] = {}
            for k, v in t["parameters"].items():
                props[k] = types.Schema(
                    type="STRING",
                    description=v.get("description", ""),
                )
            declarations.append(
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=types.Schema(
                        type="OBJECT",
                        properties=props,
                        required=t.get("required", []),
                    ),
                )
            )

    if not include_search and not declarations:
        return []

    return [
        types.Tool(
            google_search=types.GoogleSearch() if include_search else None,
            function_declarations=declarations or None,
        )
    ]


async def run(
    *,
    model: str,
    system: str,
    prompt: str | None = None,
    messages: list[types.Content] | None = None,
    tools: list[dict] | None = None,
    tool_executor: Callable[[str, dict], Awaitable[str]] | None = None,
    include_search: bool = True,
) -> str:
    """Run an autonomous Gemini agent loop with Google Search + custom tools.

    Returns the final text output from the model.
    """
    client = genai.Client()
    api_tools = to_gemini_tools(tools or [], include_search=include_search)

    config = types.GenerateContentConfig(
        system_instruction=system,
        tools=api_tools or None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            include_server_side_tool_invocations=True,
        ),
    )

    if not prompt and not messages:
        raise ValueError("At least one of 'prompt' or 'messages' must be provided.")

    if messages:
        contents = messages.copy()
        if prompt:
            contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
    else:
        # prompt is guaranteed to be non-empty here by the check above
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    while True:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        contents.append(candidate.content)

        # Get function calls from candidate
        fn_calls = [p.function_call for p in candidate.content.parts if p.function_call]

        if not fn_calls:
            text_parts = [p.text for p in candidate.content.parts if p.text]
            return "\n".join(text_parts)

        if not tool_executor:
            raise RuntimeError(
                f"Model returned {len(fn_calls)} function calls but no tool_executor was provided."
            )

        # Execute function calls and return results
        response_parts: list[types.Part] = []
        for fc in fn_calls:
            result = await tool_executor(fc.name, dict(fc.args))
            response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )
        contents.append(types.Content(role="tool", parts=response_parts))
