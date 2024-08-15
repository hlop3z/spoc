import subprocess
from pathlib import Path
import time

# Watch Dog
import watchdog.events
import watchdog.observers


def shell_cmd(name: str, cmd: str, check: bool = True) -> None:
    """
    Run a shell command and print the name of the command being executed.
    """
    print(f"Running... <{name}>")
    try:
        subprocess.run(cmd, shell=True, check=check)
    except subprocess.CalledProcessError:
        print(f"Error while running {name}")
    # Add Space
    print((72 * "~") + "\n")


def run_linters_and_formatters(path: str) -> None:
    """
    Run linters and formatters on the specified path.
    """
    # Formatters
    shell_cmd("ssort", f"python -m ssort {path}")
    shell_cmd("isort", f"python -m isort --profile black {path}")
    shell_cmd("black", f"python -m black {path}")
    shell_cmd("ruff-format", f"python -m ruff format {path}")

    # Checkers
    # run_shell_command("bandit", f"python -m bandit -r {path_to_watch}")
    shell_cmd("pyright", f"python -m pyright {path}")
    shell_cmd("mypy", f"python -m mypy {path}")
    shell_cmd("ruff-check", f"python -m ruff check {path}")

    # Quality
    shell_cmd("pylint", f"python -m pylint {path}", check=False)


class Handler(watchdog.events.PatternMatchingEventHandler):
    """Watchdog - Event Handler

    Note:
        EVENT_OPTIONS: on_created, on_modified, on_deleted, on_moved, on_any_event

    Methods:
        event_name(self, event): Do something < After > the event happens.

    Example:
        def on_modified(self, event):
            path_to_watch = event.src_path
            # After Event - Do Something ...
    """

    def __init__(self):
        watchdog.events.PatternMatchingEventHandler.__init__(
            self,
            patterns=["*.py"],  # File Types
            ignore_directories=True,
            case_sensitive=False,
        )

    def on_modified(self, event):
        path_to_watch = event.src_path
        print(f"""Fixing... { path_to_watch }""")

        run_linters_and_formatters(path_to_watch)


def server_linter(base_dir, all_folders):
    """Watch Folders"""

    # Watchdog Handler
    event_handler = Handler()
    observer = watchdog.observers.Observer()
    for folder in all_folders:
        observer.schedule(event_handler, path=base_dir / folder, recursive=True)
    observer.start()

    # Run "Server"
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def run_linter(base_dir, all_folders):
    """Run Linter"""

    for folder in all_folders:
        run_linters_and_formatters(base_dir / folder)


if __name__ == "__main__":
    import argparse

    # Base Directory
    base_dir = Path(__file__).parents[1]

    # CLI
    parser = argparse.ArgumentParser(description="Code Linter.")
    parser.add_argument("-w", "--watch", action="store_true", help="Watch Folder")
    parser.add_argument("-t", "--test", action="store_true", help="Test Folder")
    parser.add_argument("-a", "--all", action="store_true", help="Src and Test Folders")

    args = parser.parse_args()

    # Watch Directories
    the_folders = ["src"]  # src | tests
    test_folders = ["tests"]
    if args.test:
        the_folders = test_folders
    if args.all:
        the_folders = ["src", "tests"]

    # Run Linter
    if args.watch:
        server_linter(base_dir, the_folders)
    else:
        run_linter(base_dir, the_folders)
