"""Receptionist agent: gathers research requirements from the user."""

from __future__ import annotations

import asyncio
import json

from config import Backend, Config
from providers import get_provider
from agents.prompts import load_prompt

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
    messages: list[dict] = []
    brief: dict | None = None

    async def tool_executor(name: str, args: dict) -> str:
        nonlocal brief
        if name == "submit_brief":
            brief = args
            return "Brief submitted successfully. The research team will begin shortly."
        return f"Unknown tool: {name}"

    # We always use the API for the interactive receptionist
    provider = get_provider(Backend.API, "anthropic")

    # Get the user's initial description
    print(
        "\nDescribe what you'd like to research "
        "(the assistant will ask follow-up questions):\n"
    )
    initial_input = await asyncio.to_thread(input, "You: ")
    messages.append({"role": "user", "content": initial_input})

    while brief is None:
        # The provider handles the tool-use loop (e.g. if the model calls submit_brief)
        # We pass the messages list which is mutated in place.
        response_text = await provider(
            model=config.receptionist_model,
            system=load_prompt("receptionist"),
            messages=messages,
            tools=[SUBMIT_BRIEF_TOOL],
            tool_executor=tool_executor,
            max_tokens=1024,
        )

        if brief is not None:
            break

        # If the model didn't call submit_brief, show its text and wait for user input
        if response_text:
            print(f"\nAssistant: {response_text}")

        # Wait for user input
        user_input = await asyncio.to_thread(input, "\nYou: ")
        if user_input.strip().lower() in ("quit", "exit", "q"):
            raise KeyboardInterrupt("User cancelled intake.")
        messages.append({"role": "user", "content": user_input})

    print("\n--- Research brief compiled ---")
    print(json.dumps(brief, indent=2))
    return brief
