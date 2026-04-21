"""Filesystem tools shared by all agents."""

from __future__ import annotations

import asyncio
from pathlib import Path

# Project-level references directory (read-only, not scoped to workspace).
REFERENCES_DIR = Path(__file__).parent / "references"

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read the contents of a file in the workspace directory.",
    "parameters": {
        "path": {
            "type": "string",
            "description": "Relative file path within the workspace",
        },
    },
    "required": ["path"],
}

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "Write content to a file in the workspace. Creates parent directories as needed.",
    "parameters": {
        "path": {
            "type": "string",
            "description": "Relative file path within the workspace",
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file",
        },
    },
    "required": ["path", "content"],
}

LIST_FILES_TOOL = {
    "name": "list_files",
    "description": "List files and directories in the workspace.",
    "parameters": {
        "path": {
            "type": "string",
            "description": "Relative directory path within the workspace (use '.' for root)",
        },
    },
    "required": ["path"],
}

LIST_REFERENCES_TOOL = {
    "name": "list_references",
    "description": (
        "List all available reference documents (methodology guides, format templates, "
        "framework primers, etc.). Call this first to discover what references exist "
        "before calling read_reference."
    ),
    "parameters": {},
    "required": [],
}

READ_REFERENCE_TOOL = {
    "name": "read_reference",
    "description": (
        "Read a reference document by filename (e.g. 'finer-pico-primer.md'). "
        "Use list_references first to see what is available. Reference files are "
        "read-only methodology guides — do not attempt to write to them."
    ),
    "parameters": {
        "filename": {
            "type": "string",
            "description": "Filename of the reference document (basename only, e.g. 'finer-pico-primer.md')",
        },
    },
    "required": ["filename"],
}

FILE_TOOLS: list[dict] = [
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    LIST_FILES_TOOL,
    LIST_REFERENCES_TOOL,
    READ_REFERENCE_TOOL,
]

TOOL_PROFILES: dict[str, list[dict]] = {
    "full": FILE_TOOLS,
    "read_only": [
        READ_FILE_TOOL,
        LIST_FILES_TOOL,
        LIST_REFERENCES_TOOL,
        READ_REFERENCE_TOOL,
    ],
    "write_only": [WRITE_FILE_TOOL],
    "search_only": [],  # Google Search grounding only, no FS tools
}


def get_tools_for_profile(profile: str) -> list[dict]:
    """Return the tool list for a named profile. Defaults to 'full'."""
    return TOOL_PROFILES.get(profile, TOOL_PROFILES["full"])


def list_tool_profiles() -> dict[str, list[str]]:
    """Return a summary of profiles and their tool names (for prompt injection)."""
    return {name: [t["name"] for t in tools] for name, tools in TOOL_PROFILES.items()}


async def execute(name: str, args: dict, workspace: Path) -> str:
    """Execute a filesystem tool within the sandboxed workspace."""
    ws = workspace.resolve()

    def _safe_path(rel_path: str) -> Path:
        target = (ws / rel_path).resolve()
        if not target.is_relative_to(ws):
            raise PermissionError(f"path escapes workspace: {rel_path}")
        return target

    try:
        if name == "read_file":
            target = _safe_path(args["path"])
            return await asyncio.to_thread(target.read_text)

        if name == "write_file":
            target = _safe_path(args["path"])
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(target.write_text, args["content"])
            return f"Written to {args['path']}"

        if name == "list_files":
            target = _safe_path(args["path"])
            if not await asyncio.to_thread(target.is_dir):
                return f"Error: {args['path']} is not a directory"

            def _list():
                entries = sorted(target.iterdir())
                if not entries:
                    return "(empty)"
                return "\n".join(
                    f"{'[dir] ' if e.is_dir() else ''}{e.relative_to(ws)}"
                    for e in entries
                )

            return await asyncio.to_thread(_list)

        if name == "list_references":

            def _list_refs():
                if not REFERENCES_DIR.is_dir():
                    return "No references directory found."
                entries = sorted(REFERENCES_DIR.iterdir())
                if not entries:
                    return "(no reference files)"
                return "\n".join(e.name for e in entries if e.is_file())

            return await asyncio.to_thread(_list_refs)

        if name == "read_reference":
            filename = args["filename"]
            # Reject any path traversal attempts
            if "/" in filename or "\\" in filename or ".." in filename:
                return "Error: filename must be a basename only, not a path."
            target = (REFERENCES_DIR / filename).resolve()
            if not target.is_relative_to(REFERENCES_DIR.resolve()):
                return "Error: path escapes references directory."
            if not target.exists():
                return f"Error: reference '{filename}' not found. Use list_references to see available files."
            return await asyncio.to_thread(target.read_text)

        return f"Error: unknown tool '{name}'"
    except Exception as e:
        return f"Error: {e}"
