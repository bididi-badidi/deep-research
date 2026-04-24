"""Receptionist agent: gathers research requirements from the user."""

from __future__ import annotations

import asyncio
import json

from config import Backend, Config
from providers import get_provider
from agents.prompts import load_prompt
from utils import extract_json, get_provider_name

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
    session_id: str | None = None

    async def tool_executor(name: str, args: dict) -> str:
        nonlocal brief
        if name == "submit_brief":
            brief = args
            return "Brief submitted successfully. The research team will begin shortly."
        return f"Unknown tool: {name}"

    # Use the configured backend.
    model_name = config.receptionist_model
    provider_name = get_provider_name(model_name)
    provider = get_provider(config.backend, provider_name)

    # Get the user's initial description
    print("\nDescribe what you'd like to research (input quit to cancel):\n")
    initial_input = await asyncio.to_thread(input, "You: ")
    messages.append({"role": "user", "content": initial_input})

    system_prompt = load_prompt("receptionist")
    if config.backend == Backend.CLI:
        system_prompt += (
            "\n\nIMPORTANT: In this environment, custom tools like `submit_brief` are unavailable. "
            "Follow the normal intake checklist and present the text-format brief as usual. "
            "However, once the user explicitly CONFIRMS the brief (e.g. says 'yes', 'looks good', 'proceed'), "
            "your response MUST end with a raw JSON object (no markdown code fences) on its own line. "
            'The JSON MUST have these exact keys: "topic", "scope", "questions", "depth", '
            'and optionally "output_preferences". '
            "Example of the required JSON suffix:\n"
            '{"topic": "...", "scope": "...", "questions": "1. ...", "depth": "moderate"}\n'
            "Do NOT omit the JSON when the user confirms. The pipeline cannot proceed without it."
        )

    while brief is None:
        # The provider handles the tool-use loop (e.g. if the model calls submit_brief)
        # We pass the messages list which is mutated in place.

        response_text = await provider(
            model=model_name,
            system=system_prompt,
            messages=messages,
            tools=[SUBMIT_BRIEF_TOOL],
            tool_executor=tool_executor,
            max_tokens=1024,
            session_id=session_id,
            sandbox=True,
            tool_profile="search_only",
        )

        if brief is not None:
            break

        # In CLI mode, try to extract the brief from response_text if not already set by tool_executor
        if config.backend == Backend.CLI and response_text:
            parsed = extract_json(response_text)
            if isinstance(parsed, dict) and "topic" in parsed:
                print(f"\nAssistant: {response_text}")
                print(
                    "\n[receptionist] Brief JSON detected in response — handing off to lead."
                )
                brief = parsed
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


async def run_with_queue(
    config: Config,
    in_q: asyncio.Queue,
    out_q: asyncio.Queue,
    on_brief,
) -> dict:
    """Queue-based receptionist for programmatic (Gradio) integration.

    Replaces stdin/stdout with asyncio Queues so any UI can drive the
    conversation.  ``on_brief`` is an async callable invoked with the
    completed brief dict once ``submit_brief`` is called by the model.
    """
    messages: list[dict] = []
    brief: dict | None = None

    async def tool_executor(name: str, args: dict) -> str:
        nonlocal brief
        if name == "submit_brief":
            brief = args
            return "Brief submitted successfully. The research team will begin shortly."
        return f"Unknown tool: {name}"

    provider_name = get_provider_name(config.receptionist_model)
    provider = get_provider(config.backend, provider_name)
    system_prompt = load_prompt("receptionist")

    initial_input = await in_q.get()
    messages.append({"role": "user", "content": initial_input})

    while True:
        try:
            response_text = await provider(
                model=config.receptionist_model,
                system=system_prompt,
                messages=messages,
                tools=[SUBMIT_BRIEF_TOOL],
                tool_executor=tool_executor,
                max_tokens=1024,
                session_id=None,
                tool_profile="search_only",
            )
        except Exception as exc:
            await out_q.put(f"*(Receptionist error: {exc})*")
            return {}

        if brief is not None:
            closing = response_text or "Brief submitted! The research team will begin shortly."
            await out_q.put(closing)
            await on_brief(brief)
            break

        # Always put something in out_q so send_message doesn't block forever
        await out_q.put(response_text or "*(no response from model)*")

        user_input = await in_q.get()
        if user_input.strip().lower() in ("quit", "exit", "q"):
            raise KeyboardInterrupt("User cancelled intake.")
        messages.append({"role": "user", "content": user_input})

    return brief
