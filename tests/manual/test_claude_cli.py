import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
import os
from providers.claude_cli import run

async def main():
    try:
        res = await run(
            model="claude-sonnet-4-6",
            system="You are a researcher.",
            prompt="Hello, I am a researcher.",
            workspace="./workspace_test"
        )
        print(f"RESULT: {res}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
