"""Receptionist agent: gathers research requirements from the user."""
from __future__ import annotations

import asyncio
import json

from anthropic import AsyncAnthropic

from config import Config
from providers.anthropic_api import to_anthropic_tools

SYSTEM_PROMPT = """\
You are a research receptionist. Your role is to gather enough information \
from the user to produce a detailed research brief for the research team.

Collect the following through natural conversation:

1. **Topic** - What is the user researching?
2. **Scope** - How broad or narrow? Geographic, temporal, or domain boundaries?
3. **Key Questions** - Specific questions that must be answered.
4. **Depth** - Overview, moderate analysis, or deep technical dive?
5. **Output Preferences** - Structure, format, or length preferences?

Guidelines:
- Be conversational. Don't dump all questions at once.
- Ask follow-up questions to clarify vague answers.
- If the user provides rich detail upfront, skip questions you can already answer.
- When you have sufficient information, call the `submit_brief` tool.
- If the user seems unsure, offer suggestions to help them refine their needs.
"""

SUBMIT_BRIEF_TOOL = {
    "name": "submit_brief",
    "description": "Submit the completed research brief once enough information is gathered.",
    "parameters": {
        "topic": {
            "type": "string",
            "description": "The main research topic",
        },
        "scope": {
            "type": "string",
            "description": "Scope and boundaries of the research",
        },
        "questions": {
            "type": "string",
            "description": "Key questions to answer, separated by newlines",
        },
        "depth": {
            "type": "string",
            "description": "Desired depth: overview | moderate | deep",
        },
        "output_preferences": {
            "type": "string",
            "description": "Preferences for output structure and format",
        },
    },
    "required": ["topic", "scope", "questions", "depth"],
}


async def run(config: Config) -> dict:
    """Run the interactive receptionist intake. Returns the research brief dict."""
    client = AsyncAnthropic()
    messages: list[dict] = []
    brief: dict | None = None

    async def tool_executor(name: str, args: dict) -> str:
        nonlocal brief
        if name == "submit_brief":
            brief = args
            return "Brief submitted successfully. The research team will begin shortly."
        return f"Unknown tool: {name}"

    tools = to_anthropic_tools([SUBMIT_BRIEF_TOOL])

    # Get the user's initial description
    print(
        "\nDescribe what you'd like to research "
        "(the assistant will ask follow-up questions):\n"
    )
    initial_input = await asyncio.to_thread(input, "You: ")
    messages.append({"role": "user", "content": initial_input})

    while brief is None:
        response = await client.messages.create(
            model=config.receptionist_model,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools,
            max_tokens=1024,
        )

        messages.append({"role": "assistant", "content": response.content})

        # Separate text and tool-use blocks
        text_parts = [b.text for b in response.content if hasattr(b, "text") and b.text]
        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        # Always print any text the model produced
        if text_parts:
            print(f"\nAssistant: {''.join(text_parts)}")

        if tool_blocks:
            results = []
            for block in tool_blocks:
                output = await tool_executor(block.name, block.input)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
            messages.append({"role": "user", "content": results})
        else:
            # Wait for user input
            user_input = await asyncio.to_thread(input, "\nYou: ")
            if user_input.strip().lower() in ("quit", "exit", "q"):
                raise KeyboardInterrupt("User cancelled intake.")
            messages.append({"role": "user", "content": user_input})

    print("\n--- Research brief compiled ---")
    print(json.dumps(brief, indent=2))
    return brief
