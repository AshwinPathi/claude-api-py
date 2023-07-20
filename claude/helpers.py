"""Generic helper functions for random utilities."""
from typing import Tuple, Optional


def is_file_text_based(file_path: str) -> Tuple[bool, Optional[str]]:
    """Really bad way to determine whether or not a file is text based or not.
    This is used so that we don't upload non-binary files to the file converstion
    API.

    Returns [bool, file contents], where bool is true if the file is text-based.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return True, f.read()
    except UnicodeDecodeError:
        return False, None
