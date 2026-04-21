"""Google Gemini API backend with Google Search grounding and tool-use loop."""
from __future__ import annotations

from typing import Awaitable, Callable

from google import genai
from google.genai import types


def to_gemini_tools(
    tools: list[dict], *, include_search: bool = True
) -> list[types.Tool]:
    """Convert common tool definitions to Gemini API format."""
    result: list[types.Tool] = []

    if include_search:
        result.append(types.Tool(google_search=types.GoogleSearch()))

    if tools:
        declarations: list[types.FunctionDeclaration] = []
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
        result.append(types.Tool(function_declarations=declarations))

    return result


async def run(
    *,
    model: str,
    system: str,
    prompt: str,
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
    )

    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    while True:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]
        contents.append(candidate.content)

        fn_calls = [p for p in candidate.content.parts if p.function_call]

        if not fn_calls:
            text_parts = [p.text for p in candidate.content.parts if p.text]
            return "\n".join(text_parts)

        # Execute function calls and return results
        response_parts: list[types.Part] = []
        for part in fn_calls:
            fc = part.function_call
            result = await tool_executor(fc.name, dict(fc.args))
            response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )
        contents.append(types.Content(role="user", parts=response_parts))
