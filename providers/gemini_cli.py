"""Phase 2: Gemini CLI backend via asyncio.create_subprocess_exec."""

from __future__ import annotations

import asyncio
import os
import tempfile


async def run(
    *,
    model: str,
    system: str,
    prompt: str,
    workspace: str = "./workspace",
    approval_mode: str = "auto_edit",
    cli_session_id: str | None = None,
) -> str:
    """Run a prompt through the Gemini CLI."""
    env = os.environ.copy()
    temp_system_file = None

    if system:
        temp_system_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        )
        temp_system_file.write(system)
        temp_system_file.close()
        env["GEMINI_SYSTEM_MD"] = temp_system_file.name

    cmd = [
        "gemini",
        "-p",
        prompt,
        "-m",
        model,
        "--approval-mode",
        approval_mode,
    ]

    if cli_session_id:
        cmd.extend(["--resume", cli_session_id])

    # Add a small random delay to avoid hitting quota limits in parallel execution
    import random

    await asyncio.sleep(random.uniform(0.5, 2.0))

    try:
        if os.environ.get("DEBUG_GEMINI_CLI"):
            print(f"DEBUG: Running Gemini CLI in {workspace}")
            print(f"DEBUG: Cmd: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace,
            env=env,
        )

        stdout, stderr = await proc.communicate()

        if os.environ.get("DEBUG_GEMINI_CLI"):
            if stdout:
                print(f"DEBUG: STDOUT: {stdout.decode()[:200]}...")
            if stderr:
                print(f"DEBUG: STDERR: {stderr.decode()}")

        if proc.returncode != 0:
            raise RuntimeError(
                f"Gemini CLI error (rc={proc.returncode}): {stderr.decode()}"
            )

        return stdout.decode()
    finally:
        if temp_system_file:
            os.unlink(temp_system_file.name)
