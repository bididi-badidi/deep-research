
from pathlib import Path
from config import Config, Backend

def test_config_defaults():
    cfg = Config()
    assert cfg.backend == Backend.API
    assert cfg.workspace == Path("./workspace")
    assert "sonnet" in cfg.receptionist_model.lower()
    assert any(m in cfg.lead_model.lower() for m in ["sonnet", "opus"])
    assert "flash" in cfg.subagent_model.lower()

def test_config_overrides():
    cfg = Config(backend=Backend.CLI, workspace=Path("/tmp/ws"))
    assert cfg.backend == Backend.CLI
    assert cfg.workspace == Path("/tmp/ws")
