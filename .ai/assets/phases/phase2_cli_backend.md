# Phase 2 — CLI Backend

**Status:** Stub implementations exist, routing not wired

---

## Task 2.1: Wire backend routing into agents

**Files:** `main.py`, `agents/*.py`, `config.py`

- [ ] 2.1.1 — Create provider factory in `providers/__init__.py`
- [ ] 2.1.2 — Update receptionist for CLI mode (multi-turn strategy)
- [ ] 2.1.3 — Update lead agent to use provider factory
- [ ] 2.1.4 — Update subagent to use provider factory

## Task 2.2: Verify and fix Claude CLI integration

**File:** `providers/claude_cli.py`

- [ ] 2.2.1 — Document available `claude` CLI flags
- [ ] 2.2.2 — Test basic invocation via stdin/stdout
- [ ] 2.2.3 — Test `--system-prompt` (inline string vs file)
- [ ] 2.2.4 — Test `--allowedTools` for file access
- [ ] 2.2.5 — Handle long system prompts (temp file fallback)

## Task 2.3: Verify and fix Gemini CLI integration

**File:** `providers/gemini_cli.py`

- [ ] 2.3.1 — Document available `gemini` CLI flags
- [ ] 2.3.2 — Test basic invocation via stdin/stdout
- [ ] 2.3.3 — Test Google Search grounding in CLI mode
- [ ] 2.3.4 — Test file access in CLI mode
- [ ] 2.3.5 — Update `gemini_cli.py` with corrected flags

## Task 2.4: CLI-mode integration test

**Files:** All

- [ ] 2.4.1 — Run `python main.py --backend cli` end-to-end
- [ ] 2.4.2 — Compare output quality between API and CLI backends
- [ ] 2.4.3 — Measure latency differences between backends
