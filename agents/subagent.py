"""Research subagent: performs web research via Gemini with Google Search grounding."""

from __future__ import annotations

from config import Config
from providers import get_provider
from tools import get_tools_for_profile, execute as tool_execute
from agents.prompts import load_prompt
from utils import get_provider_name


async def run(config: Config, task: dict) -> str:
    """Execute a single research subtask. Returns the model's closing text."""
    # Handle schema variations from different models
    id_ = task.get("id", "unknown")
    title = task.get("title") or task.get("name") or "Research Task"
    objective = (
        task.get("objective") or task.get("description") or "Perform general research."
    )
    hints_list = task.get("search_hints") or task.get("agent_action")
    profile = task.get("tool_profile", "full")

    prompt = f"# Research Task: {title}\n\n**Objective:** {objective}\n\n"
    if hints_list:
        if isinstance(hints_list, list):
            hints = ", ".join(hints_list)
        else:
            hints = str(hints_list)
        prompt += f"**Suggested searches:** {hints}\n\n"
    prompt += f"IMPORTANT: Write your findings to the RELATIVE path: findings/{id_}.md. Do not use absolute paths."

    system = load_prompt("subagent", task_id=id_)

    async def _exec_tool(name: str, args: dict) -> str:
        return await tool_execute(name, args, workspace=config.workspace)

    model_name = config.subagent_model
    provider_name = get_provider_name(model_name)
    provider = get_provider(config.backend, provider_name)
    tools = get_tools_for_profile(profile)

    return await provider(
        model=config.subagent_model,
        system=system,
        prompt=prompt,
        tools=tools,
        tool_executor=_exec_tool,
        include_search=True,
        workspace=str(config.workspace),
        tool_profile=profile,
        sandbox=True,
    )
