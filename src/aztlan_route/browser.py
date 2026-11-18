"""Launch isolated, persistent provider browser profiles."""
from __future__ import annotations
import os
import re
from pathlib import Path
from playwright.sync_api import BrowserContext, Playwright
from .providers import Provider, SUPPORTED_BROWSERS

_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

def profile_path(root: Path, provider_id: str, browser: str) -> Path:
    if not _SAFE_ID.fullmatch(provider_id):
        raise ValueError("Invalid provider identifier")
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError("Unsupported browser")
    return root / provider_id / browser

def _secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)

def launch_provider(playwright: Playwright, provider: Provider, browser: str,
                    data_root: Path, *, headless: bool = False) -> BrowserContext:
    if browser not in provider.browser_support:
        raise ValueError(f"{provider.name} does not list {browser} as supported")
    if browser not in SUPPORTED_BROWSERS:
        raise ValueError("Unsupported browser")
    user_data_dir = profile_path(data_root, provider.id, browser)
    _secure_directory(user_data_dir)
    engine = getattr(playwright, browser)
    context = engine.launch_persistent_context(
        user_data_dir=str(user_data_dir), headless=headless,
        args=["--no-first-run"] if browser == "chromium" else [])
    context.set_default_timeout(15_000)
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(provider.url, wait_until="domcontentloaded")
    return context
