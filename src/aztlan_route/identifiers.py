"""Shared validation for identifiers used in paths and persistent storage."""
from __future__ import annotations

import re

_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_identifier(value: object, *, label: str = "identifier") -> str:
    if not isinstance(value, str) or not _SAFE_IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"Invalid {label}: use 1-64 ASCII letters, digits, underscores or hyphens"
        )
    return value
