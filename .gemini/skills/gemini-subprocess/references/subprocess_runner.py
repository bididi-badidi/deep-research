import asyncio
import os
import logging
import shlex
from typing import AsyncGenerator
from src.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Always store the logs under this directory
log_dir = os.path.expanduser("/Users/user/Documents/CS/agents/agent-lead/.gemini/logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "subprocess_runner.log")

# Create and configure the file handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Use this function to run a gemini subprocess
async def run_gemini_subprocess_stream(
    prompt: str, working_dir: str = None
) -> AsyncGenerator[str, None]:
    """
    Executes the Gemini CLI as a subprocess and streams its output.

    Args:
        prompt: The prompt to send to the Gemini CLI.
        working_dir: The directory to run the command in. Defaults to current working directory.

    Yields:
        Chunks of output from the subprocess (stdout).
    """
    working_dir = working_dir or settings.app.project_root
    # -p: Non-interactive prompt
    # -y: YOLO mode (auto-approve tool calls)
    # -m pro: Use a pro model for coding tasks
    cmd = f"gemini -p {shlex.quote(prompt)} -y -m pro"

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        cwd=working_dir,
        env={"PYTHONUNBUFFERED": "1"},
    )

    async def read_stream(stream: asyncio.StreamReader) -> AsyncGenerator[str, None]:
        total_bytes = 0
        max_bytes = 1024 * 1024  # 1 MB threshold
        start_time = asyncio.get_running_loop().time()
        max_duration = 3600  # 1 hour timeout

        while True:
            remaining_time = max_duration - (
                asyncio.get_running_loop().time() - start_time
            )
            if remaining_time <= 0:
                logger.error("Subprocess timeout (1 hour reached). Terminating.")
                yield "\n[Error: Process terminated due to 1-hour timeout.]\n"
                break

            try:
                # Read in small chunks for responsiveness, with timeout enforced
                chunk = await asyncio.wait_for(
                    stream.read(1024), timeout=remaining_time
                )
            except asyncio.TimeoutError:
                logger.error("Subprocess timeout (1 hour reached). Terminating.")
                yield "\n[Error: Process terminated due to 1-hour timeout.]\n"
                break

            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                logger.error("Subprocess output exceeded 1MB limit. Terminating.")
                yield "\n[Error: Output exceeded 1MB limit. Truncated.]\n"
                break

            yield chunk.decode(errors="replace")

    try:
        # Stream stdout
        async for chunk in read_stream(process.stdout):
            yield chunk

        # Capture any final stderr after stdout is closed
        stderr_data = await process.stderr.read()
        if stderr_data:
            yield "An internal error occurred during subprocess execution."
            logger.error("Error: %s", str(stderr_data.decode()))

    except Exception as e:
        yield f"\nException occurred: {str(e)}"
    finally:
        if process.returncode is None:
            try:
                process.terminate()
                await process.wait()
            except ProcessLookupError:
                pass


async def main():
    # Example usage:
    prompt = "Create a file named 'hello.txt' with 'Hello World' content"
    print(f"Running subprocess with prompt: {prompt}\n")

    async for output in run_gemini_subprocess_stream(prompt):
        print(output, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
