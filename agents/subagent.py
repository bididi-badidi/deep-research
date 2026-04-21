"""Research subagent: performs web research via Gemini with Google Search grounding."""
from __future__ import annotations

from config import Config
from providers import gemini_api
from tools import FILE_TOOLS, execute as tool_execute

SYSTEM_PROMPT = """\
You are a research subagent. You have been assigned a specific research task.

Use Google Search to find relevant, high-quality information, then write your \
findings to a markdown file in the workspace.

Guidelines:
- Search broadly first, then drill into specifics.
- Evaluate source quality — prefer authoritative and recent sources.
- Record key facts, data points, and direct quotes with source URLs.
- Note contradictions or uncertainties between sources.
- Structure your findings clearly with headings and bullet points.

Write your findings to: findings/{task_id}.md

The file must include:
- A title matching your assigned task
- Sections for each major finding
- Source URLs for all claims
- A brief summary at the end
"""


async def run(config: Config, task: dict) -> str:
    """Execute a single research subtask. Returns the model's closing text."""
    prompt = (
        f"# Research Task: {task['title']}\n\n"
        f"**Objective:** {task['objective']}\n\n"
    )
    if task.get("search_hints"):
        hints = ", ".join(task["search_hints"])
        prompt += f"**Suggested searches:** {hints}\n\n"
    prompt += f"Write your findings to: findings/{task['id']}.md"

    system = SYSTEM_PROMPT.replace("{task_id}", task["id"])

    async def _exec_tool(name: str, args: dict) -> str:
        return await tool_execute(name, args, workspace=config.workspace)

    return await gemini_api.run(
        model=config.subagent_model,
        system=system,
        prompt=prompt,
        tools=FILE_TOOLS,
        tool_executor=_exec_tool,
        include_search=True,
    )
