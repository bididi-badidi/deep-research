"""Manual integration test for the lead agent (CLI backend).

Simulates a receptionist output by providing a hard-coded brief, then runs
lead.plan() and lead.synthesize() end-to-end against real Gemini CLI.

Usage:
    python test_lead_cli.py          # runs both plan + synthesize
    python test_lead_cli.py plan     # plan only
    python test_lead_cli.py synth    # synthesize only (requires plan.json in workspace)
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
import json
import shutil
import sys
from pathlib import Path

from config import Backend, Config
from agents import lead

# ---------------------------------------------------------------------------
# Predefined receptionist output
# ---------------------------------------------------------------------------

BRIEF = {
    "topic": "The impact of large language models on software engineering productivity",
    "scope": (
        "Focus on empirical studies and industry surveys published 2022–2025. "
        "Exclude purely theoretical papers and marketing claims."
    ),
    "questions": (
        "1. What measurable productivity gains (or losses) do developers report?\n"
        "2. Which tasks benefit most (code generation, debugging, documentation)?\n"
        "3. What are the main risks (code quality, security, skill atrophy)?\n"
        "4. How do different LLM tools (Copilot, Cursor, Claude Code) compare?"
    ),
    "depth": "moderate",
    "output_preferences": "Executive summary followed by section-by-section analysis. Use tables where helpful.",
}

# ---------------------------------------------------------------------------
# Test workspace
# ---------------------------------------------------------------------------

WORKSPACE = Path("./workspace_lead_test")


def _setup_workspace():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "findings").mkdir(exist_ok=True)


def _teardown_workspace():
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)


def _make_config() -> Config:
    return Config(
        backend=Backend.CLI,
        workspace=WORKSPACE,
        subagent_model="gemini-3-flash-preview",
        max_subagents=5,
        max_tokens=8192,
        max_remediation_rounds=2,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def _inject_stub_findings(workspace: Path):
    """Write minimal stub findings so synthesize() has something to work with
    even if subagents are not run (plan-only mode followed by synth-only)."""
    findings_dir = workspace / "findings"
    findings_dir.mkdir(exist_ok=True)
    stub = findings_dir / "stub-task.md"
    if not stub.exists():
        stub.write_text(
            "# Stub Findings\n\n"
            "This file was created by the test harness as a placeholder.\n"
            "No real subagents were run. The lead synthesis should request "
            "more research via dispatch_subagents JSON, or write a best-effort report.\n"
        )
        print("  [test] Wrote stub findings (no subagent run detected).")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

async def test_plan(config: Config) -> list[dict]:
    _print_section("PHASE 1 — lead.plan()")
    print(f"Brief:\n{json.dumps(BRIEF, indent=2)}\n")

    tasks = await lead.plan(config, BRIEF)

    _print_section("RESULT — Research plan")
    print(json.dumps(tasks, indent=2))

    plan_path = config.workspace / "plan.json"
    assert plan_path.exists(), "plan.json was not written to workspace"
    assert isinstance(tasks, list) and len(tasks) > 0, "Plan is empty"
    for t in tasks:
        assert "id" in t, f"Task missing 'id': {t}"
        assert "title" in t, f"Task missing 'title': {t}"
        assert "objective" in t, f"Task missing 'objective': {t}"

    print(f"\n[PASS] plan() returned {len(tasks)} task(s) and wrote plan.json.")
    return tasks


async def test_synthesize(config: Config):
    _print_section("PHASE 2 — lead.synthesize()")

    _inject_stub_findings(config.workspace)

    result = await lead.synthesize(config)

    _print_section("RESULT — Synthesis output")
    print(result[:2000] + ("..." if len(result) > 2000 else ""))

    report_path = config.workspace / "report.md"
    assert report_path.exists(), "report.md was not written to workspace"
    assert len(result) > 100, "Synthesis output suspiciously short"

    print(f"\n[PASS] synthesize() completed. report.md written ({report_path.stat().st_size} bytes).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    config = _make_config()
    _setup_workspace()

    try:
        if mode in ("all", "plan"):
            await test_plan(config)

        if mode in ("all", "synth"):
            await test_synthesize(config)

    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        raise
    finally:
        print(f"\nWorkspace preserved at: {WORKSPACE.resolve()}")
        print("Run `rm -rf workspace_lead_test` to clean up.")


if __name__ == "__main__":
    asyncio.run(main())
