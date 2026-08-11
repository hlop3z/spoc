"""
Mkdocs-Macros Module

# Learn More. . .
https://mkdocs-macros-plugin.readthedocs.io/en/latest/macros/
"""

from markupsafe import Markup


def format_acronym(text):
    """
    Formats acronyms by wrapping each first letter in parentheses and <strong> tags.
    """

    # Extract the first letter and the rest of the word
    first_letter = text[0]
    rest_of_text = text[1:]

    # Construct the formatted acronym
    formatted_text = f"(<strong>{first_letter}</strong>){rest_of_text}"

    # Markup to mark the string as safe HTML
    return Markup(formatted_text)


def define_env(env):
    """
    This is the hook for defining variables, macros and filters

    - macro: a decorator function, to declare a macro.
    - filter: a function with one of more arguments, used to perform a transformation
    - variables: the dictionary that contains the environment variables
    """

    @env.macro
    def current_year():
        from datetime import UTC, datetime

        return datetime.now(UTC).year

    @env.macro
    def url(url):
        #  env.config.site_name
        site_name = env.conf.get("site_name", "").lower()
        return f"{site_name}{url}"

    @env.macro
    def acronym(text):
        return format_acronym(text)

    @env.macro
    def cli_help(*command):
        """The real `spoc [command] --help` output, captured at build time.

        Runs the shipped parser (`spoc.cli`) in a subprocess, so the CLI page
        cannot drift from the argparse surface — a flag added or reworded in
        the code appears here on the next build (docs-dx, DECISIONS.md:
        "CLI reference generation").
        """
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "spoc.cli", *command, "--help"],
            capture_output=True,
            text=True,
            check=True,
        )
        return f"```text\n{result.stdout.rstrip()}\n```"
