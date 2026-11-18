"""Validated provider catalog and provider metadata."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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
        if not self.id or not self.id.replace("-", "").isalnum():
            raise ValueError("Provider id must be a non-empty alphanumeric identifier")
        parsed = urlparse(self.url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Provider URL must be an absolute HTTPS URL")
        if not self.browser_support or not set(self.browser_support) <= SUPPORTED_BROWSERS:
            raise ValueError("Provider has unsupported browser configuration")
        if self.integration_mode not in SUPPORTED_MODES:
            raise ValueError("Unknown provider integration mode")
        if self.automation_allowed and self.integration_mode != "documented_api":
            raise ValueError("Automation requires an explicitly reviewed documented integration")

def load_providers(path: Path) -> list[Provider]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported provider catalog schema")
    entries = payload.get("providers")
    if not isinstance(entries, list):
        raise ValueError("Provider catalog must contain a providers array")
    providers = [Provider(**entry) for entry in entries]
    ids = [provider.id for provider in providers]
    if len(ids) != len(set(ids)):
        raise ValueError("Provider ids must be unique")
    return providers
