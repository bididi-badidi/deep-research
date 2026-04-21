"""Phase 2: Gemini CLI backend via asyncio.create_subprocess_exec."""
from __future__ import annotations

import asyncio


async def run(
    *,
    model: str,
    system: str,
    prompt: str,
    workspace: str = "./workspace",
) -> str:
    """Run a prompt through the Gemini CLI."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    proc = await asyncio.create_subprocess_exec(
        "gemini",
        "-model", model,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workspace,
    )
    stdout, stderr = await proc.communicate(full_prompt.encode())

    if proc.returncode != 0:
        raise RuntimeError(f"Gemini CLI error (rc={proc.returncode}): {stderr.decode()}")

    return stdout.decode()
