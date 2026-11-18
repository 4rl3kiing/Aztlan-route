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
    window = desktop.MainWindow.__new__(desktop.MainWindow)
    window._sessions = [(object(), object(), "qwen", "chromium")]
    assert window._profile_is_open("qwen", "chromium")
    assert not window._profile_is_open("qwen", "firefox")
    assert not window._profile_is_open("claude", "chromium")
