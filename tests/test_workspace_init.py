import asyncio
from pathlib import Path
from config import Config
from utils import initialize_research_workspace


async def test_init():
    config = Config(workspace=Path("./test_workspace"))
    topic = "Test Research Topic"

    research_id = initialize_research_workspace(config, topic)

    print(f"Research ID: {research_id}")
    print(f"Config Workspace: {config.workspace}")

    assert research_id.startswith("test-research-topic-")
    assert config.workspace == Path("./test_workspace") / research_id
    assert config.workspace.exists()
    assert (config.workspace / "findings").exists()

    print("Test passed!")

    # Cleanup
    import shutil

    shutil.rmtree("./test_workspace")


if __name__ == "__main__":
    asyncio.run(test_init())
