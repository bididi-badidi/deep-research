---
name: Phase 6 - Hub-and-Spoke Architecture
description: Redesign the bot to drive AI CLIs against arbitrary target projects without copying code or skills into each project directory.
type: project
---

# Phase 6: Hub-and-Spoke Architecture

## Problem Statement

The bot (the "hub") lives in one repo but needs to drive Gemini CLI and Claude Code against other projects (the "spokes"). When a CLI runs in `/target/project/`, it only discovers context from that directory — the hub's `.gemini/skills/`, workflow orchestration, and pipeline logic are invisible. Copying Python code or skill files into every target project is not feasible.

## Design Overview

```
┌───────────────────────────────────────────────────┐
│              HUB (this repo)                       │
│                                                   │
│  Telegram Bot → Orchestrator → Pipeline Runner    │
│       ↓              ↓              ↓             │
│  Receptionist    SubProcess      Review/Git       │
│  Agent           Factory         Steps            │
└──────────┬────────────┬───────────────────────────┘
           │            │
           │  (subprocess with injected prompt/system-instruction)
           ↓            ↓
┌──────────────┐  ┌──────────────┐
│  Project B   │  │  Project C   │
│  (cwd)       │  │  (cwd)       │
└──────────────┘  └──────────────┘
```

**Core principle:** The CLI always runs with `cwd` = target project (so it sees that project's files/git/tests), but pipeline instructions are injected via prompt or system-instruction flags — not discovered from the filesystem.

---

## Key Design Decisions

### 1. Prompt-Injected Context (not file-based skills)

Instead of relying on the CLI discovering `.gemini/skills/` in the target directory, inject workflow instructions directly into the prompt.

**Implementation:** A `ContextInjector` class reads templates from the hub's `templates/` directory and prepends them to every CLI invocation.

```python
# src/execution/context_injector.py
class ContextInjector:
    def build_prompt(self, user_prompt: str, mode: str = "code") -> str:
        preamble = self._load_template(mode)
        return f"{preamble}\n\n---\nUser task: {user_prompt}"
```

For Gemini CLI, use the `--system-instruction` (or `--si`) flag:
```bash
gemini chat --si "$(cat hub/templates/coding.md)" "actual user prompt"
```

For Claude Code, prepend the template to the user prompt or use `--append-system-prompt`.

**Why:** Zero file copying, zero symlinks. Instructions ride in the prompt.

---

### 2. Project Registry (replaces single `PROJECT_ROOT`)

Maintain a `projects.yaml` at the hub root mapping names/aliases to directories and project-specific metadata.

```yaml
# projects.yaml
projects:
  myapp:
    path: /Users/user/Documents/CS/myapp
    default_branch: main
    test_command: pytest
    lint_command: ruff check .
    language: python
  frontend:
    path: /Users/user/Documents/CS/frontend
    default_branch: main
    test_command: npm test
    lint_command: npm run lint
    language: typescript
```

```python
# src/infra/project_registry.py
@dataclass
class ProjectEntry:
    name: str
    path: Path
    default_branch: str = "main"
    test_command: str = "pytest"
    lint_command: str = "ruff check ."
    language: str = "python"

class ProjectRegistry:
    def resolve(self, query: str) -> ProjectEntry:
        # exact match → fuzzy match → raise AmbiguousProjectError
        ...
```

The "receptionist" is this registry with fuzzy matching — not a separate AI agent. Only escalate to an AI call if the user's intent is genuinely ambiguous.

---

### 3. Separate `pipeline_home` from `target_project`

Refactor `AppSettings` to distinguish between where the hub lives and where the CLI executes.

**Current:**
```python
project_root: Path  # single global, used for both
```

**Proposed:**
```python
# AppSettings
pipeline_home: Path  # this repo — where templates/skills live
# project_root is REMOVED as a global

# Session model gains:
target_project: Optional[ProjectEntry]  # set per-session by receptionist
```

`BaseSubprocess` uses `session.target_project.path` as `cwd`, while loading templates from `settings.app.pipeline_home / "templates"`.

---

### 4. Template Directory

```
templates/
├── coding.md        # System instructions for the coding agent
├── review.md        # Instructions for automated code review
├── testing.md       # Instructions for test interpretation
└── commit.md        # Conventional commit message generation
```

Each workflow step (`coding.py`, `review.py`, etc.) loads its template via `ContextInjector` before invoking the CLI subprocess. Target projects remain unaware of the pipeline.

---

### 5. New Telegram Command: `/target`

Allow the user to switch which project the bot is operating on mid-session:

```
/target myapp        → resolves to /Users/user/Documents/CS/myapp
/target              → shows current target and available projects
```

---

## Files Affected

| File | Change |
|------|--------|
| `src/infra/config.py` | Add `pipeline_home`, remove global `project_root` |
| `src/infra/project_registry.py` | **New** — `ProjectEntry`, `ProjectRegistry`, fuzzy resolve |
| `src/execution/context_injector.py` | **New** — loads templates, builds injected prompts |
| `src/execution/subprocess_runner.py` | Use `session.target_project.path` as `cwd`; pass injected context |
| `src/state/models.py` | Add `target_project: Optional[ProjectEntry]` to `Session` |
| `src/interfaces/telegram/handlers.py` | Add `/target` command handler |
| `src/workflow/steps/*.py` | Use `ContextInjector` for system instructions |
| `projects.yaml` | **New** — project registry config |
| `templates/` | **New** — coding, review, testing, commit instruction templates |
| `.env.example` | Add `PIPELINE_HOME` (optional, defaults to repo root) |

---

## Migration Path (ordered)

1. [ ] Create `projects.yaml` and `ProjectEntry`/`ProjectRegistry` in `src/infra/`
2. [ ] Add `target_project` field to `Session`; add `/target` Telegram command
3. [ ] Create `templates/` directory with initial template files
4. [ ] Implement `ContextInjector` in `src/execution/`
5. [ ] Refactor `BaseSubprocess.build_command()` to accept injected context and use `session.target_project.path` as `cwd`
6. [ ] Update workflow steps to pull templates via `ContextInjector`
7. [ ] Add `pipeline_home` to `AppSettings`; remove global `project_root`
8. [ ] Update `.env.example` and README

## Open Questions

- Should `projects.yaml` be committed to the hub repo, or kept in `.gitignore` (since it contains machine-local paths)?
- Should the `/target` command persist across bot restarts (write to state storage), or be session-only?
- For Gemini CLI: verify the exact flag for system-instruction injection (`--si` vs `--system-instruction` vs stdin piping).
- For Claude Code: confirm whether `--append-system-prompt` is available in the current CLI version.
