#!/usr/bin/env python3
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Error: Missing file path")
        sys.exit(1)

    rel_path = sys.argv[1]
    workspace = Path.cwd().resolve()

    try:
        target = (workspace / rel_path).resolve()
        if not target.is_relative_to(workspace):
            print(f"SANDBOX ERROR: Path '{rel_path}' is outside the workspace.")
            sys.exit(1)

        if not target.exists():
            print(f"Error: File '{rel_path}' does not exist.")
            sys.exit(1)

        if not target.is_file():
            print(f"Error: '{rel_path}' is not a file.")
            sys.exit(1)

        print(target.read_text())
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
