"""Research lead agent: plans research and synthesizes findings."""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from config import Config
from providers import get_provider
from tools import FILE_TOOLS, execute as tool_execute

# ---------------------------------------------------------------------------
# Phase A: Planning
# ---------------------------------------------------------------------------

PLANNING_SYSTEM = """\
You are the lead researcher coordinating a multi-agent research system. \
You receive a research brief and must decompose it into concrete subtasks \
for parallel execution by research subagents.

Each subagent can:
- Search the web via Google Search
- Read and write files in the shared workspace

Create 2-5 focused, non-overlapping subtasks. Each subtask should be \
independent and specific enough for a single agent to complete.

When your plan is ready, call the `create_plan` tool with a JSON array of tasks.
"""

CREATE_PLAN_TOOL = {
    "name": "create_plan",
    "description": "Submit the research plan as a JSON array of task objects.",
    "parameters": {
        "tasks": {
            "type": "string",
            "description": (
                'JSON array of objects. Each object has: '
                '"id" (short slug), "title" (human-readable), '
                '"objective" (detailed instructions for the subagent), '
                '"search_hints" (array of suggested search queries).'
            ),
        },
    },
    "required": ["tasks"],
}

# ---------------------------------------------------------------------------
# Phase B: Synthesis
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """\
You are the lead researcher. Your subagents have completed their research. \
Review all findings files in the workspace/findings/ directory and produce a \
comprehensive final report.

Your report must:
1. Synthesize findings across all subtasks into a coherent narrative.
2. Highlight key insights, agreements, and contradictions between sources.
3. Note gaps or areas needing further research.
4. Be well-structured with clear sections and headings.
5. Include source URLs where available.

Write the final report to report.md using the write_file tool.
"""


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

    provider = get_provider(config.backend, "anthropic")
    response_text = await provider(
        model=config.lead_model,
        system=PLANNING_SYSTEM,
        messages=messages,
        tools=[CREATE_PLAN_TOOL] + FILE_TOOLS,
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
    )

    if plan_data is None:
        # Fallback for CLI mode where the tool call might be in the text response
        # or the model just printed the JSON.
        import re
        # Look for JSON-like structure in the text
        json_match = re.search(r"\[\s*\{.*\}\s*\]", response_text, re.DOTALL)
        if json_match:
            try:
                plan_data = json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
    if plan_data is None:
        print(f"DEBUG: Lead response text: {response_text}")
        raise RuntimeError("Lead agent failed to produce a research plan.")

    # Persist plan
    plan_path = config.workspace / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan_data, indent=2))

    return plan_data


async def synthesize(config: Config) -> str:
    """Read all findings and write a final report. Returns the model's closing text."""

    async def _exec_tool(name: str, args: dict) -> str:
        return await tool_execute(name, args, workspace=config.workspace)

    messages = [
        {
            "role": "user",
            "content": (
                "All subagents have completed their research. "
                "List the findings directory, read each file, "
                "then write the synthesized report to report.md."
            ),
        }
    ]

    provider = get_provider(config.backend, "anthropic")
    result = await provider(
        model=config.lead_model,
        system=SYNTHESIS_SYSTEM,
        messages=messages,
        tools=FILE_TOOLS,
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
    )

    return result
