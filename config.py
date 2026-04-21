from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Backend(Enum):
    API = "api"
    CLI = "cli"


@dataclass
class Config:
    backend: Backend = Backend.API
    workspace: Path = field(default_factory=lambda: Path("./workspace"))

    # Models
    receptionist_model: str = "claude-sonnet-4-6"
    lead_model: str = "claude-opus-4-6"
    subagent_model: str = "gemini-3-flash-preview"

    # Limits
    max_subagents: int = 5
    max_tokens: int = 16384
