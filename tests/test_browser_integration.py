"""Real browser smoke tests; CI installs both engines before running this module."""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.parametrize("browser_name", ["chromium", "firefox"])
def test_real_browser_persistent_context_smoke(tmp_path: Path, browser_name: str):
    with sync_playwright() as playwright:
        browser_type = getattr(playwright, browser_name)
        if not Path(browser_type.executable_path).is_file():
            pytest.skip(f"{browser_name} binary is not installed in this test environment")
        profile = tmp_path / browser_name
        context = browser_type.launch_persistent_context(
            user_data_dir=str(profile),
            headless=True,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.set_content("<html><head><title>Aztlan smoke</title></head><body>ok</body></html>")
            assert page.title() == "Aztlan smoke"
            assert profile.is_dir()
        finally:
            context.close()
