#!/usr/bin/env python3
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Error: Missing file path")
        sys.exit(1)

    rel_path = sys.argv[1]
    content = sys.stdin.read()
    workspace = Path.cwd().resolve()

    try:
        target = (workspace / rel_path).resolve()
        if not target.is_relative_to(workspace):
            print(f"Error: Path '{rel_path}' is outside the workspace.")
            sys.exit(1)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        print(f"Successfully written to {rel_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
