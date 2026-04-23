# Feature Fix: CLI Backend Hardening

## Problem Statement

Four issues with the current CLI backend implementation:

1. **No multi-turn conversation for receptionist (Claude CLI):** The `claude -p` flag is single-turn. The current receptionist in CLI mode flattens history into a single prompt string, but each call is a fresh subprocess — the model has no persistent conversation state. Follow-up questions don't work naturally.

2. **Non-JSON CLI output:** Both Claude and Gemini CLIs can output markdown, preamble, or conversational text around JSON. `extract_json()` exists in `utils.py` but is only used in `lead.py`. The receptionist and any future JSON-expecting code paths need consistent parsing.

3. **Subagents run with too many permissions:** Gemini CLI runs with `--approval-mode auto_edit` (allows file writes + search, blocks shell). Claude CLI runs with `--dangerously-skip-permissions`. Subagents should only get the permissions their `tool_profile` requires.

4. **No custom tool scripts for subagents:** CLI subagents rely on the CLI's built-in tools. There's no way to provide sandboxed `read_only`, `write_only`, or `full` filesystem tools as standalone scripts that map to tool profiles.

---

## Subtask Breakdown

### F1 — Multi-turn Receptionist in CLI Mode

**Files:** `providers/claude_cli.py`, `providers/__init__.py`, `agents/receptionist.py`

**Current state:** Each CLI call is a separate subprocess. Conversation history is serialized into the prompt as `Human: ... Assistant: ...` text. This is lossy — the model doesn't see its own tool calls, and the prompt grows linearly.

**Approach:** Use Claude CLI's `--resume` / `--continue` flag (if available) or session persistence to maintain a real conversation across turns. Alternatively, use Claude CLI's `--conversation` mode via a named session.

**Subtasks:**

- [ ] **F1.1** — Investigate Claude CLI flags for session persistence. Run `claude --help` and check for `--resume`, `--continue`, `--session-id`, or similar. Document findings.
- [ ] **F1.2** — If session persistence exists: refactor `claude_cli.py` to support a `session_id` parameter. Each subprocess invocation reuses the session.
- [ ] **F1.3** — If no session persistence: improve the prompt-flattening approach in `wrapped_claude_run` (providers/__init__.py:133-178). Serialize messages in a structured format (XML tags or JSON) rather than loose `Human:/Assistant:` text. Include tool call/result history.
- [ ] **F1.4** — Update `agents/receptionist.py` to pass session context through when `backend == CLI`. Ensure the model sees its own prior output and can ask meaningful follow-ups.
- [ ] **F1.5** — Test: run receptionist in CLI mode with a vague initial query. Verify it asks a follow-up question and the second turn is contextually aware.

---

### F2 — Robust JSON Extraction Across All Agents

**Files:** `utils.py`, `agents/receptionist.py`, `agents/lead.py`, `agents/subagent.py`

**Current state:** `extract_json()` exists and is used in `lead.py`. The receptionist has inline JSON extraction (lines 91-94). Subagent doesn't extract JSON (it writes files directly, so this may be fine).

**Approach:** Audit every code path that expects structured output from a CLI call. Ensure all use `extract_json()` consistently. Harden `extract_json()` if edge cases are found.

**Subtasks:**

- [ ] **F2.1** — Audit: grep for `json.loads` across the codebase. Identify any direct `json.loads()` calls on CLI output that should use `extract_json()` instead.
- [ ] **F2.2** — Refactor `receptionist.py` lines 91-94 to use `extract_json()` more robustly (it already does, but verify edge cases: what if the model outputs explanation text + JSON brief?).
- [ ] **F2.3** — Add a `extract_json_or_raise()` variant that raises a clear error instead of returning `None`, for code paths where JSON is mandatory (e.g., `lead.plan()` parsing).
- [ ] **F2.4** — Add test cases for `extract_json()` with real-world CLI output patterns: thinking tags, markdown headers before JSON, trailing commentary after JSON.
- [ ] **F2.5** — Document in `utils.py` docstring: when to use `extract_json()` vs `extract_json_or_raise()`.

---

### F3 — Permission-Scoped CLI Subagents

**Files:** `providers/claude_cli.py`, `providers/gemini_cli.py`, `providers/__init__.py`

**Current state:**
- `claude_cli.py` uses `--dangerously-skip-permissions` globally — every Claude CLI subagent can do anything.
- `gemini_cli.py` uses `--approval-mode auto_edit` — allows file edits but no shell. Not scoped to tool profile.
- The `tool_profile` → allowed tools mapping exists in `providers/__init__.py` (lines 153-165) for Claude but only maps to built-in tool names. No enforcement for Gemini.

**Approach:** Replace `--dangerously-skip-permissions` with scoped `--allowedTools` based on the `tool_profile`. For Gemini, map profiles to appropriate `--approval-mode` or sandbox flags.

