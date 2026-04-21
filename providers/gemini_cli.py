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
) -> str:
    """Run a prompt through the Gemini CLI."""
    env = os.environ.copy()
    temp_system_file = None

    if system:
        temp_system_file = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        temp_system_file.write(system)
        temp_system_file.close()
        env["GEMINI_SYSTEM_MD"] = temp_system_file.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "gemini",
            "-p", prompt,
            "-m", model,
            "--yolo",  # Automatically approve tool usage if any
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace,
            env=env,
        )
        if os.environ.get("DEBUG_GEMINI_CLI"):
            print(f"DEBUG: Running Gemini CLI in {workspace}")
            print(f"DEBUG: Cmd: {' '.join(proc.args if hasattr(proc, 'args') else [])}")

        stdout, stderr = await proc.communicate()

        if os.environ.get("DEBUG_GEMINI_CLI"):
            if stdout: print(f"DEBUG: STDOUT: {stdout.decode()[:200]}...")
            if stderr: print(f"DEBUG: STDERR: {stderr.decode()}")

        if proc.returncode != 0:
            raise RuntimeError(f"Gemini CLI error (rc={proc.returncode}): {stderr.decode()}")

        return stdout.decode()
    finally:
        if temp_system_file:
            os.unlink(temp_system_file.name)
