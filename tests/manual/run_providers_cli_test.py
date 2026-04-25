import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
from providers.claude_cli import run as run_claude
from providers.gemini_cli import run as run_gemini


async def test_claude():
    print("\n--- Testing Claude CLI ---")
    try:
        res = await run_claude(
            model="claude-sonnet-4-6",
            system="You are a researcher.",
            prompt="Hello, I am a researcher.",
            workspace="./tests/workspace",
        )
        print(f"RESULT: {res}")
    except Exception as e:
        print(f"ERROR: {e}")


async def test_gemini():
    print("\n--- Testing Gemini CLI ---")
    try:
        res = await run_gemini(
            model="gemini-2.0-flash-exp",
            system="You are a researcher.",
            prompt="Hello, I am a researcher.",
            workspace="./tests/workspace",
        )
        print(f"RESULT: {res}")
    except Exception as e:
        print(f"ERROR: {e}")


async def main():
    await test_claude()
    await test_gemini()


if __name__ == "__main__":
    asyncio.run(main())
