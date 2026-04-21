"""Phase 2: Claude CLI backend via asyncio.create_subprocess_exec."""

from __future__ import annotations

import asyncio


async def run(
    *,
    model: str,
    system: str,
    prompt: str,
    workspace: str = "./workspace",
    allowed_tools: list[str] | None = None,
) -> str:
    """Run a prompt through the Claude CLI in non-interactive mode."""
    cmd = [
        "claude",
        "-p",  # print mode
        "--model",
        model,
        "--output-format",
        "text",
    ]
    if system:
        cmd.extend(["--system-prompt", system])
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workspace,
    )
    stdout, stderr = await proc.communicate(prompt.encode())

    if proc.returncode != 0:
        raise RuntimeError(
            f"Claude CLI error (rc={proc.returncode}): {stderr.decode()}"
        )

    return stdout.decode()
