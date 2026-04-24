import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import Config, Backend
from agents import lead, subagent


async def run_remediation_test():
    load_dotenv()

    # Use a specific workspace for this test
    workspace_path = Path("./tests/workspace_test")
    if workspace_path.exists():
        import shutil

        shutil.rmtree(workspace_path)

    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "findings").mkdir(exist_ok=True)

    # Use CLI backend for Gemini
    cfg = Config(
        backend=Backend.CLI,
        workspace=workspace_path,
        max_remediation_rounds=1,
        # Default CLI models
        receptionist_model="gemini-3-flash-preview",
        lead_model="gemini-3-flash-preview",
        subagent_model="gemini-3-flash-preview",
    )

    # A complex query designed to potentially trigger remediation
    brief = {
        "topic": "Deep Research RLHF techniques",
        "scope": "Comparison of OpenAI Deep Research vs Google Search with Reasoning (2026)",
        "questions": "Do they use Q* or Process Supervision? What are the core differences in their RLHF implementation? Find specific technical blog posts or papers from late 2025/early 2026.",
        "depth": "forensic",
        "audience": "AI researchers",
    }

    print("\n" + "=" * 50)
    print("  [REMEDIATION TEST] STARTING CLI TEST")
    print("=" * 50)

    print("\n--- [REMEDIATION TEST] Planning ---")
    tasks = await lead.plan(cfg, brief)
    print(f"Created {len(tasks)} tasks:")
    for t in tasks:
        print(f"  - {t['id']}: {t['title']} (Profile: {t.get('tool_profile', 'full')})")

    print("\n--- [REMEDIATION TEST] Executing Initial Subagents ---")
    # Run in parallel
    results = await asyncio.gather(
        *(subagent.run(cfg, task) for task in tasks), return_exceptions=True
    )

    for task, result in zip(tasks, results):
        status = "FAIL" if isinstance(result, Exception) else "DONE"
        task_id = task.get("id") or "unknown"
        print(f"  [{status}] {task_id}")
        if isinstance(result, Exception):
            print(f"    Error: {result}")

    print("\n--- [REMEDIATION TEST] Synthesizing (Remediation possible) ---")
    # This will call synthesize(), which handles remediation internally
    # In CLI mode, synthesize() uses a loop to handle remediation
    await lead.synthesize(cfg)

    report_path = cfg.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        print(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        print("\nERROR: report.md not found!")


if __name__ == "__main__":
    asyncio.run(run_remediation_test())
