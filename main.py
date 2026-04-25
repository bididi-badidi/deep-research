"""Deep Research: Multi-agent research system.

Architecture (inspired by Anthropic's multi-agent research system):
  User → Receptionist (Sonnet) → Lead (Opus) → Subagents (Gemini) → Report

Phase 1: API-based   (anthropic + google-genai SDKs)
Phase 2: CLI-based   (claude + gemini CLIs via asyncio.create_subprocess_exec)
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from config import Backend, Config


async def main() -> None:
    # Load .env variables before anything else
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Deep Research - Multi-agent research system"
    )
    parser.add_argument(
        "--backend",
        choices=["api", "cli"],
        default="api",
        help="Backend to use (default: api)",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("./workspace"),
        help="Workspace directory (default: ./workspace)",
    )
    parser.add_argument(
        "--max-remediation-rounds",
        type=int,
        default=2,
        help="Max number of iterative remediation rounds (default: 2)",
    )
    parser.add_argument(
        "--brief",
        type=Path,
        help="Path to a JSON research brief to skip interactive intake.",
    )
    args = parser.parse_args()

    config = Config(
        backend=Backend(args.backend),
        workspace=args.workspace.resolve(),
        max_remediation_rounds=args.max_remediation_rounds,
    )
    config.validate()

    print("=" * 50)
    print("  Deep Research - Multi-Agent Research System")
    print("=" * 50)

    # ── 1. Receptionist: gather research brief ──────────────────────────
    if args.brief:
        if not args.brief.exists():
            print(f"Error: Brief file not found at {args.brief}")
            return
        try:
            with open(args.brief, "r") as f:
                brief = json.load(f)
            print(f"\nLoaded research brief from {args.brief}")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON brief: {e}")
            return
    else:
        from agents import receptionist

        brief = await receptionist.run(config)

    # Generate a unique research ID based on the topic
    import re
    from datetime import datetime

    topic_slug = re.sub(r"[^a-z0-9]+", "-", brief["topic"].lower()).strip("-")[:30]
    if not topic_slug:
        topic_slug = "research"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    research_id = f"{topic_slug}-{timestamp}"

    # Update workspace to task-specific folder
    config.workspace = config.workspace / research_id
    config.workspace.mkdir(parents=True, exist_ok=True)
    (config.workspace / "findings").mkdir(exist_ok=True)

    print(f"\nResearch session ID: {research_id}")
    print(f"Workspace: {config.workspace}")

    # ── 2. Lead: plan research tasks ────────────────────────────────────
    from agents import lead

    print("\n--- Planning research ---")
    tasks = await lead.plan(config, brief)

    print(f"\nResearch plan ({len(tasks)} tasks):")
    for t in tasks:
        print(f"  - [{t['id']}] {t['title']}")

    # ── 3. Subagents: execute research in parallel ──────────────────────
    from agents import subagent

    print("\n--- Executing research subagents ---")
    results = await asyncio.gather(
        *(subagent.run(config, task) for task in tasks),
        return_exceptions=True,
    )

    for task, result in zip(tasks, results):
        status = "FAIL" if isinstance(result, Exception) else "done"
        detail = str(result) if isinstance(result, Exception) else ""
        print(f"  [{status}] {task['title']}  {detail}")

    # ── 4. Lead: synthesize findings into final report ──────────────────
    print("\n--- Synthesizing findings (may trigger remediation rounds) ---")
    await lead.synthesize(config)

    report_path = config.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        print(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        print("\nWarning: report.md not found — check workspace for outputs")


if __name__ == "__main__":
    asyncio.run(main())
