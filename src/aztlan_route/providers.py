"""Validated provider catalog and provider metadata."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .identifiers import validate_identifier

SUPPORTED_BROWSERS = frozenset({"chromium", "firefox"})
SUPPORTED_MODES = frozenset({"manual_browser", "documented_api", "disabled"})


@dataclass(frozen=True, slots=True)
class Provider:
    id: str
    name: str
    url: str
    browser_support: tuple[str, ...]
    integration_mode: str
    automation_allowed: bool
    notes: str

    def __post_init__(self) -> None:
        validate_identifier(self.id, label="provider id")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Provider name must be a non-empty string")
        if not isinstance(self.url, str):
            raise ValueError("Provider URL must be a string")
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Provider URL must be an absolute HTTPS URL")
        if (
            not isinstance(self.browser_support, tuple)
            or not self.browser_support
            or not all(isinstance(item, str) for item in self.browser_support)
            or not set(self.browser_support) <= SUPPORTED_BROWSERS
        ):
            raise ValueError("Provider has unsupported browser configuration")
        if not isinstance(self.integration_mode, str) or self.integration_mode not in SUPPORTED_MODES:
            raise ValueError("Unknown provider integration mode")
        if type(self.automation_allowed) is not bool:
            raise ValueError("automation_allowed must be a boolean")
        if not isinstance(self.notes, str):
            raise ValueError("Provider notes must be a string")
        if self.automation_allowed and self.integration_mode != "documented_api":
            raise ValueError("Automation requires an explicitly reviewed documented integration")


def load_providers(path: Path) -> list[Provider]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported provider catalog schema")
    entries = payload.get("providers")
    if not isinstance(entries, list):
        raise ValueError("Provider catalog must contain a providers array")
    providers = []
    required = set(Provider.__dataclass_fields__)
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError("Each provider entry must contain exactly the required fields")
        values = dict(entry)
        if isinstance(values.get("browser_support"), list):
            values["browser_support"] = tuple(values["browser_support"])
        providers.append(Provider(**values))
    ids = [provider.id for provider in providers]
    if len(ids) != len(set(ids)):
        raise ValueError("Provider ids must be unique")
    return providers
