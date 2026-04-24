# Completed Tasks

## Phase 1: API Backend

### [x] Task 1.1: Validate and fix Gemini API integration
- **Completed:** 2026-04-21
- **Details:** Verified `google-genai` SDK v1.73.1. Implemented manual tool-use loop with `include_server_side_tool_invocations=True` in `ToolConfig` to support combined Google Search and custom functions. Verified model IDs.

### [x] Task 1.2: Validate and fix Anthropic API integration
- **Completed:** 2026-04-21
- **Details:** Verified `AsyncAnthropic` tool-use loop. Successfully ran lead and receptionist agents using Claude Sonnet.

### [x] Task 1.3: End-to-end receptionist test
- **Completed:** 2026-04-21
- **Details:** Ran full interactive intake for "stock market in 2026" research. Model successfully called `submit_brief` with a structured research brief.

### [x] Task 1.4: End-to-end lead agent test
- **Completed:** 2026-04-21
- **Details:** Verified lead's `plan()` and `synthesize()` functions. Added JSON fallback parsing for tool calls. Successfully decomposed brief into 3 subtasks and synthesized final report.

### [x] Task 1.5: End-to-end subagent test
- **Completed:** 2026-04-21
- **Details:** Verified parallel subagent execution using `asyncio.gather`. Subagents correctly used Google Search and wrote findings to the workspace. Added resilience to schema variations (id/name, title/name).

### [x] Task 1.6: Full pipeline integration test
- **Completed:** 2026-04-21
- **Details:** Ran `main.py` end-to-end. Flow: User Intake → Plan → 3x Parallel Subagents → Synthesis → 24KB `report.md`.

## Phase 2: CLI Backend

### [x] Task 2.1: Wire backend routing into agents
- **Completed:** 2026-04-21
- **Details:** Implemented a provider factory in `providers/__init__.py`. Updated `receptionist.py`, `lead.py`, and `subagent.py` to use `get_provider()`. This enables switching between API and CLI backends via `config.backend`.

### [x] Task 2.2: Verify and fix Claude CLI integration
- **Completed:** 2026-04-21
- **Details:** Verified `claude` CLI flags (`-p`, `--model`, `--system-prompt`, `--allowedTools`). Tested basic invocation.

### [x] Task 2.3: Verify and fix Gemini CLI integration
- **Completed:** 2026-04-21
- **Details:** Verified `gemini` CLI flags (`-p`, `-m`). Implemented system prompt support via `GEMINI_SYSTEM_MD` environment variable and temporary files. Added `--yolo` flag for automated tool approval.

### [x] Task 2.6: CLI-mode integration test
- **Completed:** 2026-04-21
- **Details:** Ran `main.py --backend cli` end-to-end. Optimized Lead agent to use Gemini in CLI mode for stability with large prompts. Fixed Claude CLI hangs by switching synthesis to read-then-output text instead of subprocess tool calls. Verified full pipeline: Intake (API) -> Plan (CLI/Gemini) -> 3x Parallel Subagents (CLI/Gemini) -> Synthesis (CLI/Gemini) -> `report.md`.

## Phase 3: Iterative Deepening & Dynamic Tool Assignment

### [x] Task 3.1: Tool Registry
- **Completed:** 2026-04-21
- **Details:** Refactored `FILE_TOOLS` into individual constants in `tools.py`. Defined `TOOL_PROFILES` (`full`, `read_only`, `search_only`, `write_only`). Added `get_tools_for_profile()` and `list_tool_profiles()` for dynamic tool assignment. Verified with unit tests.

### [x] Task 3.2: Inject Tool Profile Info into Lead's Planning Prompt
- **Completed:** 2026-04-21
- **Details:** Added `{tool_profiles}` placeholder to `prompts/lead_planning.md`. Updated `agents/lead.py` to inject profile data at runtime. Updated `CREATE_PLAN_TOOL` schema and added validation to default missing profiles to "full".

### [x] Task 3.3: Subagent Respects Tool Profile
- **Completed:** 2026-04-21
- **Details:** Updated `agents/subagent.py` to resolve `tool_profile` from the task dictionary and fetch the corresponding tools from the registry. This ensures subagents only have access to the permissions designated by the Lead.

