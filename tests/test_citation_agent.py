import json
from pathlib import Path

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


@pytest.mark.asyncio
async def test_citation_agent_audits_urls_not_checked_by_model(tmp_path, monkeypatch):
    workspace = tmp_path
    (workspace / "report.md").write_text(
        "# Report\n\nA cited claim (https://example.com/skipped).",
        encoding="utf-8",
    )

    async def fake_provider(**kwargs):
        await kwargs["tool_executor"](
            "write_file",
            {
                "path": "report.md",
                "content": "# Report\n\nA cited claim (Example, 2026).",
            },
        )
        return "done"

    monkeypatch.setattr(citation, "get_provider", lambda backend, name: fake_provider)

    await citation.run(Config(workspace=workspace), {"topic": "x"})

    audit = json.loads((workspace / "citation_report.json").read_text())
    assert audit["verified_count"] == 0
    assert audit["urls"] == [
        {
            "url": "https://example.com/skipped",
            "reachable": "not_checked",
            "error": "Citation agent did not call verify_url for this URL.",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("citation_format", ["MLA", "Chicago"])
async def test_citation_agent_uses_requested_format_variants(
    tmp_path, monkeypatch, citation_format
):
    workspace = tmp_path
    (workspace / "report.md").write_text(
        "# Report\n\nA cited claim (https://example.com/source).",
        encoding="utf-8",
    )
    captured = {}

    async def fake_provider(**kwargs):
        captured["system"] = kwargs["system"]
        await kwargs["tool_executor"](
            "verify_url", {"url": "https://example.com/source"}
        )
        await kwargs["tool_executor"](
            "write_file",
            {
                "path": "report.md",
                "content": f"# Report\n\nA {citation_format} cited claim.",
            },
        )
        return "done"

    monkeypatch.setattr(citation, "get_provider", lambda backend, name: fake_provider)

    await citation.run(
        Config(workspace=workspace, verify_urls=False),
        {"topic": "x", "output_preferences": {"citation_format": citation_format}},
    )

    audit = json.loads((workspace / "citation_report.json").read_text())
    assert f"Citation format: {citation_format}" in captured["system"]
    assert audit["citation_format"] == citation_format


@pytest.mark.asyncio
async def test_pipeline_with_sample_brief_runs_citation_stage(tmp_path, monkeypatch):
    from agents import lead, subagent
    from main import run_pipeline

    brief = json.loads(
        Path("examples/brief_plans/research_brief.json").read_text(encoding="utf-8")
    )
    config = Config(workspace=tmp_path, verify_urls=False)

    async def fake_plan(config, brief):
        (config.workspace / "plan.json").write_text(
            json.dumps(
                [
                    {
                        "id": "frameworks",
                        "title": "Compare frameworks",
                        "objective": "Compare RAGAS, DeepEval, and HELM.",
                        "search_hints": [],
                        "tool_profile": "full",
                    }
                ]
            ),
            encoding="utf-8",
        )
        return json.loads((config.workspace / "plan.json").read_text())

    async def fake_subagent(config, task):
        findings_dir = config.workspace / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)
        (findings_dir / f"{task['id']}.md").write_text(
            "RAGAS provides RAG metrics. https://example.com/ragas",
            encoding="utf-8",
        )
        return "done"

    async def fake_synthesize(config):
        (config.workspace / "report.md").write_text(
            "# Report\n\nRAGAS provides RAG metrics. https://example.com/ragas",
            encoding="utf-8",
        )
        return "done"

    async def fake_citation(config, brief):
        report_path = config.workspace / "report.md"
        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + "\n\n## Full Source List\n\n- https://example.com/ragas",
            encoding="utf-8",
        )
        (config.workspace / "citation_report.json").write_text(
            json.dumps({"citation_format": "APA", "citation_count": 1}),
            encoding="utf-8",
        )
        return str(report_path)

    monkeypatch.setattr(lead, "plan", fake_plan)
    monkeypatch.setattr(subagent, "run", fake_subagent)
    monkeypatch.setattr(lead, "synthesize", fake_synthesize)
    monkeypatch.setattr(citation, "run", fake_citation)

    await run_pipeline(config, brief)

    assert (tmp_path / "plan.json").exists()
    assert (tmp_path / "findings" / "frameworks.md").exists()
    assert "## Full Source List" in (tmp_path / "report.md").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / "citation_report.json").exists()


@pytest.mark.asyncio
async def test_pipeline_skip_citation_leaves_report_unchanged(tmp_path, monkeypatch):
    from agents import lead, subagent
    from main import run_pipeline

    config = Config(workspace=tmp_path)
    original_report = "# Report\n\nNo citation post-processing."

    async def fake_plan(config, brief):
        return [
            {
                "id": "task-1",
                "title": "Task 1",
                "objective": "Write a finding.",
                "search_hints": [],
            }
        ]

    async def fake_subagent(config, task):
        (config.workspace / "findings").mkdir(parents=True, exist_ok=True)
        return "done"

    async def fake_synthesize(config):
        (config.workspace / "report.md").write_text(original_report, encoding="utf-8")
        return "done"

    async def fail_if_called(config, brief):
        raise AssertionError("citation agent should not run")

    monkeypatch.setattr(lead, "plan", fake_plan)
    monkeypatch.setattr(subagent, "run", fake_subagent)
    monkeypatch.setattr(lead, "synthesize", fake_synthesize)
    monkeypatch.setattr(citation, "run", fail_if_called)

    await run_pipeline(config, {"topic": "x"}, skip_citation=True)

    assert (tmp_path / "report.md").read_text(encoding="utf-8") == original_report
    assert not (tmp_path / "citation_report.json").exists()
