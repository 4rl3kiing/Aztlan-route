from pathlib import Path
import pytest
from aztlan_route.browser import profile_path

def test_profiles_are_isolated_by_provider_and_browser(tmp_path: Path):
    paths = {profile_path(tmp_path, "gemini", "firefox"),
             profile_path(tmp_path, "gemini", "chromium"),
             profile_path(tmp_path, "claude", "firefox")}
    assert len(paths) == 3

@pytest.mark.parametrize("provider,browser", [
    ("../escape", "firefox"), ("provider", "webkit")])
def test_rejects_invalid_profile_components(tmp_path, provider, browser):
    with pytest.raises(ValueError):
        profile_path(tmp_path, provider, browser)