### [x] Task 3.4: `dispatch_subagents` Tool for the Lead
- **Completed:** 2026-04-21
- **Details:** Implemented a new `dispatch_subagents` tool that allows the Lead agent to spawn additional research rounds during synthesis. The tool executes subagents in parallel and returns their consolidated findings to the Lead.

### [x] Task 3.5: Update Synthesis Prompt for Iterative Awareness
- **Completed:** 2026-04-21
- **Details:** Updated `prompts/lead_synthesis.md` to document the iterative remediation process and tool usage. Refactored `agents/lead.py` to properly inject the remediation budget (current round vs. max rounds) into the system prompt.

### [x] Task 3.6: Simplify `main.py` Orchestration
- **Completed:** 2026-04-21
- **Details:** Updated `main.py` to reflect that the Lead agent now handles iterative remediation internally. Simplified the orchestration flow and added console logging for remediation rounds.

### [x] Task 3.7: Config Updates
- **Completed:** 2026-04-21
- **Details:** Added `max_remediation_rounds` to `Config` (default 2) and exposed it via the `--max-remediation-rounds` CLI argument in `main.py`.

### [x] Task 3.8.1-3.8.4: Unit Testing for Tool Profiles and Lead/Subagent
- **Completed:** 2026-04-23
- **Details:** Verified `get_tools_for_profile()` and `list_tool_profiles()`. Confirmed `lead.plan()` defaults to "full" and `subagent.run()` respects assigned tool profiles.

### [x] Task 3.9: Robust JSON parsing for CLI backend
- **Completed:** 2026-04-23
- **Details:** Created `utils.py` with `extract_json()` and `extract_json_or_raise()` to robustly extract JSON from freeform LLM text. Handles markdown code blocks, conversational filler, and embedded objects/arrays. Integrated into Lead planning and synthesis phases.

### [x] Task 3.10: Multi-turn conversation support for CLI backend
- **Completed:** 2026-04-23
- **Details:** Added `session_id` support to Claude and Gemini CLI runners. Fixed conversation history flattening to ensure correct multi-turn behavior. Implemented CLI-specific synthesis loop in Lead agent to handle iterative tool calls without repeated process overhead.

### [x] Task 3.11: Tighten CLI security by restricting subagent tool permissions
- **Completed:** 2026-04-23
- **Details:** Mapped `tool_profile` to CLI-specific profiles. Gemini CLI now uses `--approval-mode` for tool execution. Restricted subagent tool sets based on Lead's assignment, even in CLI mode.

### [x] Task 3.12: Move CLI backend to Gemini
- **Completed:** 2026-04-23
- **Details:** Switched Receptionist and Lead agents to use Gemini in CLI mode by default for better stability and lower latency compared to Claude CLI. Implemented system prompt support for Gemini CLI via `GEMINI_SYSTEM_MD` and temporary files.

### [x] Task 3.13: Implement custom tool scripts for CLI subagents (F4 Hardening)
- **Completed:** 2026-04-23
- **Details:** Implemented sandboxed file tools (`read_file.py`, `write_file.py`, `list_files.py`) with `Path.cwd().resolve()` workspace boundary enforcement. Built a JSON-RPC/MCP server (`server.py`) exposing these as `sandboxed_read_file`, `sandboxed_write_file`, `sandboxed_list_files`. Created Gemini CLI extension at `.gemini/extensions/sandboxed-tools/` using `excludeTools` to disable core file-system tools. Extension globally linked via `gemini extensions link`. Fixed `write_file.py` to read content from stdin (instead of argv) to handle multiline/special-char content. Verified: tools discoverable, write/read functional, path traversal escape blocked.

### [x] Task 3.8.5: Verify remediation loop (CLI mode)
- **Completed:** 2026-04-23
- **Details:** Identified and fixed a bug in the Lead agent's synthesis loop for CLI mode where conversation history was causing context pollution and Human-Human message sequences. Refactored the loop to use a stateless, single-message approach with full consolidated findings in each turn. Verified with a simplified remediation test. Note: Complex prompts may still trigger 'AbortError' in Gemini CLI due to internal loop recovery mechanisms.
