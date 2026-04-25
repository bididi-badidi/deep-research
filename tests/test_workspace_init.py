import asyncio
from pathlib import Path
from config import Config
from utils import initialize_research_workspace


async def test_init(tmp_path):
    test_workspace = tmp_path / "test_workspace"
    config = Config(workspace=test_workspace)
    topic = "Test Research Topic"

    research_id = initialize_research_workspace(config, topic)

    assert research_id.startswith("test-research-topic-")
    assert config.workspace == test_workspace / research_id
    assert config.workspace.exists()
    assert (config.workspace / "findings").exists()
