from aztlan_route import app as desktop
from aztlan_route.providers import Provider


def test_main_window_handles_empty_provider_catalog(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "user_data_dir", lambda *args: str(tmp_path))
    monkeypatch.setattr(desktop, "load_providers", lambda _path: [])
    window = desktop.MainWindow()
    qtbot.addWidget(window)
    assert window.provider_list.count() == 1
    assert not window.launch_button.isEnabled()
    assert "No hay proveedores" in window.provider_list.item(0).text()


def test_main_window_hides_disabled_providers(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "user_data_dir", lambda *args: str(tmp_path))
    disabled = Provider(
        "offline", "Offline", "https://example.com", ("chromium",),
        "disabled", False, "disabled for test",
    )
    enabled = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )
    monkeypatch.setattr(desktop, "load_providers", lambda _path: [disabled, enabled])
    window = desktop.MainWindow()
    qtbot.addWidget(window)
    assert window.provider_list.count() == 1
    assert window.provider_list.item(0).text().startswith("Manual")
    assert window.launch_button.isEnabled()


def test_worker_closes_driver_even_if_context_close_fails(tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )
    worker = BrowserSessionWorker(provider, "chromium", tmp_path)

    class BrokenContext:
        def close(self):
            raise RuntimeError("context close failed")

    class Driver:
        stopped = False

        def stop(self):
            self.stopped = True

    driver = Driver()
    worker._context = BrokenContext()
    worker._driver = driver

    import pytest

    with pytest.raises(RuntimeError, match="context close failed"):
        worker._stop_resources()
    assert driver.stopped
    assert worker._context is None
    assert worker._driver is None


def test_main_window_initializes_session_controls(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "user_data_dir", lambda *args: str(tmp_path))
    monkeypatch.setattr(desktop, "load_providers", lambda _path: [])
    window = desktop.MainWindow()
    qtbot.addWidget(window)
    assert window.active_sessions.count() == 0
    assert not window.close_session_button.isEnabled()


def test_duplicate_profile_detection():
    state = type("SessionState", (), {
        "_sessions": [(object(), object(), "qwen", "chromium")]
    })()
    assert desktop.MainWindow._profile_is_open(state, "qwen", "chromium")
    assert not desktop.MainWindow._profile_is_open(state, "qwen", "firefox")
    assert not desktop.MainWindow._profile_is_open(state, "claude", "chromium")


def test_browser_worker_start_and_close_releases_all_resources(monkeypatch, tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )

    class Context:
        closed = False

        def close(self):
            self.closed = True

    class Driver:
        stopped = False

        def stop(self):
            self.stopped = True

    context = Context()
    driver = Driver()

    class PlaywrightStarter:
        def start(self):
            return driver

    monkeypatch.setattr(desktop, "sync_playwright", lambda: PlaywrightStarter())
    monkeypatch.setattr(desktop, "launch_provider", lambda *_args: context)

    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    worker.start()
    assert worker._context is context
    assert worker._driver is driver
    worker.close()
    assert context.closed
    assert driver.stopped
    assert worker._context is None
    assert worker._driver is None


def test_browser_worker_releases_driver_when_launch_fails(monkeypatch, tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )

    class Driver:
        stopped = False

        def stop(self):
            self.stopped = True

    driver = Driver()

    class PlaywrightStarter:
        def start(self):
            return driver

    monkeypatch.setattr(desktop, "sync_playwright", lambda: PlaywrightStarter())

    def fail_launch(*_args):
        raise RuntimeError("browser launch failed")

    monkeypatch.setattr(desktop, "launch_provider", fail_launch)
    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    worker.start()
    assert driver.stopped
    assert worker._driver is None



def test_worker_confirmation_emits_explicit_user_confirmed_state(tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )
    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    received = []
    worker.authentication_state.connect(lambda *args: received.append(args))

    worker.confirm_authenticated()

    assert received == [("manual", "chromium", "authenticated_user_confirmed")]



def test_worker_reauthentication_reuses_existing_context(tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )

    class Page:
        brought_to_front = False

        def bring_to_front(self):
            self.brought_to_front = True

    class Context:
        pages = [Page()]

    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    worker._context = Context()
    received = []
    worker.authentication_state.connect(lambda *args: received.append(args))

    worker.request_reauthentication()

    assert worker._page is worker._context.pages[0]
    assert worker._page.brought_to_front
    assert received == [("manual", "chromium", "awaiting_user")]


def test_worker_reauthentication_reopens_closed_tab(tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )

    class Page:
        url = "about:blank"
        navigated = None

        def goto(self, url, **_kwargs):
            self.navigated = url

    class Context:
        pages = []

        def new_page(self):
            page = Page()
            self.pages.append(page)
            return page

    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    worker._context = Context()
    worker.request_reauthentication()

    assert worker._page is worker._context.pages[0]
    assert worker._page.navigated == provider.url



def test_worker_marks_closed_browser_context_for_recovery(tmp_path):
    from aztlan_route.app import BrowserSessionWorker

    provider = Provider(
        "manual", "Manual", "https://example.org", ("chromium",),
        "manual_browser", False, "manual for test",
    )
    worker = BrowserSessionWorker(provider, "chromium", tmp_path)
    received = []
    worker.authentication_state.connect(lambda *args: received.append(args))

    worker._on_context_closed()

    assert worker._context_closed
    assert received == [("manual", "chromium", "browser_session_closed")]
