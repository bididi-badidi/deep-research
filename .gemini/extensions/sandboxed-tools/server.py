import sys
import json
import subprocess
import os
from pathlib import Path

# Path to the scripts directory relative to this file
SCRIPTS_DIR = Path(__file__).parent / "scripts"
DEBUG_LOGGING = os.getenv("SANDBOXED_TOOLS_DEBUG", "").lower() in ("1", "true", "yes", "on")


def log(msg):
    if not DEBUG_LOGGING:
        return
    sys.stderr.write(f"DEBUG: {msg}\n")
    sys.stderr.flush()


def read_json():
    line = sys.stdin.readline()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        log(f"JSON Decode Error: {e} in line: {line}")
        return None


def write_json(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    log("Sandboxed Tools MCP Server starting...")
    while True:
        req = read_json()
        if req is None:
            break

        method = req.get("method")
        params = req.get("params", {})
        id_ = req.get("id")

        if method == "initialize":
            write_json(
                {
                    "jsonrpc": "2.0",
                    "id": id_,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "sandboxed-tools", "version": "0.1.0"},
                    },
                }
            )
        elif method == "notifications/initialized":
            log("Server initialized.")
            continue
        elif method == "tools/list":
            write_json(
                {
                    "jsonrpc": "2.0",
                    "id": id_,
                    "result": {
                        "tools": [
                            {
                                "name": "sandboxed_read_file",
                                "description": "Read a file securely within the workspace.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Relative path to the file",
                                        }
                                    },
                                    "required": ["path"],
                                },
                            },
                            {
                                "name": "sandboxed_write_file",
                                "description": "Write content to a file securely within the workspace.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Relative path to the file",
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Content to write",
                                        },
                                    },
                                    "required": ["path", "content"],
                                },
                            },
                            {
                                "name": "sandboxed_list_files",
                                "description": "List files and directories securely within the workspace.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {
                                            "type": "string",
                                            "description": "Relative path to the directory (default: '.')",
                                        }
                                    },
                                },
                            },
                        ]
                    },
                }
            )
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments", {})

            result_text = ""
            error = None

            if not isinstance(args, dict):
                error = "Invalid arguments: 'arguments' must be an object"

            tool_name = (
                name.replace("sandboxed_", "")
                if name.startswith("sandboxed_")
                else name
            )

            if error:
                pass
            elif tool_name == "read_file":
                path = args.get("path")
                if not isinstance(path, str) or not path:
                    error = "Invalid arguments: 'path' is required and must be a non-empty string"
                else:
                    proc = subprocess.run(
                        ["python3", str(SCRIPTS_DIR / "read_file.py"), path],
                        capture_output=True,
                        text=True,
                    )
                    result_text = proc.stdout if proc.returncode == 0 else proc.stderr
            elif tool_name == "write_file":
                path = args.get("path")
                if not isinstance(path, str) or not path:
                    error = "Invalid arguments: 'path' is required and must be a non-empty string"
                else:
                    content = args.get("content", "")
                    proc = subprocess.run(
                        ["python3", str(SCRIPTS_DIR / "write_file.py"), path],
                        input=content,
                        capture_output=True,
                        text=True,
                    )
                    result_text = proc.stdout if proc.returncode == 0 else proc.stderr
            elif tool_name == "list_files":
                path = args.get("path", ".")
                if not isinstance(path, str):
                    error = "Invalid arguments: 'path' must be a string"
                else:
                    proc = subprocess.run(
                        ["python3", str(SCRIPTS_DIR / "list_files.py"), path],
                        capture_output=True,
                        text=True,
                    )
                    result_text = proc.stdout if proc.returncode == 0 else proc.stderr
            else:
                error = f"Unknown tool: {name}"

            if error:
                write_json(
                    {
                        "jsonrpc": "2.0",
                        "id": id_,
                        "error": {"code": -32601, "message": error},
                    }
                )
            else:
                write_json(
                    {
                        "jsonrpc": "2.0",
                        "id": id_,
                        "result": {"content": [{"type": "text", "text": result_text}]},
                    }
                )
        else:
            if id_ is not None:
                write_json(
                    {
                        "jsonrpc": "2.0",
                        "id": id_,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}",
                        },
                    }
                )


if __name__ == "__main__":
    main()
