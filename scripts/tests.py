import subprocess
from pathlib import Path
import argparse
import shutil

# Define the commands
CMD_MAIN = "python main.py"
CMD_INIT = "spoc-init"


def execute_command(the_dir: Path, command: str, params: str = ""):
    """Execute a shell command with optional parameters."""
    try:
        full_command = f"{command} {params}".strip()
        # Optional: Print the command being executed
        print(f"Executing: {full_command}\n")
        subprocess.run(full_command, cwd=the_dir, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command '{command}': {e}")


def main():
    # Base Directory
    base_dir = Path(__file__).parents[1]
    test_dir = base_dir / "tests"

    # CLI
    parser = argparse.ArgumentParser(description="Test Manager.")
    parser.add_argument("name", choices=["spoc", "init"], help="Test to run")
    parser.add_argument(
        "-a",
        "--args",
        nargs=argparse.REMAINDER,
        help="Additional arguments for the command",
    )

    # Parse arguments
    args = parser.parse_args()

    # Determine which command to run
    params = " ".join(args.args or [])
    if args.name:
        match args.name:
            case "spoc":
                execute_command(test_dir, CMD_MAIN, params)
            case "init":
                test_dir = base_dir / "test_init"
                try:
                    shutil.rmtree(test_dir)
                except FileNotFoundError:
                    pass
                test_dir.mkdir(parents=True, exist_ok=True)
                execute_command(test_dir, CMD_INIT)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
