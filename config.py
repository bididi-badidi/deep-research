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

    receptionist_model: str = "gemini-3-flash-preview"
    lead_model: str = "gemini-3-flash-preview"
    subagent_model: str = "gemini-3-flash-preview"

    # Limits
    max_subagents: int = 15
    max_tokens: int = 16384
    max_remediation_rounds: int = 5

    def __post_init__(self) -> None:
        if self.receptionist_model is None:
            self.receptionist_model = (
                "claude-sonnet-4-6"
                if self.backend == Backend.API
                else "gemini-3-flash-preview"
            )
        if self.lead_model is None:
            self.lead_model = (
                "claude-opus-4-6"
                if self.backend == Backend.API
                else "gemini-3-pro-preview"
            )
