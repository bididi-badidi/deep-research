"""Interactive receptionist runner — type your own responses.

Usage:
    python tests/manual/run_receptionist.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from config import Backend, Config
from agents import receptionist


async def main():
    load_dotenv()
    config = Config(
        backend=Backend.CLI,
        workspace=Path("./workspace_receptionist_test"),
        subagent_model="gemini-3-flash-preview",
        max_tokens=2048,
    )
    config.workspace.mkdir(parents=True, exist_ok=True)

    brief = await receptionist.run(config)
    print("\nFinal brief:")
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
