# Phase 4: Automated Code Review & PR Workflow (Refined)

## Goals

Implement a robust, state-machine driven automated coding workflow using Gemini CLI subprocesses. This workflow handles iterative coding, automated reviews, and PR management with clear state transitions and specialized components.

## Subtasks

### Subtask 1: Workflow State Machine Design

- [x] **Description:** Design and implement a formal workflow state machine that controls transitions between different phases of the task (e.g., `CODING`, `REVIEWING`, `FIXING`, `PR_PENDING`, `COMPLETED`).
- [x] **Deliverables:**
  - Define states and valid transitions in `src/state.py`.
  - Implement a `WorkflowManager` that enforces these transitions.

### Subtask 2: Code Review Component & Parser

- [x] **Description:** Create a dedicated component to execute the `/code-review` command and parse its output to determine the next logical step in the workflow.
- [x] **Deliverables:**
  - `CodeReviewRunner` (implemented as `ReviewEngine`) class in `src/review_engine.py`.
  - Logic to decide between `CONTINUE_CODING`, `RETRY_FIX`, or `EXIT_LOOP`.
  - Robust parsing in `src/review_parser.py` (JSON and Text/Regex support).

### Subtask 3: Retry Decision Logic

- [x] **Description:** Implement the business logic that evaluates code review results (severity, number of issues) to decide if a retry of the coding task is necessary.
- [x] **Deliverables:**
  - `RetryPolicy` class in `src/retry_logic.py`.
  - Threshold-based decision logic (e.g., retry if any `MEDIUM` or `HIGH` issues exist).

### Subtask 4: Feedback Loop & Session Management

- [x] **Description:** Develop the mechanism to extract actionable error messages from the code review and pass them to a fresh Gemini CLI session for targeted fixing.
- [x] **Deliverables:**
  - `FeedbackManager` in `src/feedback_manager.py` to format findings into prompts.
  - Integration with `orchestrator.py` to start fix sessions.

### Subtask 5: PR Automation & Finalization

- [x] **Description:** Automate the final steps of the workflow, including Git staging, committing, and Pull Request creation using the GitHub CLI.
- [x] **Deliverables:**
  - `GitAutomationEngine` in `src/git_automation.py` for PR lifecycle management.
  - `GitEngine` in `src/git_engine.py` for low-level git/gh command execution.
  - Final state transitions and PR reporting.
