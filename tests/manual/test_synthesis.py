import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
from config import Config, Backend
from agents import lead
from dotenv import load_dotenv


async def test_synthesis():
    load_dotenv()
    config = Config(
        backend=Backend.CLI,
        workspace=Path("./tests/workspace_test"),
        lead_model="sonnet",
    )
    print("\n--- Synthesizing findings ---")
    await lead.synthesize(config)

    report_path = config.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        print(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        print("\nWarning: report.md not found")


if __name__ == "__main__":
    asyncio.run(test_synthesis())
