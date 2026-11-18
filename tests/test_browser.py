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


def test_launch_closes_context_when_navigation_fails(tmp_path):
    from aztlan_route.browser import launch_provider
    from aztlan_route.providers import Provider

    class Page:
        def goto(self, *_args, **_kwargs):
            raise RuntimeError("navigation failed")

    class Context:
        pages = [Page()]
        closed = False

        def set_default_timeout(self, _timeout):
            pass

        def close(self):
            self.closed = True

    context = Context()

    class Engine:
        def launch_persistent_context(self, **_kwargs):
            return context

    class Playwright:
        chromium = Engine()

    provider = Provider(
        "test", "Test", "https://example.com", ("chromium",),
        "manual_browser", False, "test",
    )
    with pytest.raises(RuntimeError, match="navigation failed"):
        launch_provider(Playwright(), provider, "chromium", tmp_path)
    assert context.closed
