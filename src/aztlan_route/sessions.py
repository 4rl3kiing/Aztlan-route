"""Discover local browser profiles without reading authentication contents."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .providers import SUPPORTED_BROWSERS


@dataclass(frozen=True, slots=True)
class BrowserProfile:
    provider_id: str
    browser: str
    path: Path


class SessionManager:
    def __init__(self, profiles_root: Path) -> None:
        self.profiles_root = profiles_root

    def list_profiles(self) -> list[BrowserProfile]:
        profiles: list[BrowserProfile] = []
        if not self.profiles_root.is_dir():
            return profiles
        for provider_dir in self.profiles_root.iterdir():
            if not provider_dir.is_dir() or not provider_dir.name.replace("-", "").isalnum():
                continue
            for browser_dir in provider_dir.iterdir():
                if browser_dir.is_dir() and browser_dir.name in SUPPORTED_BROWSERS:
                    profiles.append(BrowserProfile(
                        provider_id=provider_dir.name,
                        browser=browser_dir.name,
                        path=browser_dir,
                    ))
        return sorted(profiles, key=lambda item: (item.provider_id, item.browser))
