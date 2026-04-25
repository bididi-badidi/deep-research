import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import Config, Backend
from agents import lead


async def run_synthesis_only():
    load_dotenv()

    workspace_path = Path("./tests/workspace")
    if not workspace_path.exists():
        print("Error: workspace not found!")
        return

    cfg = Config(
        backend=Backend.CLI,
        workspace=workspace_path,
        max_remediation_rounds=1,
        lead_model="gemini-3-flash-preview",
        subagent_model="gemini-3-flash-preview",
    )

    print(
        "\n--- [REMEDIATION TEST] Synthesizing (Remediation expected due to missing findings) ---"
    )
    await lead.synthesize(cfg)

    report_path = cfg.workspace / "report.md"
    if report_path.exists():
        size = len(report_path.read_text())
        print(f"\nFinal report written to {report_path} ({size:,} chars)")
    else:
        print(
            "\nNote: report.md not found — this is expected if remediation was triggered."
        )


if __name__ == "__main__":
    asyncio.run(run_synthesis_only())
