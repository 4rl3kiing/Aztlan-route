"""Launch isolated, persistent provider browser profiles."""
from __future__ import annotations

import getpass
import os
import subprocess
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright

from .identifiers import validate_identifier
from .providers import Provider, SUPPORTED_BROWSERS


def profile_path(root: Path, provider_id: str, browser: str) -> Path:
    validate_identifier(provider_id, label="provider id")
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError("Unsupported browser")
    return root / provider_id / browser


def _apply_windows_acl(path: Path) -> None:
    """Disable inherited ACLs and grant access only to the current user and SYSTEM."""
    username = getpass.getuser()
    if not username or any(char in username for char in '\\\"\n\r'):
        raise RuntimeError("Cannot safely determine the current Windows account")
    subprocess.run(
        [
            "icacls", str(path), "/inheritance:r", "/grant:r",
            f"{username}:(OI)(CI)F", "SYSTEM:(OI)(CI)F",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _secure_directory(path: Path) -> None:
    for directory in (path.parents[1], path.parent, path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            directory.chmod(0o700)
        elif os.name == "nt":
            _apply_windows_acl(directory)


def launch_provider(
    playwright: Playwright,
    provider: Provider,
    browser: str,
    data_root: Path,
    *,
    headless: bool = False,
) -> BrowserContext:
    if provider.integration_mode == "disabled":
        raise ValueError(f"{provider.name} is disabled in the provider catalog")
    if browser not in provider.browser_support:
        raise ValueError(f"{provider.name} does not list {browser} as supported")
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError("Unsupported browser")

    user_data_dir = profile_path(data_root, provider.id, browser)
    _secure_directory(user_data_dir)
    engine = getattr(playwright, browser)
    context = engine.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=headless,
        args=["--no-first-run"] if browser == "chromium" else [],
    )
    try:
        context.set_default_timeout(15_000)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(provider.url, wait_until="domcontentloaded")
    except Exception:
        # A failed navigation must not strand a persistent context/profile lock.
        try:
            context.close()
        except Exception:
            pass
        raise
    return context
