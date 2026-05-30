from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Backend(Enum):
    API = "api"
    CLI = "cli"


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got '{raw}'")


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Environment variable {name} must be a boolean, got '{raw}'")


@dataclass
class Config:
    backend: Backend = Backend.API
    workspace: Path = field(
        default_factory=lambda: Path(os.getenv("WORKSPACE", "./workspace"))
    )

    receptionist_model: str | None = None
    lead_model: str | None = None
    subagent_model: str | None = None
    citation_model: str | None = None
    verify_urls: bool = field(default_factory=lambda: _get_env_bool("VERIFY_URLS", True))

    # Limits
    max_subagents: int = field(
        default_factory=lambda: _get_env_int("MAX_SUBAGENTS", 15)
    )
    max_tokens: int = field(default_factory=lambda: _get_env_int("MAX_TOKENS", 16384))
    max_remediation_rounds: int = field(
        default_factory=lambda: _get_env_int("MAX_REMEDIATION_ROUNDS", 5)
    )
    timeout_seconds: int = field(
        default_factory=lambda: _get_env_int("TIMEOUT_SECONDS", 900)
    )

    verbose: bool = field(
        default_factory=lambda: os.getenv("VERBOSE", "false").lower() == "true"
    )

    def __post_init__(self) -> None:
        # 1. Resolve Receptionist Model
        if self.receptionist_model is None:
            self.receptionist_model = os.getenv("RECEPTIONIST_MODEL")
        if self.receptionist_model is None:
            self.receptionist_model = (
                "claude-sonnet-4-6"
                if self.backend == Backend.API
                else "gemini-3-flash-preview"
            )

        # 2. Resolve Lead Model
        if self.lead_model is None:
            self.lead_model = os.getenv("LEAD_MODEL")
        if self.lead_model is None:
            self.lead_model = (
                "claude-opus-4-6"
                if self.backend == Backend.API
                else "gemini-3-pro-preview"
            )

        # 3. Resolve Subagent Model
        if self.subagent_model is None:
            self.subagent_model = os.getenv("SUBAGENT_MODEL", "gemini-3-flash-preview")

        # 4. Resolve Citation Model. The citation agent intentionally uses the
        # Anthropic API provider even when the research backend is CLI.
        if self.citation_model is None:
            self.citation_model = os.getenv("CITATION_MODEL", "claude-sonnet-4-6")

    def validate(self) -> None:
        """Validate configuration constraints and required environment variables."""
        if self.max_subagents <= 0:
            raise ValueError(f"max_subagents must be > 0, got {self.max_subagents}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be > 0, got {self.max_tokens}")
        if self.timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got {self.timeout_seconds}")

        from utils import get_provider_name

        required_providers = set()
        if self.citation_model:
            required_providers.add(get_provider_name(self.citation_model))

        if self.backend == Backend.API:
            for model in [
                self.receptionist_model,
                self.lead_model,
                self.subagent_model,
            ]:
                if model:
                    required_providers.add(get_provider_name(model))

        if "anthropic" in required_providers and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError(
                "ANTHROPIC_API_KEY is required for Anthropic models used by the API-backed citation agent"
            )
        if "gemini" in required_providers:
            if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
                raise ValueError(
                    "GOOGLE_API_KEY or GEMINI_API_KEY is required for Gemini models in API mode"
                )
