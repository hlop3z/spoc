from pathlib import Path
import argparse
import subprocess
from functools import partial

# Define commands for various operations
CMD_DEV = "python -m mkdocs serve --dev-addr 0.0.0.0:8056"
CMD_DEPLOY = "python -m mkdocs gh-deploy --force"
CMD_MIKE = "python -m mike"


def execute_command(docs_dir: Path, command: str) -> None:
    """Execute a command in the specified directory."""
    try:
        subprocess.run(command, cwd=docs_dir, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command '{command}': {e}")


def get_args() -> argparse.Namespace:
    """Set up CLI argument parser."""
    parser = argparse.ArgumentParser(description="Manage Documentation Tasks")
    parser.add_argument(
        "-gh", "--github", action="store_true", help="Deploy to GitHub pages"
    )
    parser.add_argument(
        "-m", "--mike", action="store_true", help="Use Mike for versioning"
    )
    parser.add_argument(
        "-r", "--reset", action="store_true", help="Reset Mike versioning"
    )
    parser.add_argument("-l", "--list", action="store_true", help="Mike list versions")
    parser.add_argument(
        "-sd", "--set-default", type=str, help="Set default version with Mike"
    )

    # Parse arguments
    return parser.parse_args()


def main(docs_dir: Path):
    """
    Execute A Command

    ### Usage

    - **Dev Docs**: `python docs.py`
    - **Deploy to GitHub**: `python docs.py -gh`
    - **Use Mike**: `python docs.py -m`
    - **Reset Versioning**: `python docs.py -m -r`
    - **Set Default Version**: `python docs.py -m -sd v1.0`
    """

    # Prepare command execution function
    command = partial(execute_command, docs_dir)

    # Get command-line arguments
    args = get_args()

    # Determine which command to run based on arguments
    if args.mike:
        mike_command = CMD_MIKE
        if args.github:
            mike_command += " deploy --push"
        elif args.reset:
            mike_command += " delete --all"
        elif args.set_default:
            mike_command += f" set-default {args.set_default}"
        else:
            mike_command += " serve"
        command(mike_command)
    elif args.github:
        command(CMD_DEPLOY)
    else:
        command(CMD_DEV)


if __name__ == "__main__":
    # Base Directory
    base_dir = Path(__file__).resolve().parents[1]
    docs_dir = base_dir / "docs"

    # Execute Command
    main(docs_dir)
