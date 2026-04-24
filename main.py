"""Deep Research: Multi-agent research system.

Architecture (inspired by Anthropic's multi-agent research system):
  User → Receptionist (Sonnet) → Lead (Opus) → Subagents (Gemini) → Report

Phase 1: API-based   (anthropic + google-genai SDKs)
Phase 2: CLI-based   (claude + gemini CLIs via asyncio.create_subprocess_exec)
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from config import Backend, Config


async def run_pipeline(
    config: Config,
    brief: dict,
    on_log=None,
) -> None:
    """Execute the full research pipeline after the brief is gathered.

    Args:
        config:  Runtime configuration (backend, workspace, etc.)
        brief:   Research brief dict produced by the receptionist.
        on_log:  Optional callable(str) invoked for each log line.
                 Defaults to ``print`` so CLI usage is unchanged.
    """
    log = on_log or print

    from agents import lead
    from agents import subagent

    # ── 2. Lead: plan research tasks ────────────────────────────────────
    log("\n--- Planning research ---")
    tasks = await lead.plan(config, brief)

    log(f"\nResearch plan ({len(tasks)} tasks):")
    for t in tasks:
        log(f"  - [{t['id']}] {t['title']}")

    # ── 3. Subagents: execute research in parallel ──────────────────────
    log("\n--- Executing research subagents ---")
    results = await asyncio.gather(
        *(subagent.run(config, task) for task in tasks),
        return_exceptions=True,
    )

    for task, result in zip(tasks, results):
        status = "FAIL" if isinstance(result, Exception) else "done"
        detail = str(result) if isinstance(result, Exception) else ""
        log(f"  [{status}] {task['title']}  {detail}")

    # ── 4. Lead: synthesize findings into final report ──────────────────
    log("\n--- Synthesizing findings (may trigger remediation rounds) ---")
    await lead.synthesize(config)

    report_path = config.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        log(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        log("\nWarning: report.md not found — check workspace for outputs")


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
    args = parser.parse_args()

    config = Config(
        backend=Backend(args.backend),
        workspace=args.workspace,
        max_remediation_rounds=args.max_remediation_rounds,
    )
    config.workspace.mkdir(parents=True, exist_ok=True)
    (config.workspace / "findings").mkdir(exist_ok=True)

    print("=" * 50)
    print("  Deep Research - Multi-Agent Research System")
    print("=" * 50)

    # ── 1. Receptionist: gather research brief ──────────────────────────
    from agents import receptionist

    brief = await receptionist.run(config)

    await run_pipeline(config, brief)


if __name__ == "__main__":
    asyncio.run(main())
