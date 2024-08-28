import argparse
import re
import sys
from pathlib import Path
import subprocess

# Define the path to your __about__.py file
ABOUT_FILE = Path("src/spoc/__about__.py")


def read_version(file_path):
    """Read the current version from __about__.py."""
    with open(file_path, "r") as f:
        content = f.read()
    match = re.search(r"__version__ = ['\"]([^'\"]*)['\"]", content)
    if match:
        return match.group(1)
    raise ValueError("Version not found in __about__.py")


def write_version(file_path, new_version):
    """Write the new version to __about__.py."""
    with open(file_path, "r") as f:
        content = f.read()
    new_content = re.sub(
        r"__version__ = ['\"]([^'\"]*)['\"]",
        f'''__version__ = "{new_version}"''',
        content,
    )
    with open(file_path, "w") as f:
        f.write(new_content)
    print(f"Updated version to {new_version}")


def bump_version(version, bump_type):
    """Bump the version number."""
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError("Invalid bump type. Choose 'major', 'minor', or 'patch'.")
    return f"{major}.{minor}.{patch}"


def commit_changes(version):
    """Commit the changes to Git if commit is specified."""
    subprocess.check_call(["git", "add", "."])
    subprocess.check_call(["git", "commit", "-m", f"v{version}"])
    subprocess.check_call(["git", "push"])


def tag_and_push(version):
    """Create a Git tag and push it to the remote repository."""
    try:
        # Commit Changes
        commit_changes(version)
        # Create a Git tag
        subprocess.check_call(["git", "tag", f"v{version}"])
        # Push the tag to the remote repository
        subprocess.check_call(["git", "push", "origin", f"v{version}"])
        print(f"Git tag v{version} created and pushed.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while tagging or pushing: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Update version in __about__.py.")
    parser.add_argument(
        "--bump", choices=["major", "minor", "patch"], help="Type of version bump."
    )
    parser.add_argument("--set", help="Explicitly set the version.")
    parser.add_argument(
        "-g", "--git", action="store_true", help="Git create tag and push."
    )

    args = parser.parse_args()

    if not ABOUT_FILE.exists():
        print(f"{ABOUT_FILE} does not exist.")
        sys.exit(1)

    current_version = read_version(ABOUT_FILE)

    if args.bump:
        new_version = bump_version(current_version, args.bump)
    elif args.set:
        new_version = args.set
    else:
        print("You must specify either --bump or --set.")
        sys.exit(1)

    # Update Version
    write_version(ABOUT_FILE, new_version)

    # Push Github
    if args.git:
        tag_and_push(new_version)


if __name__ == "__main__":
    main()
