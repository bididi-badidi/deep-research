"""Manual integration tests for the receptionist agent.

Covers:
  TC-1  Single-turn rich input  — user gives enough info upfront; brief extracted in ≤3 turns.
  TC-2  Multi-turn clarification — user starts vague; receptionist asks follow-ups; brief extracted.
  TC-3  Explicit confirmation    — user must say "yes" / "looks good" to trigger JSON brief.
  TC-4  Quit / cancel mid-intake — user types "quit"; KeyboardInterrupt is raised cleanly.
  TC-5  Brief → lead.plan()     — receptionist output feeds lead.plan(); plan.json written.

All tests run against the real Gemini CLI.  User input is simulated via
`unittest.mock.patch('builtins.input', side_effect=[...])`.

Usage:
    python tests/manual/run_receptionist_suite.py          # run all tests
    python tests/manual/run_receptionist_suite.py tc1      # single test
    python tests/manual/run_receptionist_suite.py tc5      # integration (receptionist → lead)

Flags:
    --keep   keep the test workspace after a run (default: delete on pass)
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

# Make project root importable regardless of invocation directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

from config import Backend, Config
from agents import receptionist, lead


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

WORKSPACE = Path("./tests/workspace/receptionist")

REQUIRED_BRIEF_KEYS = {"topic", "scope", "questions", "depth"}


def _print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _make_config() -> Config:
    return Config(
        backend=Backend.CLI,
        workspace=WORKSPACE,
        subagent_model="gemini-3-flash-preview",
        max_tokens=2048,
    )


def _setup():
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "findings").mkdir(exist_ok=True)


def _teardown():
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)


def _assert_brief(brief: dict, label: str = ""):
    prefix = f"[{label}] " if label else ""
    missing = REQUIRED_BRIEF_KEYS - brief.keys()
    assert not missing, f"{prefix}Brief missing required keys: {missing}"
    for key in REQUIRED_BRIEF_KEYS:
        assert brief[key], f"{prefix}Brief key '{key}' is empty"
    print(f"\n{prefix}Brief validated: {json.dumps(brief, indent=2)}")


# ---------------------------------------------------------------------------
# TC-1: Single-turn rich input
# ---------------------------------------------------------------------------


async def tc1_single_turn_rich_input(config: Config):
    """User provides a complete, detailed request in the first message.

    Expected behaviour: the receptionist should present the brief and
    ask for confirmation in one pass.  The test then confirms it, and
    the JSON brief should be returned within 3 total user turns.
    """
    _print_section("TC-1 — Single-turn rich input")

    # Turn 1 : rich initial description
    # Turn 2 : confirmation ("yes, proceed")
    # (Turn 3 is a safety fallback in case the model asks one follow-up)
    scripted_inputs = [
        (
            "I want a deep-dive research report on the environmental impact of "
            "large-scale Bitcoin mining.  Scope: focus on energy consumption and "
            "carbon emissions from 2020 to 2024 using peer-reviewed sources.  "
            "Key questions: (1) How much electricity does Bitcoin mining consume globally? "
            "(2) What percentage comes from renewables? (3) How does "
            "this compare to traditional banking?  Depth: deep. "
            "Output: executive summary for about 2 pages."
            "No specific priority for materials, no specific sources to avoid."
            "Target Audience: students. Deadline: today, no specific aspect of research to prioritize if time is limited."
        ),
        "Yes, that looks good. Please proceed.",
        "Confirmed, go ahead.",
    ]

    with patch("builtins.input", side_effect=scripted_inputs):
        brief = await receptionist.run(config)

    _assert_brief(brief, "TC-1")
    assert "bitcoin" in brief["topic"].lower() or "mining" in brief["topic"].lower(), (
        "TC-1: expected topic to mention Bitcoin or mining"
    )
    print("\n[PASS] TC-1 — Single-turn rich input")
    return brief


# ---------------------------------------------------------------------------
# TC-2: Multi-turn clarification
# ---------------------------------------------------------------------------


async def tc2_multi_turn_clarification(config: Config):
    """User starts vague; the receptionist must ask follow-up questions.

    The test simulates 4-5 turns where the user gradually fills in the
    scope, questions, and depth before finally confirming.
    """
    _print_section("TC-2 — Multi-turn clarification")

    scripted_inputs = [
        # Turn 1: intentionally vague
        "I want to research quantum computing.",
        # Turn 2: receptionist will ask about scope / questions / depth; user narrows scope
        "Focus on quantum computing applications in drug discovery, published research from 2021 to 2025.",
        # Turn 3: user supplies key questions
        (
            "Key questions: (1) Which quantum algorithms are most promising for "
            "molecular simulation? (2) What milestones have been reached in the last "
            "3 years? (3) What are the main technical barriers? Depth: moderate."
        ),
        # Turn 4: confirmation
        "Yes, that covers everything. Proceed.",
        # Safety fallback
        "Go ahead, confirmed.",
    ]

    with patch("builtins.input", side_effect=scripted_inputs):
        brief = await receptionist.run(config)

    _assert_brief(brief, "TC-2")
    assert "quantum" in brief["topic"].lower(), (
        "TC-2: expected topic to mention quantum"
    )
    print("\n[PASS] TC-2 — Multi-turn clarification")
    return brief


# ---------------------------------------------------------------------------
# TC-3: Explicit confirmation gate
# ---------------------------------------------------------------------------


async def tc3_explicit_confirmation(config: Config):
    """Verifies that the receptionist does NOT submit the brief until
    the user explicitly confirms.

    Turn 1 : complete brief description
    Turn 2 : user says "not yet, change depth to deep"
    Turn 3 : user confirms
    """
    _print_section("TC-3 — Explicit confirmation gate")

    scripted_inputs = [
        # Turn 1: full description
        (
            "Research the regulatory landscape for autonomous vehicles in the EU "
            "and US.  Scope: compare frameworks from 2020–2025.  Questions: "
            "(1) What are the key differences? (2) Which jurisdiction is more "
            "permissive? (3) What upcoming legislation is expected?  Depth: overview."
        ),
        # Turn 2: user requests a change instead of confirming
        "Actually, change the depth to deep, not overview.",
        # Turn 3: confirmation
        "Yes, that's correct now. Please go ahead.",
        # Fallback
        "Confirmed.",
    ]

    with patch("builtins.input", side_effect=scripted_inputs):
        brief = await receptionist.run(config)

    _assert_brief(brief, "TC-3")
    # After the change request, depth should be "deep"
    assert brief.get("depth", "").lower() == "deep", (
        f"TC-3: expected depth='deep', got '{brief.get('depth')}'"
    )
    print("\n[PASS] TC-3 — Explicit confirmation gate")
    return brief


# ---------------------------------------------------------------------------
# TC-4: Quit / cancel mid-intake
# ---------------------------------------------------------------------------


async def tc4_quit_cancels_intake(config: Config):
    """User types 'quit' mid-conversation; KeyboardInterrupt must be raised."""
    _print_section("TC-4 — Quit / cancel mid-intake")

    scripted_inputs = [
        "I want to research something...",
        "Actually never mind. quit",
    ]

    raised = False
    try:
        with patch("builtins.input", side_effect=scripted_inputs):
            await receptionist.run(config)
    except KeyboardInterrupt:
        raised = True

    assert raised, "TC-4: expected KeyboardInterrupt when user types 'quit'"
    print("\n[PASS] TC-4 — Quit / cancel mid-intake")


# ---------------------------------------------------------------------------
# TC-5: Receptionist brief → lead.plan() integration
# ---------------------------------------------------------------------------


async def tc5_brief_to_lead_plan(config: Config):
    """End-to-end: receptionist collects a brief → brief feeds lead.plan().

    Verifies:
    - Brief is a valid dict with required keys.
    - lead.plan() returns a non-empty list of task dicts.
    - Each task has 'id', 'title', 'objective', and 'tool_profile'.
    - plan.json is written to the workspace.
    """
    _print_section("TC-5 — Brief → lead.plan() integration")

    scripted_inputs = [
        (
            "Research the current state of open-source large language models in 2024. "
            "Scope: focus on models released by non-profit or community organisations "
            "(e.g., Mistral, Meta LLaMA, Falcon).  Key questions: "
            "(1) What are the top 5 open-source LLMs by capability benchmarks? "
            "(2) How do they compare to closed-source models? "
            "(3) What licensing restrictions apply?  Depth: moderate."
        ),
        "Yes, proceed.",
        "Confirmed.",  # fallback
    ]

    # --- Phase A: receptionist ---
    _print_section("TC-5 Phase A — Receptionist intake")
    with patch("builtins.input", side_effect=scripted_inputs):
        brief = await receptionist.run(config)

    _assert_brief(brief, "TC-5/receptionist")

    # --- Phase B: lead planning ---
    _print_section("TC-5 Phase B — lead.plan()")
    print(f"Brief passed to lead:\n{json.dumps(brief, indent=2)}\n")

    tasks = await lead.plan(config, brief)

    _print_section("TC-5 Result — Research plan")
    print(json.dumps(tasks, indent=2))

    plan_path = config.workspace / "plan.json"
    assert plan_path.exists(), "TC-5: plan.json was not written to workspace"
    assert isinstance(tasks, list) and len(tasks) > 0, "TC-5: plan is empty"

    for t in tasks:
        for key in ("id", "title", "objective", "tool_profile"):
            assert key in t, f"TC-5: task missing '{key}': {t}"

    print(f"\n[PASS] TC-5 — Brief → lead.plan() returned {len(tasks)} task(s).")
    return tasks


# ---------------------------------------------------------------------------
# Test registry & entry point
# ---------------------------------------------------------------------------

ALL_TESTS = {
    "tc1": tc1_single_turn_rich_input,
    "tc2": tc2_multi_turn_clarification,
    "tc3": tc3_explicit_confirmation,
    "tc4": tc4_quit_cancels_intake,
    "tc5": tc5_brief_to_lead_plan,
}


async def main():
    load_dotenv()

    keep_workspace = "--keep" in sys.argv
    requested = [a for a in sys.argv[1:] if not a.startswith("--")]

    tests_to_run = (
        {k: v for k, v in ALL_TESTS.items() if k in requested}
        if requested
        else ALL_TESTS
    )

    if not tests_to_run:
        print(f"Unknown test(s): {requested}.  Available: {list(ALL_TESTS)}")
        sys.exit(1)

    config = _make_config()
    _setup()

    passed, failed = [], []

    for name, test_fn in tests_to_run.items():
        try:
            await test_fn(config)
            passed.append(name)
        except AssertionError as e:
            print(f"\n[FAIL] {name} — Assertion: {e}")
            failed.append(name)
        except KeyboardInterrupt:
            # TC-4 is the only test that intentionally propagates this;
            # if it reaches here unexpectedly, treat as a failure.
            print(f"\n[FAIL] {name} — unexpected KeyboardInterrupt")
            failed.append(name)
        except Exception as e:
            print(f"\n[ERROR] {name} — {type(e).__name__}: {e}")
            failed.append(name)
            raise  # re-raise to show full traceback

    _print_section("Summary")
    for t in passed:
        print(f"  [PASS] {t}")
    for t in failed:
        print(f"  [FAIL] {t}")

    if not keep_workspace and not failed:
        _teardown()
        print("\nWorkspace cleaned up.")
    else:
        print(f"\nWorkspace preserved at: {WORKSPACE.resolve()}")
        print(f"Run `rm -rf {WORKSPACE}` to clean up.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
