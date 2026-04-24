import json
import re
from pathlib import Path
from typing import Any


def get_project_name(path: str | Path | None = None) -> str:
    """Get the Gemini CLI project name from a directory path.

    By default, uses the current working directory's name.
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path).resolve()

    return path.name


def get_session_id_by_prompt(
    project_name: str, prompt_prefix: str, n: int = 50
) -> str | None:
    """Extract a session ID from the Gemini CLI history by comparing prompt prefix.

    Searches in ~/.gemini/tmp/{project_name}/chats/ for the first message matching
    the provided prompt_prefix (truncated to n characters).

    Args:
        project_name: The name of the project (e.g., 'deep-research').
        prompt_prefix: The text to match against the start of the first prompt.
        n: The number of characters to compare.

    Returns:
        The sessionId string if found, else None.
    """
    history_dir = Path.home() / ".gemini" / "tmp" / project_name / "chats"
    if not history_dir.exists():
        return None

    # Sort by mtime to check newest sessions first
    session_files = sorted(
        history_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
    )

    for session_file in session_files:
        try:
            with open(session_file, "r") as f:
                data = json.load(f)

            messages = data.get("messages", [])
            if not messages:
                continue

            # The first message is typically from the user (the initial prompt)
            first_msg = messages[0]
            if first_msg.get("type") != "user":
                continue

            content_list = first_msg.get("content", [])
            if not content_list or not isinstance(content_list, list):
                continue

            # Extract text from the first content block
            first_text = content_list[0].get("text", "")

            # Compare prefixes
            if first_text[:n] == prompt_prefix[:n]:
                return data.get("sessionId")

        except (json.JSONDecodeError, OSError, KeyError, IndexError):
            continue

    return None


def extract_json(text: str) -> Any:
    """Extract the first valid JSON object or array from a string.

    Use this when JSON is expected but not guaranteed, or when you want to handle
    the absence of JSON gracefully (it returns None).

    Tries multiple strategies:
    1. Direct parsing
    2. Markdown code blocks (```json ... ```)
    3. Finding outermost delimiters ([ ... ] or { ... })
    """
    if not text:
        return None

    text = text.strip()

    # 1. Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try to find markdown code blocks
    code_block_patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
    ]
    for pattern in code_block_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    # 3. Try to find the outermost delimiters.
    # We want to find the one that starts first.
    start_array = text.find("[")
    start_obj = text.find("{")

    # Define candidates to try in order of their appearance
    candidates = []
    if start_array != -1 and start_obj != -1:
        if start_array < start_obj:
            candidates = [("[", "]"), ("{", "}")]
        else:
            candidates = [("{", "}"), ("[", "]")]
    elif start_array != -1:
        candidates = [("[", "]")]
    elif start_obj != -1:
        candidates = [("{", "}")]

    for start_char, end_char in candidates:
        s = text.find(start_char)
        e = text.rfind(end_char)
        if s != -1 and e != -1 and e > s:
            potential_json = text[s : e + 1]
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError:
                continue

    return None


def extract_json_or_raise(
    text: str, error_msg: str = "No valid JSON found in response."
) -> Any:
    """Extract JSON or raise ValueError if none found.

    Use this for mandatory structured data (e.g. lead's research plan).
    """
    result = extract_json(text)
    if result is None:
        raise ValueError(error_msg)
    return result


def get_safe_path(requested_path: str | Path, workspace: Path) -> Path:
    """Resolves a path and ensures it is within the workspace root.

    Args:
        requested_path: The relative or absolute path requested by the agent.
        workspace: The absolute path to the allowed workspace root.

    Returns:
        A resolved Path object within the workspace.

    Raises:
        PermissionError: If the path escapes the workspace.
    """
    ws = workspace.resolve()
    # If path is absolute, it must be absolute *within* the workspace or relative to it
    target = (ws / requested_path).resolve()

    if not target.is_relative_to(ws):
        raise PermissionError(f"Access denied: Path '{requested_path}' escapes the workspace.")

    return target


def get_provider_name(model_name: str) -> str:
    """Derive the provider name ('anthropic' or 'gemini') from the model name."""
    m = model_name.lower()
    if "gemini" in m:
        return "gemini"
    if "claude" in m or "anthropic" in m or "sonnet" in m or "opus" in m:
        return "anthropic"
    # Fallback default
    return "gemini"
