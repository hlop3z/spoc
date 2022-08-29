"""
    Exception & Error Messages
"""


class MissingValue(Exception):
    """Base class for other exceptions"""


def error_message(message):
    """Error Message"""

    outlined = f"{ '~' * (len(message) + 4)}"
    return f"\n{outlined}\n~ {message} ~\n{outlined}"
