"""Research lead agent: plans research and synthesizes findings."""

from __future__ import annotations

import json

from config import Config, Backend
from providers import get_provider
from tools import FILE_TOOLS, execute as tool_execute
from agents.prompts import load_prompt

CREATE_PLAN_TOOL = {
    "name": "create_plan",
    "description": "Submit the research plan as a JSON array of task objects.",
    "parameters": {
        "tasks": {
            "type": "string",
            "description": (
                "JSON array of objects. Each object has: "
                '"id" (short slug), "title" (human-readable), '
                '"objective" (detailed instructions for the subagent), '
                '"search_hints" (array of suggested search queries).'
            ),
        },
    },
    "required": ["tasks"],
}

async def plan(config: Config, brief: dict) -> list[dict]:
    """Decompose a research brief into subtasks. Returns list of task dicts."""
    plan_data: list[dict] | None = None

    async def _exec_tool(name: str, args: dict) -> str:
        nonlocal plan_data
        if name == "create_plan":
            try:
                plan_data = json.loads(args["tasks"])
                return "Plan created."
            except json.JSONDecodeError as e:
                return f"Error: Failed to parse JSON in 'tasks'. Please ensure it's a valid JSON array of objects. Detail: {e}"
        return await tool_execute(name, args, workspace=config.workspace)

    messages = [
        {
            "role": "user",
            "content": f"Research brief:\n\n{json.dumps(brief, indent=2)}",
        }
    ]

    provider_name = "gemini" if config.backend == Backend.CLI else "anthropic"
    model_name = (
        config.subagent_model if config.backend == Backend.CLI else config.lead_model
    )
    provider = get_provider(config.backend, provider_name)

    system_prompt = load_prompt("lead_planning")
    if config.backend == Backend.CLI:
        system_prompt += (
            "\n\nIMPORTANT: In this environment, custom tools like `create_plan` are unavailable. "
            "You MUST output the research plan as a raw JSON array of objects directly in your response text. "
            "Each object MUST have the following keys: "
            '1. "id" (short unique slug, e.g., "market-size"), '
            '2. "title" (human-readable title), '
            '3. "objective" (detailed research instructions), '
            '4. "search_hints" (list of suggested search queries).'
        )

    response_text = await provider(
        model=model_name,
        system=system_prompt,
        messages=messages,
        tools=[CREATE_PLAN_TOOL] + FILE_TOOLS,
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
        workspace=str(config.workspace),
    )

    # Persist plan
    plan_path = config.workspace / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    if plan_data:
        plan_path.write_text(json.dumps(plan_data, indent=2))
    elif response_text:
        # Final fallback: if we still don't have plan_data, try more aggressive cleanup

        # Look for the first '[' and last ']'
        try:
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start != -1 and end != -1:
                potential_json = response_text[start : end + 1]
                plan_data = json.loads(potential_json)
                plan_path.write_text(json.dumps(plan_data, indent=2))
        except (json.JSONDecodeError, ValueError):
            pass

    if plan_data is None:
        print(f"DEBUG: Lead response text: {response_text}")
        raise RuntimeError("Lead agent failed to produce a research plan.")

    return plan_data


async def synthesize(config: Config) -> str:
    """Read all findings and write a final report. Returns the model's closing text."""

    findings_dir = config.workspace / "findings"
    findings_files = list(findings_dir.glob("*.md"))

    findings_content = ""
    for f in sorted(findings_files):
        try:
            content = f.read_text()
            findings_content += f"\n\n--- Findings from {f.name} ---\n\n{content}"
        except Exception as e:
            print(f"Warning: Failed to read {f}: {e}")

    system_prompt = load_prompt("lead_synthesis")
    if config.backend == Backend.CLI:
        system_prompt += (
            "\n\nIMPORTANT: In this environment, you MUST output the final report "
            "directly in your response text. Do NOT use any tools to write the file. "
            "Python will handle writing your output to report.md."
        )

    messages = [
        {
            "role": "user",
            "content": (
                f"All subagents have completed their research. Here are the findings:\n{findings_content}\n\n"
                "Please synthesize these findings into a comprehensive final report. "
                "Output the full report in markdown format."
            ),
        }
    ]

    async def _exec_tool(name: str, args: dict) -> str:
        return await tool_execute(name, args, workspace=config.workspace)

    provider_name = "gemini" if config.backend == Backend.CLI else "anthropic"
    model_name = (
        config.subagent_model if config.backend == Backend.CLI else config.lead_model
    )
    provider = get_provider(config.backend, provider_name)
    result = await provider(
        model=model_name,
        system=system_prompt,
        messages=messages,
        tools=FILE_TOOLS,
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
        workspace=str(config.workspace),
    )

    # Persist report if the model didn't use a tool to write it (e.g. in CLI mode fallback)
    report_path = config.workspace / "report.md"
    if result and ("# " in result or "## " in result):
        # Strip potential markdown code blocks
        clean_report = result
        if "```markdown" in clean_report:
            clean_report = clean_report.split("```markdown")[1].split("```")[0].strip()
        elif "```" in clean_report:
            # Check if it looks like a code block starting at the beginning
            parts = clean_report.split("```")
            if len(parts) >= 3:
                clean_report = parts[1].strip()
                # If first line is a language identifier, strip it
                lines = clean_report.split("\n")
                if lines and not lines[0].startswith("#"):
                    clean_report = "\n".join(lines[1:]).strip()

        report_path.write_text(clean_report)

    return result
