"""Research lead agent: plans research and synthesizes findings."""

from __future__ import annotations

import asyncio
import json

from config import Config, Backend
from providers import get_provider
from tools import FILE_TOOLS, list_tool_profiles, execute as tool_execute
from agents.prompts import load_prompt
from utils import extract_json, extract_json_or_raise

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
                '"search_hints" (array of suggested search queries), '
                '"tool_profile" (string, one of: "full", "read_only", "write_only", "search_only").'
            ),
        },
    },
    "required": ["tasks"],
}

DISPATCH_SUBAGENTS_TOOL = {
    "name": "dispatch_subagents",
    "description": (
        "Dispatch additional research subagents to fill gaps in the current findings. "
        "Use this when the current evidence is insufficient to write an honest report. "
        "Each task follows the same schema as create_plan output. "
        "Returns a summary of which tasks succeeded or failed."
    ),
    "parameters": {
        "tasks": {
            "type": "string",
            "description": (
                "JSON array of task objects. Each object has: "
                '"id" (short slug, prefix with "R-" for remediation), '
                '"title", "objective", "search_hints", '
                '"tool_profile" (optional, defaults to "full").'
            ),
        },
        "reason": {
            "type": "string",
            "description": "Brief explanation of why additional research is needed.",
        },
    },
    "required": ["tasks", "reason"],
}


async def plan(config: Config, brief: dict) -> list[dict]:
    """Decompose a research brief into subtasks. Returns list of task dicts."""
    plan_data: list[dict] | None = None

    async def _exec_tool(name: str, args: dict) -> str:
        nonlocal plan_data
        if name == "create_plan":
            try:
                parsed = extract_json_or_raise(
                    args["tasks"],
                    "Error: Failed to parse JSON in 'tasks'. Please ensure it's a valid JSON array of objects.",
                )
                if isinstance(parsed, list):
                    plan_data = parsed
                    return "Plan created."
                else:
                    return "Error: 'tasks' must be a JSON array of objects."
            except ValueError as e:
                return str(e)
        return await tool_execute(name, args, workspace=config.workspace)

    messages = [
        {
            "role": "user",
            "content": f"Research brief:\n\n{json.dumps(brief, indent=2)}",
        }
    ]

    provider_name = "gemini" if config.backend == Backend.CLI else "anthropic"
    model_name = config.lead_model
    provider = get_provider(config.backend, provider_name)

    profiles_str = json.dumps(list_tool_profiles(), indent=2)
    system_prompt = load_prompt("lead_planning").replace(
        "{tool_profiles}", profiles_str
    )

    if config.backend == Backend.CLI:
        system_prompt += (
            "\n\nIMPORTANT: In this environment, custom tools like `create_plan` are unavailable. "
            "You MUST output the research plan as a raw JSON array of objects directly in your response text. "
            "Each object MUST have the following keys: "
            '1. "id" (short unique slug, e.g., "market-size"), '
            '2. "title" (human-readable title), '
            '3. "objective" (detailed research instructions), '
            '4. "search_hints" (list of suggested search queries), '
            '5. "tool_profile" (one of: "full", "read_only", "write_only", "search_only").'
        )

    response_text = await provider(
        model=model_name,
        system=system_prompt,
        messages=messages,
        tools=[CREATE_PLAN_TOOL] + FILE_TOOLS,
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
        workspace=str(config.workspace),
        tool_profile="full",
    )

    # Persist plan
    plan_path = config.workspace / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    if plan_data:
        # Validate and default tool_profile
        for task in plan_data:
            if "tool_profile" not in task:
                task["tool_profile"] = "full"
        plan_path.write_text(json.dumps(plan_data, indent=2))
    elif response_text:
        # Final fallback: if we still don't have plan_data, try more aggressive cleanup
        try:
            parsed = extract_json_or_raise(response_text)
            if isinstance(parsed, list):
                plan_data = parsed
                # Validate and default tool_profile for fallback parsing too
                for task in plan_data:
                    if "tool_profile" not in task:
                        task["tool_profile"] = "full"
                plan_path.write_text(json.dumps(plan_data, indent=2))
        except ValueError:
            pass

    if plan_data is None:
        print(f"DEBUG: Lead response text: {response_text}")
        raise RuntimeError("Lead agent failed to produce a research plan.")

    return plan_data


