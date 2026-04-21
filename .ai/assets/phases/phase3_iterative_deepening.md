# Phase 3 — Iterative Deepening & Dynamic Tool Assignment

## Problem Statement

Two capabilities are missing from the current pipeline:

1. **The Lead agent cannot spawn more subagents.** After `synthesize()` runs, the pipeline terminates — even if the synthesis prompt (`lead_synthesis.md`) explicitly describes a "Remediation Request" path where the Lead should commission additional research. Today, `main.py` hardcodes a linear flow: `plan → subagents → synthesize → done`. The Lead has no tool to say "I need more research on X" and actually trigger new subagent runs.

2. **The Lead cannot control what tools subagents receive.** Every subagent gets the same `FILE_TOOLS` list plus Google Search grounding. But some tasks may need tighter sandboxing (read-only, no file writes) or broader capabilities (e.g., a future code-execution tool). The Lead should be able to declare per-task tool sets when writing Task Cards.

---

## Architecture Changes

### Current Flow (linear, single-pass)

```
main.py:
  receptionist.run()     → brief
  lead.plan()            → tasks[]
  subagent.run(task) × N → findings/
  lead.synthesize()      → report.md
```

### Target Flow (iterative, lead-controlled)

```
main.py:
  receptionist.run()             → brief
  lead.plan()                    → tasks[] (each task includes tool_profile)
  loop:
    subagent.run(task) × N       → findings/
    lead.evaluate_and_synthesize() → report.md OR remediation_tasks[]
    if report.md → break
    else → append remediation_tasks to task queue, continue loop
  done
```

---

## Implementation Plan

### Task 3.1 — Tool Registry

**Files:** `tools.py`

Create a registry of available tool profiles that the Lead can reference by name when assigning tools to subagents.

**Design:**

```python
# tools.py additions

TOOL_PROFILES: dict[str, list[dict]] = {
    "full": FILE_TOOLS,                          # read + write + list + refs
    "read_only": [READ_FILE, LIST_FILES, LIST_REFERENCES, READ_REFERENCE],
    "write_only": [WRITE_FILE],
    "search_only": [],                            # Google Search grounding only, no FS tools
}

def get_tools_for_profile(profile: str) -> list[dict]:
    """Return the tool list for a named profile. Defaults to 'full'."""
    return TOOL_PROFILES.get(profile, TOOL_PROFILES["full"])

def list_tool_profiles() -> dict[str, list[str]]:
    """Return a summary of profiles and their tool names (for prompt injection)."""
    return {name: [t["name"] for t in tools] for name, tools in TOOL_PROFILES.items()}
```

**Subtasks:**

- [x] **3.1.1** — Refactor `FILE_TOOLS` into individually named constants (`READ_FILE_TOOL`, `WRITE_FILE_TOOL`, etc.) so they can be composed into profiles.
- [x] **3.1.2** — Define `TOOL_PROFILES` dict with at least: `full`, `read_only`, `search_only`.
- [x] **3.1.3** — Add `get_tools_for_profile(name)` and `list_tool_profiles()` functions.
- [x] **3.1.4** — Unit test: verify each profile returns the expected tool names.

---

### Task 3.2 — Inject Tool Profile Info into Lead's Planning Prompt

**Files:** `agents/lead.py`, `prompts/lead_planning.md`

The Lead needs to *see* what tool profiles are available so it can assign one per task in the plan. We inject a summary into the planning prompt.

**Design:**

Update `lead_planning.md` to include a section like:

```markdown
## Available Tool Profiles for Subagents

When creating each task, you MUST include a `tool_profile` field. Available profiles:

{tool_profiles}

Choose the most restrictive profile that still allows the subagent to complete its task.
Default to "full" if unsure.
```

In `lead.py`, inject the actual profile data at runtime:

```python
from tools import list_tool_profiles
profiles_str = json.dumps(list_tool_profiles(), indent=2)
system_prompt = load_prompt("lead_planning").replace("{tool_profiles}", profiles_str)
```

Update `CREATE_PLAN_TOOL` schema to include `tool_profile` as an optional field per task.

**Subtasks:**

- [x] **3.2.1** — Add `{tool_profiles}` placeholder to `prompts/lead_planning.md` in a new "Available Tool Profiles" section.
- [x] **3.2.2** — In `lead.plan()`, inject `list_tool_profiles()` output into the prompt.
- [x] **3.2.3** — Update `CREATE_PLAN_TOOL` description to document the `tool_profile` field on each task object.
- [x] **3.2.4** — In `plan()`, validate parsed tasks: if `tool_profile` is missing, default to `"full"`.