**Subtasks:**

- [ ] **F3.1** — Remove `--dangerously-skip-permissions` from `claude_cli.py`. Replace with `--allowedTools` that is always populated from the resolved tool profile.
- [ ] **F3.2** — Define a mapping from `tool_profile` → Claude CLI `--allowedTools` list:
  - `full` → `Read,Write,Edit,Glob,Grep`
  - `read_only` → `Read,Glob,Grep`
  - `write_only` → `Write`
  - `search_only` → (no `--allowedTools`, or empty)
- [ ] **F3.3** — For Gemini CLI: investigate `--approval-mode` options (`auto_edit`, `read_only`, etc.) and map tool profiles accordingly:
  - `full` → `auto_edit`
  - `read_only` → appropriate read-only mode (investigate available flags)
  - `search_only` → disable file tools entirely if possible
- [ ] **F3.4** — Update `wrapped_claude_run` in `providers/__init__.py` to always pass the profile-derived `allowed_tools` (currently it maps individual tools, should use the profile directly).
- [ ] **F3.5** — Update `wrapped_gemini_run_cli` in `providers/__init__.py` to pass approval-mode based on tool profile.
- [ ] **F3.6** — Test: run a subagent with `read_only` profile via Claude CLI. Verify it cannot write files. Run with `search_only` and verify no filesystem access.

---

### F4 — Custom Tool Scripts for CLI Subagents

**Files:** `scripts/` (new), `providers/claude_cli.py`, `providers/gemini_cli.py`, `providers/__init__.py`, `tools.py`

**Current state:** CLI subagents use the CLI's built-in tools (Read/Write/Glob for Claude, native file access for Gemini). There's no way to provide custom sandboxed tools that enforce workspace boundaries — the CLI tools can access any file the process can see.

**Approach:** Write small shell/Python scripts that act as sandboxed filesystem tools. These scripts:
- Accept a workspace root as an argument
- Validate that all paths stay within the workspace
- Provide `read_file.py`, `write_file.py`, and `list_files.py` equivalents
- Can be registered as MCP tools or passed via `--tool-command` (if supported by the CLI)

**Subtasks:**

- [ ] **F4.1** — Investigate Claude CLI's custom tool support. Check for `--mcp-config`, `--tool-command`, or similar flags that allow registering external tool scripts.
- [ ] **F4.2** — Investigate Gemini CLI's custom tool/extension support.
- [ ] **F4.3** — Write `scripts/workspace_read.py`: accepts `--workspace DIR --path REL_PATH`, validates path stays within workspace, prints file content to stdout. Exits non-zero on violation.
- [ ] **F4.4** — Write `scripts/workspace_write.py`: accepts `--workspace DIR --path REL_PATH --content CONTENT` (or reads content from stdin), validates path, writes file. Exits non-zero on violation.
- [ ] **F4.5** — Write `scripts/workspace_list.py`: accepts `--workspace DIR --path REL_PATH`, validates path, lists directory contents.
- [ ] **F4.6** — Create tool profile → script mapping:
  - `full` → all three scripts
  - `read_only` → only `workspace_read.py` + `workspace_list.py`
  - `write_only` → only `workspace_write.py`
  - `search_only` → no scripts
- [ ] **F4.7** — Wire the scripts into the CLI provider layer. For Claude: use MCP config or `--tool-command`. For Gemini: use extensions or `--tool` flag (based on F4.2 findings).
- [ ] **F4.8** — Test: run a subagent with custom tool scripts. Verify workspace sandboxing — attempt path traversal and confirm it's blocked.

---

## Implementation Order

```
F1 (multi-turn)     — independent, can start immediately
F2 (JSON parsing)   — independent, can start immediately
F3 (permissions)    — independent, can start immediately
F4 (tool scripts)   — depends on F3 findings (what CLI flags exist)

Recommended parallel tracks:
  Track A: F1 → F1.5 (test)
  Track B: F2 → F2.4 (test)
  Track C: F3 + F4 (sequential — F3 informs F4 design)
```

## Key Design Decisions

### Why not just use API mode for the receptionist?
The user wants a uniform CLI backend. Falling back to API for one agent defeats the purpose of CLI mode. However, if CLI multi-turn proves too brittle, this is a valid escape hatch — document it as a known limitation.

### Why custom scripts instead of relying on CLI built-in tools?
CLI built-in tools (Read/Write) have no workspace sandboxing — they can access any file. Custom scripts enforce the same path validation that `tools.py:execute()` does for API mode, maintaining security parity between backends.

### Why map profiles to `--allowedTools` rather than per-tool?
The profile is the source of truth for what a subagent can do. Mapping at the profile level (not per-tool) keeps the logic in one place and ensures new tools added to a profile automatically propagate to CLI permissions.
