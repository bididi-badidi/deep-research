"""Citation post-processor.

The Citation Agent always uses the Anthropic API provider, regardless of
``config.backend``. CLI mode controls the research agents only; this final pass
needs reliable tool calling for URL verification and report rewriting.
"""

from __future__ import annotations

import json
import re
from typing import Any

from config import Backend, Config
from providers import get_provider
from tools import VERIFY_URL_TOOL, WRITE_FILE_TOOL, execute as tool_execute
from agents.prompts import load_prompt

URL_RE = re.compile(r"https?://[^\s\])>\"']+")


async def run(config: Config, brief: dict) -> str:
    """Post-process report.md: verify URLs and reformat citations.

    Returns the path to the updated report.md as a string.
    """
    report_path = config.workspace / "report.md"
    if not report_path.exists():
        raise FileNotFoundError(f"Report not found: {report_path}")

    report_content = report_path.read_text(encoding="utf-8")
    citation_format = _citation_format_from_brief(brief)
    verification_results: list[dict[str, Any]] = []

    async def _exec_tool(name: str, args: dict) -> str:
        if name == "verify_url" and not config.verify_urls:
            result = {
                "url": args["url"],
                "reachable": "skipped",
                "status": None,
                "final_url": args["url"],
            }
            verification_results.append(result)
            return json.dumps(result)

        output = await tool_execute(name, args, workspace=config.workspace)
        if name == "verify_url":
            try:
                parsed = json.loads(output)
            except json.JSONDecodeError:
                parsed = {"url": args.get("url"), "reachable": False, "error": output}
            verification_results.append(parsed)
        return output

    provider = get_provider(Backend.API, "anthropic")
    system_prompt = load_prompt("citation", citation_format=citation_format)
    messages = [
        {
            "role": "user",
            "content": (
                "Post-process this report for citation correctness. "
                "Use the available tools to verify URLs and write the final report.\n\n"
                f"{report_content}"
            ),
        }
    ]

    await provider(
        model=config.citation_model,
        system=system_prompt,
        messages=messages,
        tools=[VERIFY_URL_TOOL, WRITE_FILE_TOOL],
        tool_executor=_exec_tool,
        max_tokens=config.max_tokens,
    )

    _write_audit_report(
        config=config,
        citation_format=citation_format,
        original_report=report_content,
        verification_results=verification_results,
    )

    return str(report_path)


def _citation_format_from_brief(brief: dict) -> str:
    output_preferences = brief.get("output_preferences") or {}
    if isinstance(output_preferences, dict):
        return str(output_preferences.get("citation_format") or "APA")
    return "APA"


def _write_audit_report(
    *,
    config: Config,
    citation_format: str,
    original_report: str,
    verification_results: list[dict[str, Any]],
) -> None:
    cited_urls = sorted(set(URL_RE.findall(original_report)))
    checked_urls = {r.get("url") for r in verification_results}
    missing_results = [
        {
            "url": url,
            "reachable": "not_checked",
            "error": "Citation agent did not call verify_url for this URL.",
        }
        for url in cited_urls
        if url not in checked_urls
    ]
    all_results = verification_results + missing_results
    audit = {
        "citation_format": citation_format,
        "verify_urls": config.verify_urls,
        "citation_count": len(cited_urls),
        "verified_count": len(verification_results),
        "unreachable_count": sum(
            1 for r in all_results if r.get("reachable") is False
        ),
        "urls": all_results,
    }
    (config.workspace / "citation_report.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
