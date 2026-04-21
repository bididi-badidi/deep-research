# Phase 1 — API Backend

**Status:** Scaffolded, needs testing and hardening

---

## Task 1.1: Validate and fix Gemini API integration

**File:** `providers/gemini_api.py`

- [ ] 1.1.1 — Verify `google-genai` SDK installation and import paths
- [ ] 1.1.2 — Test `GoogleSearch` grounding in isolation
- [ ] 1.1.3 — Test custom `FunctionDeclaration` + `GoogleSearch` coexistence
- [ ] 1.1.4 — Test the function-call loop (tool call → FunctionResponse → continue)
- [ ] 1.1.5 — Verify correct model ID string for Gemini 3 Flash

## Task 1.2: Validate and fix Anthropic API integration

**File:** `providers/anthropic_api.py`

- [ ] 1.2.1 — Run a basic tool-use round trip
- [ ] 1.2.2 — Test edge case: text + tool_use in same response
- [ ] 1.2.3 — Verify model IDs (`claude-sonnet-4-20250514`, `claude-opus-4-20250514`)

## Task 1.3: End-to-end receptionist test

**File:** `agents/receptionist.py`

- [ ] 1.3.1 — Run receptionist in isolation, verify greeting → follow-ups → `submit_brief`
- [ ] 1.3.2 — Test fast-path (detailed input → immediate `submit_brief`)
- [ ] 1.3.3 — Test `quit`/`exit`/`q` raises `KeyboardInterrupt` cleanly
- [ ] 1.3.4 — Verify returned brief has all required keys

## Task 1.4: End-to-end lead agent test

**File:** `agents/lead.py`

- [ ] 1.4.1 — Test `plan()` with sample brief, verify task dicts and `plan.json`
- [ ] 1.4.2 — Test `synthesize()` with dummy findings, verify `report.md`
- [ ] 1.4.3 — Add JSON error handling in `create_plan` handler

## Task 1.5: End-to-end subagent test

**File:** `agents/subagent.py`

- [ ] 1.5.1 — Test single subagent with a sample task dict
- [ ] 1.5.2 — Test parallel execution (3 subagents via `asyncio.gather`)
- [ ] 1.5.3 — Test error resilience (`return_exceptions=True`)

## Task 1.6: Full pipeline integration test

**Files:** `main.py`, all agents, all providers

- [ ] 1.6.1 — Run `python main.py` end-to-end with real research query
- [ ] 1.6.2 — Measure token usage and latency per stage
- [ ] 1.6.3 — Verify workspace output structure
