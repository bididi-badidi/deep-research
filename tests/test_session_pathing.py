import asyncio
from pathlib import Path
import shutil
from tools import execute as tool_execute
from config import Config


async def test_session_pathing():
    # 1. Setup session-specific workspace
    base_ws = Path("/tmp/deep-research-test").resolve()
    if base_ws.exists():
        shutil.rmtree(base_ws)

    session_id = "test-research-2026"
    session_ws = base_ws / session_id
    session_ws.mkdir(parents=True)
    (session_ws / "findings").mkdir()

    config = Config(workspace=session_ws)

    print(f"Session workspace: {config.workspace}")

    # 2. Simulate agent writing findings
    # Agent thinks its root is session_ws, so it writes to 'findings/T-01.md'
    write_args = {"path": "findings/T-01.md", "content": "# Test Findings\nSuccess."}

    print(f"Agent writing to: {write_args['path']}")
    result = await tool_execute("write_file", write_args, workspace=config.workspace)
    print(f"Result: {result}")

    # 3. Verify physical location
    expected_path = base_ws / session_id / "findings" / "T-01.md"
    print(f"Checking expected physical path: {expected_path}")

    if expected_path.exists():
        print("✅ SUCCESS: File is in the correct session folder.")
        content = expected_path.read_text()
        print(f"Content matches: {content == write_args['content']}")
    else:
        print("❌ FAILURE: File not found at expected location.")
        # Check if it leaked to base_ws or project root
        if (base_ws / "findings" / "T-01.md").exists():
            print("❌ LEAK: File leaked to base workspace root.")
        elif Path("findings/T-01.md").exists():
            print("❌ LEAK: File leaked to project root.")


if __name__ == "__main__":
    asyncio.run(test_session_pathing())