---

### Task 3.3 — Subagent Respects Tool Profile

**Files:** `agents/subagent.py`

The subagent currently hardcodes `tools=FILE_TOOLS`. Change it to read `task["tool_profile"]` and resolve via the registry.

**Design:**

```python
from tools import get_tools_for_profile

async def run(config: Config, task: dict) -> str:
    profile = task.get("tool_profile", "full")
    tools = get_tools_for_profile(profile)
    # ... rest unchanged, but pass `tools` instead of `FILE_TOOLS`
```

**Subtasks:**

- [x] **3.3.1** — Update `subagent.run()` to resolve `tool_profile` from the task dict.
- [x] **3.3.2** — Pass resolved tools to the provider call instead of hardcoded `FILE_TOOLS`.
- [x] **3.3.3** — Test: a task with `"tool_profile": "read_only"` should not have `write_file` available.

---

### Task 3.4 — `dispatch_subagents` Tool for the Lead

**Files:** `agents/lead.py`, `tools.py`

Give the Lead agent a new tool it can call during synthesis to spawn additional subagent rounds. This is the core of iterative deepening.

**Design:**

The Lead's synthesis phase currently has no way to trigger new work. We add a `dispatch_subagents` tool that:

1. Accepts a list of remediation task dicts (same schema as `create_plan` output).
2. Runs them through `subagent.run()` in parallel (same as `main.py` does today).
3. Returns a summary of results (success/fail per task).

```python
# In lead.py — new tool definition

DISPATCH_SUBAGENTS_TOOL = {
    "name": "dispatch_subagents",
    "description": (
        "Dispatch additional research subagents to fill gaps in the current findings. "
        "Use this when the current evidence is insufficient to write an honest report. "
        "Each task follows the same schema as create_plan output. "
        "Returns a summary of which tasks succeeded or failed."
    ),
    "parameters": {
        "tasks": {
            "type": "string",
            "description": (
                "JSON array of task objects. Each object has: "
                '"id" (short slug, prefix with "R-" for remediation), '
                '"title", "objective", "search_hints", '
                '"tool_profile" (optional, defaults to "full").'
            ),
        },
        "reason": {
            "type": "string",
            "description": "Brief explanation of why additional research is needed.",
        },
    },
    "required": ["tasks", "reason"],
}
```

The tool executor in `synthesize()` handles this by actually running subagents:

```python
async def _exec_tool(name: str, args: dict) -> str:
    if name == "dispatch_subagents":
        remediation_tasks = json.loads(args["tasks"])
        reason = args["reason"]
        print(f"\n--- Lead requesting remediation: {reason} ---")

        from agents import subagent
        results = await asyncio.gather(
            *(subagent.run(config, task) for task in remediation_tasks),
            return_exceptions=True,
        )

        summary = []
        for task, result in zip(remediation_tasks, results):
            status = "FAIL" if isinstance(result, Exception) else "done"
            summary.append(f"[{status}] {task['id']}: {task['title']}")

        # After new findings are written, re-read findings directory
        # so the Lead can incorporate them
        return "Remediation complete.\n" + "\n".join(summary)

    return await tool_execute(name, args, workspace=config.workspace)
```

**Subtasks:**

- [x] **3.4.1** — Define `DISPATCH_SUBAGENTS_TOOL` constant in `lead.py`.
- [x] **3.4.2** — In `synthesize()`, add `DISPATCH_SUBAGENTS_TOOL` to the tools list passed to the provider.
- [x] **3.4.3** — Implement the `dispatch_subagents` handler inside `synthesize()`'s `_exec_tool`, including subagent execution and result summary.
- [x] **3.4.4** — Add a remediation loop cap (`max_remediation_rounds`, default 2) in `Config` to prevent infinite loops.
- [x] **3.4.5** — Track remediation round count and inject it into the tool result so the Lead knows how many rounds remain.

---

### Task 3.5 — Update Synthesis Prompt for Iterative Awareness

**Files:** `prompts/lead_synthesis.md`

The synthesis prompt already describes the Remediation Request concept but treats it as a document to write. Update it so the Lead knows it has a concrete `dispatch_subagents` tool and should use it when evidence is insufficient.

**Design:**

Add to the prompt:

