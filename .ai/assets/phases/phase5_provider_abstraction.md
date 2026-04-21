# Phase 5: Provider Abstraction and Multi-CLI Support

## Overview
This phase aims to decouple the core execution logic from the Gemini CLI, allowing the bot to support multiple AI CLI tools (specifically Gemini and Claude). It involves refactoring the subprocess management into a more generic and extensible architecture.

## Goals
1.  **Generic Subprocess Architecture**: Abstract the current `GeminiSubprocess` into a base `SubProcess` class to handle common concerns like streaming, retry logic, and input handling.
2.  **Multi-Provider Support**: Implement specific subclasses for Gemini (`GeminiSubprocess`) and Claude (`ClaudeSubprocess`).
3.  **CLI Flag for Provider Selection**: Allow users to specify the provider when starting the server via a `--provider` flag.
4.  **Refactor Dependencies**: Update all modules (handlers, orchestrator, review engine) to use the generic interface.

## Technical Details

### 1. Refactor `src/execution/subprocess_runner.py`
- Define an abstract base class `BaseSubprocess` (or similar).
- Move core streaming and error handling logic to the base class.
- Create `GeminiSubprocess` and `ClaudeSubprocess` as specialized implementations.
- Generalize `run_gemini_subprocess_stream` to `run_subprocess_stream` which factory-creates the correct runner based on configuration.

### 2. Configuration Updates (`src/infra/config.py`)
- Add `CLI_PROVIDER` to `AppSettings`.
- Supported values: `gemini`, `claude`.

### 3. CLI Entry Point (`main.py` and `src/app/main.py`)
- Use `argparse` to handle `--provider` flag.
- Override `settings.app.cli_provider` if the flag is provided.

### 4. Integration
- Update `src/interfaces/telegram/handlers.py` to use the new generic runner.
- Update `src/workflow/orchestrator.py` and `src/review/engine.py`.

## Success Criteria
- [ ] Subprocess execution is abstracted into a clean class hierarchy.
- [ ] The bot can be started with `python main.py --provider claude` or `python main.py --provider gemini`.
- [ ] Existing Gemini functionality remains unchanged (no regressions).
- [ ] Claude CLI is successfully integrated and functional (assuming `claude` CLI is installed).

## References
- Current implementation: `src/execution/subprocess_runner.py`
- Entry point: `main.py`
