#!/usr/bin/env python3
import sys
from pathlib import Path


def main():
    rel_path = sys.argv[1] if len(sys.argv) > 1 else "."
    workspace = Path.cwd().resolve()

    try:
        target = (workspace / rel_path).resolve()
        if not target.is_relative_to(workspace):
            print(f"Error: Path '{rel_path}' is outside the workspace.")
            sys.exit(1)

        if not target.exists():
            print(f"Error: Directory '{rel_path}' does not exist.")
            sys.exit(1)

        if not target.is_dir():
            print(f"Error: '{rel_path}' is not a directory.")
            sys.exit(1)

        entries = sorted(target.iterdir())
        if not entries:
            print("(empty)")
        else:
            for e in entries:
                prefix = "[DIR] " if e.is_dir() else ""
                print(f"{prefix}{e.relative_to(workspace)}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
