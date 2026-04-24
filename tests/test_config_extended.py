import os
import pytest
from pathlib import Path
from config import Config, Backend

def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("MAX_SUBAGENTS", "20")
    monkeypatch.setenv("WORKSPACE", "./custom_ws")
    monkeypatch.setenv("VERBOSE", "true")
    
    cfg = Config()
    assert cfg.max_subagents == 20
    assert cfg.workspace == Path("./custom_ws")
    assert cfg.verbose is True

def test_config_backend_defaults():
    # API Backend
    cfg_api = Config(backend=Backend.API)
    assert "claude-sonnet" in cfg_api.receptionist_model
    assert "claude-opus" in cfg_api.lead_model
    
    # CLI Backend
    cfg_cli = Config(backend=Backend.CLI)
    assert "gemini" in cfg_cli.receptionist_model
    assert "gemini" in cfg_cli.lead_model

def test_config_validation_numeric():
    cfg = Config(max_subagents=0)
    with pytest.raises(ValueError, match="max_subagents must be > 0"):
        cfg.validate()

def test_config_validation_api_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    cfg = Config(backend=Backend.API)
    # By default, API mode uses Anthropic for receptionist/lead
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
        cfg.validate()
    
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # Subagent is Gemini by default, so it should still fail for Gemini key
    with pytest.raises(ValueError, match="GOOGLE_API_KEY or GEMINI_API_KEY is required"):
        cfg.validate()
    
    monkeypatch.setenv("GOOGLE_API_KEY", "gt-test")
    # Now it should pass
    cfg.validate()
