# Deep Research — System Architecture & Project Plan

## Overview

A multi-agent research system inspired by [Anthropic's multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). Three agent roles collaborate to turn a vague research request into a comprehensive, sourced report.

**Two delivery phases:**

| Phase                 | Backend | How agents call models                                          |
| --------------------- | ------- | --------------------------------------------------------------- |
| **Phase 1** (current) | API     | `anthropic` and `google-genai` Python SDKs                      |
| **Phase 2**           | CLI     | `claude` and `gemini` CLIs via `asyncio.create_subprocess_exec` |

---

## System Architecture

### Agent Pipeline

```
User
 │
 ▼
┌─────────────────────────────────┐
│  Receptionist  (Claude Sonnet)  │  Interactive intake conversation
│  agents/receptionist.py         │  Outputs: research brief (dict)
└────────────┬────────────────────┘
             │ brief
             ▼
┌─────────────────────────────────┐
│  Research Lead  (Claude Opus)   │  Phase A: decompose brief → task list
│  agents/lead.py                 │  Phase B: synthesize findings → report
└────────────┬────────────────────┘
             │ tasks[]
             ▼
┌─────────────────────────────────┐
│  Subagents  (Gemini 3 Flash)   │  Run in parallel via asyncio.gather
│  agents/subagent.py             │  Google Search grounding + file tools
│  × 2-5 concurrent instances     │  Each writes workspace/findings/{id}.md
└─────────────────────────────────┘
             │
             ▼
       workspace/report.md
```

### File Structure

```
deep-research/
├── main.py                        # Entry point, CLI args, orchestration flow
├── config.py                      # Config dataclass (models, backend, limits)
├── tools.py                       # Sandboxed filesystem tools + executor
├── pyproject.toml                 # Dependencies: anthropic, google-genai
│
├── agents/
│   ├── __init__.py
│   ├── receptionist.py            # Sonnet — multi-turn user intake
│   ├── lead.py                    # Opus — plan() + synthesize()
│   └── subagent.py                # Gemini — web search + write findings
│
├── providers/
│   ├── __init__.py
│   ├── anthropic_api.py           # Anthropic tool-use loop
│   ├── gemini_api.py              # Gemini tool-use loop + Google Search
│   ├── claude_cli.py              # Phase 2 stub — Claude CLI subprocess
│   └── gemini_cli.py              # Phase 2 stub — Gemini CLI subprocess
│
└── workspace/                     # Runtime output (gitignored)
    └── <research_id>/             # One folder per research session
        ├── findings/              # One .md per subagent task
        ├── plan.json              # Lead's task decomposition
        └── report.md              # Final synthesized report
```

### Data Flow

1. **Receptionist** converses with user, calls `submit_brief` tool → `dict` with keys: `topic`, `scope`, `questions`, `depth`, `output_preferences`
2. **Lead (plan)** receives brief, calls `create_plan` tool → `list[dict]` with each task having: `id`, `title`, `objective`, `search_hints`
3. **Subagents** receive one task each, use Google Search + `write_file` → `workspace/findings/{task_id}.md`
4. **Lead (synthesize)** uses `list_files` + `read_file` on findings dir, then `write_file` → `workspace/report.md`

### Tool Definitions

All agents share a common tool format (converted per-provider):

| Tool           | Parameters                                                   | Used By           |
| -------------- | ------------------------------------------------------------ | ----------------- |
| `read_file`    | `path` (relative to workspace)                               | Lead, Subagents   |
| `write_file`   | `path`, `content`                                            | Lead, Subagents   |
| `list_files`   | `path`                                                       | Lead              |
| `submit_brief` | `topic`, `scope`, `questions`, `depth`, `output_preferences` | Receptionist only |
| `create_plan`  | `tasks` (JSON string)                                        | Lead only         |
| Google Search  | (native Gemini grounding)                                    | Subagents only    |

### Provider Abstraction

Each provider module exposes an `async def run(...)` function with a tool-use loop:

- **anthropic_api**: takes `messages` list (mutated in place), converts tools via `to_anthropic_tools()`, loops until `stop_reason != tool_use`
- **gemini_api**: takes a `prompt` string, converts tools via `to_gemini_tools()`, attaches `GoogleSearch()` grounding, loops until no `function_call` parts
- **claude_cli / gemini_cli**: Phase 2 — `asyncio.create_subprocess_exec` with prompt via stdin, result via stdout

### Configuration

`config.py` — `Config` dataclass:

| Field                | Default             | Purpose                                 |
| -------------------- | ------------------- | --------------------------------------- |
| `backend`            | `Backend.API`       | `api` or `cli`                          |
| `workspace`          | `./workspace`       | Runtime output directory                |
| `receptionist_model` | `claude-sonnet-4-6` | Model for intake                        |
| `lead_model`         | `claude-opus-4-6`   | Model for planning + synthesis          |
| `subagent_model`     | `gemini-3-flash`    | Model for web research                  |
| `max_subagents`      | `15`                | Upper limit on parallel subagents       |
| `timeout_seconds`    | `900`               | Timeout for each subagent research task |
| `max_tokens`         | `16384`             | Max output tokens per API call          |

---

## Phase 1 — API Backend

### Status: Scaffolded, needs testing and hardening

### Task 1.1: Validate and fix Gemini API integration

**File:** `providers/gemini_api.py`

**Context:** The Gemini provider uses the `google-genai` SDK. The tool-use loop and `GoogleSearch` grounding integration are written but untested. The SDK API surface may differ from what's implemented.

**Subtasks:**

- [x] **1.1.1** — Verify `google-genai` SDK installation and import paths. Run `from google import genai; from google.genai import types` in a Python shell. Fix any import errors.
- [x] **1.1.2** — Test `GoogleSearch` grounding in isolation. Send a simple query with `types.Tool(google_search=types.GoogleSearch())` and confirm grounded results come back. Document the required env var (`GOOGLE_API_KEY` or `GEMINI_API_KEY`).
- [x] **1.1.3** — Test custom `FunctionDeclaration` tools alongside `GoogleSearch` in the same request. Confirm both tool types can coexist in the `tools` list. If not, restructure `to_gemini_tools()` to separate them.
- [x] **1.1.4** — Test the function-call loop: send a prompt that triggers a custom tool call, return a `FunctionResponse`, confirm the model continues. Verify the `function_call` attribute access pattern (`part.function_call`, `fc.name`, `fc.args`).
- [x] **1.1.5** — Verify the correct model ID string for Gemini 3 Flash. Update `config.py` if the actual ID differs from `"gemini-3-flash"`.

---

### Task 1.2: Validate and fix Anthropic API integration

**File:** `providers/anthropic_api.py`

**Context:** The Anthropic provider uses `AsyncAnthropic`. The tool-use loop is standard but untested end-to-end.

**Subtasks:**

- [ ] **1.2.1** — Run a basic tool-use round trip: send a message that triggers a tool call, return a `tool_result`, confirm the model continues. Verify `block.type == "tool_use"`, `block.id`, `block.name`, `block.input` all work as expected.
- [ ] **1.2.2** — Test edge case: model returns text + tool_use in the same response. Confirm the loop processes tool calls and continues (doesn't return early on the text).
- [x] **1.2.3** — Verify model IDs `claude-sonnet-4-20250514` and `claude-opus-4-20250514` are valid. Update `config.py` if needed.

---

### Task 1.3: End-to-end receptionist test

**File:** `agents/receptionist.py`

**Context:** The receptionist runs an interactive multi-turn loop. It uses `asyncio.to_thread(input, ...)` for non-blocking user input. It detects completion when the model calls the `submit_brief` tool.

**Subtasks:**

- **1.3.1** — Run the receptionist in isolation: `python -c "import asyncio; from config import Config; from agents.receptionist import run; asyncio.run(run(Config()))"`. Verify: (a) it prints a greeting/question, (b) accepts typed input, (c) asks follow-ups, (d) eventually calls `submit_brief`.
- **1.3.2** — Test the fast-path: provide a very detailed initial description. Confirm the model calls `submit_brief` without unnecessary follow-up questions.
- **1.3.3** — Test `quit`/`exit`/`q` input raises `KeyboardInterrupt` cleanly.
- **1.3.4** — Verify the returned brief dict has all required keys: `topic`, `scope`, `questions`, `depth`. `output_preferences` is optional.

---

### Task 1.4: End-to-end lead agent test

**File:** `agents/lead.py`

**Context:** The lead has two phases. `plan()` receives a brief dict and must call the `create_plan` tool with a valid JSON array. `synthesize()` reads findings files and writes `report.md`.

**Subtasks:**

- **1.4.1** — Test `plan()` with a sample brief dict. Confirm it returns a list of task dicts with keys `id`, `title`, `objective`, `search_hints`. Confirm `workspace/plan.json` is written.
- **1.4.2** — Create 2-3 dummy `workspace/findings/*.md` files, then test `synthesize()`. Confirm it reads all files and writes `workspace/report.md`.
- **1.4.3** — Validate JSON parsing in `create_plan` handler: if the model outputs malformed JSON in the `tasks` field, the current code will crash with `json.JSONDecodeError`. Add a try/except that returns an error message to the model so it can retry.

---

### Task 1.5: End-to-end subagent test

**File:** `agents/subagent.py`

**Context:** Each subagent receives a task dict and uses Gemini with Google Search grounding + filesystem tools to research and write findings.

**Subtasks:**

- **1.5.1** — Test with a single task dict: `{"id": "test-task", "title": "Test", "objective": "Find the population of Tokyo", "search_hints": ["Tokyo population 2025"]}`. Confirm `workspace/findings/test-task.md` is created with sourced content.
- **1.5.2** — Test parallel execution: run 3 subagents via `asyncio.gather`. Confirm all 3 findings files are written without race conditions on the filesystem.
- **1.5.3** — Test error resilience: if a subagent fails (API error, rate limit), confirm `asyncio.gather(..., return_exceptions=True)` in `main.py` captures it and the other subagents still complete.

---

### Task 1.6: Full pipeline integration test

**Files:** `main.py`, all agents, all providers

**Subtasks:**

- **1.6.1** — Run `python main.py` end-to-end with a real research query. Document the full flow: intake → planning → subagent execution → synthesis → report.
- **1.6.2** — Measure token usage and latency at each stage. Record baseline numbers for a typical 3-subagent research run.
- **1.6.3** — Verify workspace output structure: `plan.json`, `findings/*.md` (one per task), `report.md`.

---

## Phase 2 — CLI Backend

### Status: Stub implementations exist, routing not wired

### Task 2.1: Wire backend routing into agents

**Files:** `main.py`, `agents/receptionist.py`, `agents/lead.py`, `agents/subagent.py`, `config.py`

**Context:** Currently all agents hardcode their provider (anthropic_api or gemini_api). When `config.backend == Backend.CLI`, agents should use `claude_cli` and `gemini_cli` instead.

**Subtasks:**

- [x] **2.1.1** — Add a provider selection layer. Options: (a) each agent checks `config.backend` and imports the right provider, or (b) create a factory function in `providers/__init__.py` that returns the right `run()` callable based on backend + provider name. Approach (b) is cleaner. Implement it.
- [x] **2.1.2** — Update `agents/receptionist.py` to support CLI mode. In CLI mode, the receptionist cannot do multi-turn conversation through the CLI (claude CLI's `-p` flag is single-turn). Options: (a) keep receptionist always on API, (b) implement a multi-prompt loop where each turn is a separate CLI invocation with conversation history serialized into the prompt. Decide and implement.
- [x] **2.1.3** — Update `agents/lead.py` to use the provider factory for both `plan()` and `synthesize()`. In CLI mode, the lead runs as a single prompt with tools handled by the CLI's built-in file access. The lead's prompt must instruct the CLI to write `plan.json` and `report.md` directly. Adjust prompts and parsing accordingly.
- [x] **2.1.4** — Update `agents/subagent.py` to use the provider factory. In CLI mode, the Gemini CLI handles search natively. The prompt must instruct it to write findings to the correct path. Adjust accordingly.

---

### Task 2.2: Verify and fix Claude CLI integration

**File:** `providers/claude_cli.py`

**Context:** The stub uses `claude -p --model MODEL --output-format text --system-prompt SYSTEM`. Prompt is piped via stdin. The exact CLI flags need verification against the current Claude CLI version.

**Subtasks:**

- [x] **2.2.1** — Run `claude --help` and document the available flags. Verify: `-p` (print mode), `--model`, `--system-prompt`, `--output-format`, `--allowedTools`. Update the stub if flags differ.
- [x] **2.2.2** — Test a basic invocation: `echo "What is 2+2?" | claude -p --output-format text`. Confirm stdout contains the response.
- [x] **2.2.3** — Test with `--system-prompt`: verify it accepts an inline string. If it requires a file, adjust the implementation to write a temp file.
- [x] **2.2.4** — Test with `--allowedTools Read,Write,Edit,Glob,Grep`: confirm the CLI enables those tools and the model can use them to read/write files in the cwd.
- [x] **2.2.5** — Handle long system prompts: if the system prompt exceeds shell argument limits, switch to passing it via a temp file or environment variable.

---

### Task 2.3: Verify and fix Gemini CLI integration

**File:** `providers/gemini_cli.py`

**Context:** The stub assumes `gemini -model MODEL` with prompt via stdin. The Gemini CLI's actual interface needs verification.

**Subtasks:**

- [x] **2.3.1** — Run `gemini --help` and document the available flags. Verify: model selection flag, stdin prompt support, non-interactive mode, search/tool flags.
- [x] **2.3.2** — Test a basic invocation: `echo "What is 2+2?" | gemini ...`. Confirm stdout output.
- [x] **2.3.3** — Test Google Search grounding in CLI mode: verify the CLI can perform web searches. Document the flag or configuration needed.
- [x] **2.3.4** — Test file access in CLI mode: verify the CLI can read/write files in its working directory. Document how this is enabled.
- [x] **2.3.5** — Update `gemini_cli.py` with corrected flags and patterns based on findings.

---

### Task 2.4: CLI-mode integration test

**Files:** All

**Subtasks:**

- **2.4.1** — Run `python main.py --backend cli` end-to-end. Document any failures and fix.
- **2.4.2** — Compare output quality (report.md) between API and CLI backends for the same research query.
- **2.4.3** — Measure latency differences between API and CLI backends. CLI may be slower due to subprocess overhead and lack of streaming.

---

## Future Enhancements (not yet planned)

These are ideas noted for potential later work. No tasks are defined.

- **Citation agent** — Post-processing agent that verifies source URLs and adds proper citations (matches Anthropic's architecture).
- **Iterative deepening** — Lead agent spawns a second round of subagents to fill gaps identified during synthesis.
- **Streaming output** — Stream subagent progress to the terminal as it happens.
- **Token budget tracking** — Monitor and cap token usage across all agents.
- **Workspace persistence** — Resume interrupted research from checkpoint state.
- **Web UI** — Browser-based interface instead of CLI.