async def synthesize(config: Config) -> str:
    """Read all findings and write a final report. Returns the model's closing text."""

    findings_dir = config.workspace / "findings"

    def _read_findings():
        files = list(findings_dir.glob("*.md"))
        content = ""
        for f in sorted(files):
            try:
                c = f.read_text()
                content += f"\n\n--- Findings from {f.name} ---\n\n{c}"
            except Exception as e:
                print(f"Warning: Failed to read {f}: {e}")
        return content

    findings_content = _read_findings()

    system_prompt = load_prompt("lead_synthesis").replace(
        "{max_remediation_rounds}", str(config.max_remediation_rounds)
    )
    if config.backend == Backend.CLI:
        system_prompt += (
            "\n\nIMPORTANT: In this environment, custom tool calls are unavailable. "
            "You have two options:\n"
            "1. If the findings are sufficient, output ONLY the final report in markdown format "
            "(starting with a `#` heading). Python will save it to report.md.\n"
            "2. If you need more research, output ONLY a JSON object in this exact format "
            "(no markdown, no explanation):\n"
            '{"action": "dispatch_subagents", "reason": "<why more research is needed>", '
            '"tasks": [{"id": "<slug>", "title": "<title>", "objective": "<instructions>", '
            '"search_hints": ["<query1>"], "tool_profile": "full"}]}\n'
            "Do NOT mix JSON and markdown in the same response."
        )

    current_round = 0
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
        nonlocal current_round
        if name == "dispatch_subagents":
            current_round += 1
            if current_round > config.max_remediation_rounds:
                return f"Error: Maximum remediation rounds ({config.max_remediation_rounds}) reached. Please synthesize the final report now."

            try:
                remediation_tasks = extract_json_or_raise(
                    args["tasks"],
                    "Error: 'tasks' must be a JSON array of task objects.",
                )
                if not isinstance(remediation_tasks, list):
                    return "Error: 'tasks' must be a JSON array of task objects."

                reason = args["reason"]
                print(
                    f"\n--- Lead requesting remediation (round {current_round}/{config.max_remediation_rounds}): {reason} ---"
                )

                from agents import subagent

                # Ensure every task has a tool_profile
                for t in remediation_tasks:
                    if "tool_profile" not in t:
                        t["tool_profile"] = "full"

                results = await asyncio.gather(
                    *(subagent.run(config, task) for task in remediation_tasks),
                    return_exceptions=True,
                )

                summary = []
                for task, result in zip(remediation_tasks, results):
                    status = "FAIL" if isinstance(result, Exception) else "done"
                    summary.append(f"[{status}] {task['id']}: {task['title']}")

                # Re-read findings to get the new data
                new_findings = _read_findings()
                return (
                    f"Remediation round {current_round} complete. "
                    f"Findings directory has been updated with new evidence.\n"
                    f"Summary:\n" + "\n".join(summary) + "\n\n"
                    "Updated findings content:\n" + new_findings
                )
            except Exception as e:
                return f"Error during remediation: {e}"

        return await tool_execute(name, args, workspace=config.workspace)

    provider_name = "gemini" if config.backend == Backend.CLI else "anthropic"
    model_name = (
        config.subagent_model if config.backend == Backend.CLI else config.lead_model
    )
    provider = get_provider(config.backend, provider_name)

    if config.backend == Backend.CLI:
        from agents import subagent as subagent_module

        result = ""
        while True:
            result = await provider(
                model=model_name,
                system=system_prompt.replace("{current_round}", str(current_round)),
                messages=messages,
                tools=[DISPATCH_SUBAGENTS_TOOL] + FILE_TOOLS,
                tool_executor=_exec_tool,
                max_tokens=config.max_tokens,
                workspace=str(config.workspace),
                tool_profile="full",
            )

            parsed = extract_json(result)
            if isinstance(parsed, dict) and "tasks" in parsed:
                if current_round >= config.max_remediation_rounds:
                    print(
                        f"\n--- Max remediation rounds ({config.max_remediation_rounds}) reached. Forcing final report. ---"
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Maximum remediation rounds ({config.max_remediation_rounds}) reached. "
                                "You MUST now write the final report in markdown format using the available findings."
                            ),
                        }
                    )
                    result = await provider(
                        model=model_name,
                        system=system_prompt,
                        messages=messages,
                        tools=[DISPATCH_SUBAGENTS_TOOL] + FILE_TOOLS,
                        tool_executor=_exec_tool,
                        max_tokens=config.max_tokens,
                        workspace=str(config.workspace),
                        tool_profile="full",
                    )
                    break

                remediation_tasks = parsed["tasks"]
                if isinstance(remediation_tasks, str):
                    remediation_tasks = extract_json(remediation_tasks) or []
                if not isinstance(remediation_tasks, list):
                    break

                reason = parsed.get("reason", "Additional research needed.")
                current_round += 1
                print(
                    f"\n--- Lead requesting remediation (round {current_round}/{config.max_remediation_rounds}): {reason} ---"
                )

                for t in remediation_tasks:
                    if "tool_profile" not in t:
                        t["tool_profile"] = "full"

                sub_results = await asyncio.gather(
                    *(subagent_module.run(config, task) for task in remediation_tasks),
                    return_exceptions=True,
                )

                summary = []
                for task, sub_result in zip(remediation_tasks, sub_results):
                    status = "FAIL" if isinstance(sub_result, Exception) else "done"
                    summary.append(f"[{status}] {task['id']}: {task['title']}")

                new_findings = _read_findings()
                # Discard previous history to prevent context pollution and O(n²) growth.
                # In CLI mode, we start fresh with the full consolidated findings in every round.
                messages[:] = [
                    {
                        "role": "user",
                        "content": (
                            f"All subagents have completed their research (including {current_round} remediation rounds). "
                            f"Here are the COMPLETE consolidated findings:\n{new_findings}\n\n"
                            "Please now synthesize the final report in markdown format, or request more research if still insufficient."
                        ),
                    }
                ]
            else:
                # Model output markdown — we're done
                break
    else:
        result = await provider(
            model=model_name,
            system=system_prompt.replace("{current_round}", str(current_round)),
            messages=messages,
            tools=[DISPATCH_SUBAGENTS_TOOL] + FILE_TOOLS,
            tool_executor=_exec_tool,
            max_tokens=config.max_tokens,
            workspace=str(config.workspace),
            tool_profile="full",
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
