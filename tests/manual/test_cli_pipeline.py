
import asyncio
import os
import json
from pathlib import Path
from config import Config, Backend
from agents import lead, subagent

async def test_cli_pipeline():
    # Load env for gemini cli (if needed by the tool itself, 
    # though our provider handles its own env)
    # The user's .env has GEMINI_API_KEY which the gemini CLI uses.
    
    cfg = Config(backend=Backend.CLI, workspace=Path("./workspace_cli"))
    cfg.workspace.mkdir(parents=True, exist_ok=True)
    (cfg.workspace / "findings").mkdir(exist_ok=True)
    
    # Gemini 3.1 Pro is our lead now
    brief = {
        "topic": "Population of Tokyo 2026",
        "scope": "Current population estimates for Tokyo metropolis and greater area.",
        "questions": "What is the latest population? How does it compare to previous years?",
        "depth": "moderate"
    }
    
    print("\n--- [CLI] Planning ---")
    tasks = await lead.plan(cfg, brief)
    print(f"Created {len(tasks)} tasks.")
    
    print("\n--- [CLI] Executing Subagents ---")
    # Run in parallel
    results = await asyncio.gather(
        *(subagent.run(cfg, task) for task in tasks),
        return_exceptions=True
    )
    
    for task, result in zip(tasks, results):
        status = "FAIL" if isinstance(result, Exception) else "DONE"
        task_id = task.get("id", "unknown")
        task_title = task.get("title") or task.get("name") or "Task"
        print(f"  [{status}] {task_id}: {task_title}")
        if isinstance(result, Exception):
            print(f"    Error: {result}")
            
    print("\n--- [CLI] Synthesizing ---")
    report = await lead.synthesize(cfg)
    
    report_path = cfg.workspace / "report.md"
    if report_path.exists():
        print(f"\nReport written to {report_path}")
        # print(report_path.read_text()[:500] + "...")
    else:
        print("\nERROR: report.md not found!")

if __name__ == "__main__":
    asyncio.run(test_cli_pipeline())
