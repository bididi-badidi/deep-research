import json

import pytest

from agents import citation
from config import Config


@pytest.mark.asyncio
async def test_citation_agent_writes_report_and_audit(tmp_path, monkeypatch):
    workspace = tmp_path
    (workspace / "report.md").write_text(
        "# Report\n\nA cited claim (https://example.com/source).",
        encoding="utf-8",
    )

    async def fake_provider(**kwargs):
        await kwargs["tool_executor"](
            "verify_url", {"url": "https://example.com/source"}
        )
        await kwargs["tool_executor"](
            "write_file",
            {
                "path": "report.md",
                "content": (
                    "# Report\n\nA cited claim (Example, 2026)."
                    "\n\n## Full Source List\n\n"
                    "- Example. https://example.com/source"
                ),
            },
        )
        return "done"

    monkeypatch.setattr(citation, "get_provider", lambda backend, name: fake_provider)

    config = Config(workspace=workspace, verify_urls=False)
    result = await citation.run(
        config,
        {"topic": "x", "output_preferences": {"citation_format": "APA"}},
    )

    assert result == str(workspace / "report.md")
    assert "## Full Source List" in (workspace / "report.md").read_text(
        encoding="utf-8"
    )

    audit = json.loads((workspace / "citation_report.json").read_text())
    assert audit["citation_format"] == "APA"
    assert audit["citation_count"] == 1
    assert audit["verified_count"] == 1
    assert audit["urls"][0]["reachable"] == "skipped"
