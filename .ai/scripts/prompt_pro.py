import sys
import subprocess


def main():
    if len(sys.argv) < 2:
        print("Usage: python .ai/scripts/prompt_pro.py <prompt>")
        sys.exit(1)

    # Join all arguments as a single prompt
    prompt = " ".join(sys.argv[1:])

    # Command to run gemini -m pro -p "prompt"
    command = ["gemini", "-m", "pro", "-p", prompt]

    try:
        # Run the command and let it output directly to terminal
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(
            "Error: 'gemini' command not found. Please ensure it's installed and in your PATH."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
