import sys
from pathlib import Path
import asyncio
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import Config, Backend
from agents import lead


async def run_remediation_test():
    load_dotenv()

    # Use a specific workspace for this test
    workspace_path = Path("./tests/workspace_test_simple")
    if workspace_path.exists():
        import shutil

        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)
    findings_dir = workspace_path / "findings"
    findings_dir.mkdir(exist_ok=True)

    # Mock an incomplete findings report
    (findings_dir / "T1.md").write_text(
        "# Initial Findings\n\nThe topic of 'Deep Research RLHF' was investigated, but no specific technical blog posts from late 2025 were found. The evidence is very thin."
    )

    # Use CLI backend for Gemini
    cfg = Config(
        backend=Backend.CLI,
        workspace=workspace_path,
        max_remediation_rounds=1,
    )

    print("\n" + "=" * 50)
    print("  [REMEDIATION TEST SIMPLE] STARTING CLI TEST")
    print("=" * 50)

    print("\n--- [REMEDIATION TEST SIMPLE] Synthesizing (Remediation expected) ---")
    # This will call synthesize(), which handles remediation internally
    # In CLI mode, synthesize() uses a loop to handle remediation
    try:
        # Increase debug output for this test
        os.environ["DEBUG_GEMINI_CLI"] = "1"
        result = await lead.synthesize(cfg)
        print("\nFinal Synthesis result (Markdown or JSON):")
        print("-" * 30)
        print(result)
        print("-" * 30)
    except Exception as e:
        print(f"\nERROR: {e}")

    report_path = cfg.workspace / "report.md"
    if report_path.exists():
        print(f"\nFinal report written to {report_path}")
    else:
        print(
            "\nNOTE: report.md not found (might still be in remediation if test was cut short)"
        )

if __name__ == "__main__":
    asyncio.run(run_remediation_test())