```markdown
## Available Tools

You have access to the following tools during synthesis:

- `read_file`, `write_file`, `list_files` — filesystem access to the workspace
- `list_references`, `read_reference` — access to methodology guides
- `dispatch_subagents` — **spawn additional research subagents** to fill evidence gaps

### When to use `dispatch_subagents`

If your Coverage Gate (Step 2) determines evidence is insufficient, call
`dispatch_subagents` with a JSON array of remediation tasks instead of writing
a Remediation Request document. The system will execute these tasks and return
their results to you. You can then re-evaluate and proceed to write the report.

You have a maximum of {max_remediation_rounds} remediation rounds. Use them wisely.
After the final round, you must write the best report possible with available evidence.
```

**Subtasks:**

- [x] **3.5.1** — Update `prompts/lead_synthesis.md` to document `dispatch_subagents` and the remediation round budget.
- [x] **3.5.2** — In `lead.synthesize()`, inject `max_remediation_rounds` and current round count into the prompt.
- [x] **3.5.3** — After each remediation round, re-read findings and append new findings content to the conversation so the Lead can see them.

---

### Task 3.6 — Simplify `main.py` Orchestration

**Files:** `main.py`

Since the Lead now controls remediation internally (via the `dispatch_subagents` tool during synthesis), `main.py` stays mostly the same. The loop is inside `synthesize()`, not in `main.py`.

**Design:**

The only change to `main.py`:

```python
# After subagents complete, call synthesize (which may internally trigger more subagents)
print("\n--- Synthesizing findings (may trigger remediation rounds) ---")
await lead.synthesize(config)
```

**Subtasks:**

- [x] **3.6.1** — Update the print message in `main.py` to indicate potential remediation.
- [x] **3.6.2** — Pass `config.max_remediation_rounds` through to ensure it's respected.
- [x] **3.6.3** — Log remediation round activity to stdout for user visibility.

---

### Task 3.7 — Config Updates

**Files:** `config.py`

**Subtasks:**

- [x] **3.7.1** — Add `max_remediation_rounds: int = 2` to `Config` dataclass.
- [x] **3.7.2** — Add `--max-remediation-rounds` CLI arg in `main.py`.

---

### Task 3.8 — Testing

**Files:** `tests/`

**Subtasks:**

- [x] **3.8.1** — Unit test: `get_tools_for_profile()` returns correct tools for each profile.
- [x] **3.8.2** — Unit test: `list_tool_profiles()` returns expected structure.
- [x] **3.8.3** — Unit test: `lead.plan()` defaults missing `tool_profile` to `"full"`.
- [x] **3.8.4** — Unit test: `subagent.run()` uses the correct tool set based on `tool_profile`.
- [ ] **3.8.5** — Integration test (manual): run full pipeline with a query that should trigger remediation, verify the Lead calls `dispatch_subagents` and the final report incorporates remediation findings.

---

## Key Design Decisions

### Why the loop is inside `synthesize()`, not `main.py`

The Lead agent is the one with the judgment to decide whether evidence is sufficient. Making `main.py` orchestrate remediation would require parsing the Lead's output to detect remediation requests, then feeding results back — essentially reimplementing what the tool-use loop already does. By giving the Lead a `dispatch_subagents` tool, the existing provider tool-use loop handles the back-and-forth naturally.

### Why tool profiles instead of arbitrary tool lists

Allowing the Lead to specify arbitrary tools would require it to know tool schemas — complex and error-prone. Named profiles are simpler, safer, and extensible. New tools get added to profiles, not to every prompt.

### Why cap remediation rounds

Without a cap, a perfectionist Lead could loop forever chasing marginal evidence improvements. The cap forces the Lead to write the best report possible with what it has, and honestly disclose remaining gaps.

### Why not a separate "Citation Agent"

The synthesis prompt already handles citation verification as part of its quality gates. A separate agent adds latency and complexity for marginal benefit at this stage. It can be added later as Task 3.9+ if citation quality proves insufficient.

---

## Dependency Graph

```
3.1 (Tool Registry)
 ├──→ 3.2 (Inject profiles into Lead prompt)
 │     └──→ 3.3 (Subagent respects profiles)
 └──→ 3.4 (dispatch_subagents tool)
       └──→ 3.5 (Update synthesis prompt)
             └──→ 3.6 (main.py updates)

3.7 (Config) ──→ 3.4, 3.6

3.8 (Testing) — after all above
```

Parallelizable: 3.2 and 3.4 can be developed in parallel after 3.1 is done.
