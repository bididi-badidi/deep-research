import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
from config import Config, Backend
from agents import lead, subagent
from dotenv import load_dotenv


async def test_cli_pipeline():
    load_dotenv()
    # Use a specific workspace for this example
    workspace_path = Path("./tests/workspace_test")
    cfg = Config(backend=Backend.CLI, workspace=workspace_path)
    cfg.workspace.mkdir(parents=True, exist_ok=True)
    (cfg.workspace / "findings").mkdir(exist_ok=True)

    # Use flash for faster testing in examples
    cfg.subagent_model = "flash"

    brief = {
        "topic": "CEO of Anthropic",
        "scope": "Current leadership",
        "questions": "Who is the current CEO of Anthropic? What is their background?",
        "depth": "overview",
    }

    print("\n--- [CLI] Planning ---")
    tasks = await lead.plan(cfg, brief)
    print(f"Created {len(tasks)} tasks.")

    print("\n--- [CLI] Executing Subagents ---")
    # Run in parallel
    results = await asyncio.gather(
        *(subagent.run(cfg, task) for task in tasks), return_exceptions=True
    )

    for task, result in zip(tasks, results):
        status = "FAIL" if isinstance(result, Exception) else "DONE"
        task_id = task.get("id") or task.get("task_id") or "unknown"
        task_title = task.get("title") or task.get("name") or "Task"
        print(f"  [{status}] {task_id}: {task_title}")
        if isinstance(result, Exception):
            print(f"    Error: {result}")

    print("\n--- [CLI] Synthesizing ---")
    await lead.synthesize(cfg)

    report_path = cfg.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        print(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        print("\nERROR: report.md not found!")


if __name__ == "__main__":
    asyncio.run(test_cli_pipeline())
