---
name: gemini-subprocess
description: Run Gemini CLI as a subprocess to perform automated tasks in specific directories. Use this skill when the user is asking to work on a specific project or perform automated actions through a secondary gemini instance. Trigger this skill whenever the user mentions running gemini chat or gemini CLI programmatically or from within another process.
---

# Gemini Subprocess Skill

This skill provides a standardized way to invoke the Gemini CLI as a subprocess for automated, non-interactive tasks.

## Core Command

To run a gemini subprocess effectively, use the following flags:

- `-p <prompt>`: Non-interactive mode with the specified prompt.
- `-y`: YOLO mode, which automatically approves all tool calls (required for non-interactive execution of most tasks).

### How to run

For streaming implementation, see [references/subprocess_runner.py](./references/subprocess_runner.py).

## Workflow for Running a Subprocess

1. **Identify the Directory**: Determine the `cwd` (the project folders live under '/Users/user/Documents/CS/') where the subprocess should run. To enter a project directory, cd to '/Users/user/Documents/CS/<project_name>'
2. **Construct the Prompt**: Be specific about the task the subprocess needs to perform (e.g., "Create a note named 'result.txt' with content 'Task complete'"). If the task is not specific, strip the user's request by removing the gemini CLI command. (For example, strip 'run a gemini process to write testing code for project personal bot' to 'write testing code for project personal bot')
3. **Execute via Shell**: Use a tool like `run_shell_command` or a library like `asyncio.create_subprocess_shell` in Python. Always use a '-m pro' to use pro models when a coding task should be performed.
4. **Capture Output**: Ensure you read both `stdout` and `stderr` to monitor progress and catch errors.

## When to use this skill

- Use this skill whenever the user asks for a "run a subprocess of gemini cli".
- Use this skill to delegate complex, directory-specific tasks that are better handled by a fresh gemini instance.
- Use this skill when you need to perform an action that requires a clean environment or a specific set of tools available to the CLI.

## When Encounter an error

- Feedback to me and terminate the process. Do not run any script not mentioned.

## The Big No No

You are NOT allowed to:

1. Change the settings under ~/.gemini/
2. Make changes to other project not specified.
3. Run chmod without permission, even in YOLO mode.
