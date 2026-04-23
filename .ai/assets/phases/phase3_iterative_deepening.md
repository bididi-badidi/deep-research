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
[x] 3.1.1-3.1.4 Refactor tools, define profiles, add registry helpers, unit test.

### Task 3.2 — Inject Tool Profile Info into Lead's Planning Prompt
[x] 3.2.1-3.2.4 Placeholder in lead_planning.md, injection in lead.py, update tool schema, validation.

### Task 3.3 — Subagent Respects Tool Profile
[x] 3.3.1-3.3.3 Subagent resolves tool_profile, passes correct tools to provider, unit test.

### Task 3.4 — `dispatch_subagents` Tool for the Lead
[x] 3.4.1-3.4.5 Define tool, implement handler in synthesize(), add remediation round cap.

### Task 3.5 — Update Synthesis Prompt for Iterative Awareness
[x] 3.5.1-3.5.3 Document tool in lead_synthesis.md, inject round budget, re-read findings after remediation.

### Task 3.6 — Simplify `main.py` Orchestration
[x] 3.6.1-3.6.3 Indicative console output, pass config, log remediation round activity.

### Task 3.7 — Config Updates
[x] 3.7.1-3.7.2 Add max_remediation_rounds to Config and CLI args.

### Task 3.8 — Testing & Verification
- [x] 3.8.1-3.8.4 Unit tests for profiles, lead.plan defaults, subagent tool set validation.
- [ ] **3.8.5** — Integration test (manual): run full pipeline with a query that should trigger remediation, verify the Lead calls `dispatch_subagents` and the final report incorporates remediation findings.

### Task 3.9 — Robust JSON parsing for CLI backend
[x] 3.9.1-3.9.3 Create utils.py JSON helpers, unit test, integrate into lead and receptionist agents.

### Task 3.10 — Multi-turn conversation support for CLI backend
[x] 3.10.1-3.10.3 Session ID support in CLI runners, history flattening fix, CLI synthesis loop.

### Task 3.11 — Tighten CLI security by restricting subagent tool permissions
[x] 3.11.1-3.11.3 Map tool_profile to CLI-specific profiles, --approval-mode support, permission scoping.

### Task 3.12 — Move CLI backend to Gemini
[x] 3.12.1-3.12.2 Default Receptionist and Lead to Gemini CLI, system prompt support.

### Task 3.13 — Implement custom tool scripts for CLI subagents (F4 Hardening)
[x] 3.13.1-3.13.4 Sandboxed tool scripts (read/write/list), workspace boundary enforcement via Path.cwd().resolve(), Gemini CLI extension wiring via MCP server + excludeTools, path traversal escape verified.
