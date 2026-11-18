"""Qt desktop application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_data_dir
from PySide6.QtCore import QMetaObject, QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from playwright.sync_api import Error as PlaywrightError, sync_playwright

from . import __version__
from .browser import launch_provider
from .conversations import ConversationStore
from .providers import Provider, load_providers
from .sessions import SessionManager


class BrowserSessionWorker(QObject):
    """Owns Playwright and its browser context entirely on a dedicated Qt thread."""

    opened = Signal()
    failed = Signal(str)
    closed = Signal()

    def __init__(self, provider: Provider, browser: str, profile_root: Path) -> None:
        super().__init__()
        self.provider = provider
        self.browser = browser
        self.profile_root = profile_root
        self._driver = None
        self._context = None

    @Slot()
    def start(self) -> None:
        try:
            self._driver = sync_playwright().start()
            self._context = launch_provider(
                self._driver, self.provider, self.browser, self.profile_root
            )
        except (PlaywrightError, OSError, ValueError, RuntimeError) as exc:
            try:
                self._stop_resources()
            except Exception:
                pass
            self.failed.emit(str(exc))
            return
        self.opened.emit()

    def _stop_resources(self) -> None:
        errors = []
        if self._context is not None:
            try:
                self._context.close()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._context = None
        if self._driver is not None:
            try:
                self._driver.stop()
            except Exception as exc:
                errors.append(exc)
            finally:
                self._driver = None
        if errors:
            raise RuntimeError("; ".join(str(error) for error in errors))

    @Slot()
    def close(self) -> None:
        try:
            self._stop_resources()
        except Exception as exc:
            self.failed.emit(f"Error cerrando sesión: {exc}")
        finally:
            self.closed.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Aztlan-route {__version__}")
        self.resize(800, 640)
        self.data_root = Path(user_data_dir("Aztlan-route", "Aztlan"))
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.profile_root = self.data_root / "profiles"
        catalog = Path(__file__).with_name("providers.json")
        self.providers = load_providers(catalog)
        self._sessions: list[tuple[QThread, BrowserSessionWorker]] = []
        self.conversations = ConversationStore(self.data_root / "conversations.sqlite3")
        self.session_manager = SessionManager(self.profile_root)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("Proveedores disponibles"))
        self.provider_list = QListWidget()
        self._visible_providers = [
            provider for provider in self.providers if provider.integration_mode != "disabled"
        ]
        for provider in self._visible_providers:
            mode = (
                "Navegación manual"
                if provider.integration_mode == "manual_browser"
                else provider.integration_mode
            )
            self.provider_list.addItem(f"{provider.name} — {mode}")
        if self._visible_providers:
            self.provider_list.setCurrentRow(0)
        else:
            self.provider_list.addItem("No hay proveedores habilitados.")
        layout.addWidget(self.provider_list)

        layout.addWidget(QLabel("Navegador"))
        self.browser_choice = QComboBox()
        self.browser_choice.addItem("Chromium", "chromium")
        self.browser_choice.addItem("Firefox", "firefox")
        layout.addWidget(self.browser_choice)

        self.launch_button = QPushButton("Abrir sesión del proveedor")
        self.launch_button.setEnabled(bool(self._visible_providers))
        self.launch_button.clicked.connect(self.open_provider)
        layout.addWidget(self.launch_button)

        layout.addWidget(QLabel("Perfiles locales detectados"))
        self.profile_list = QListWidget()
        layout.addWidget(self.profile_list)
        self.refresh_button = QPushButton("Actualizar perfiles")
        self.refresh_button.clicked.connect(self.refresh_profiles)
        layout.addWidget(self.refresh_button)
        self.refresh_profiles()

        layout.addWidget(QLabel(
            "La autenticación se realiza directamente en el sitio oficial. "
            "Los perfiles se mantienen separados. No se extraen contraseñas "
            "ni se automatiza la conversación en proveedores no autorizados."
        ))
        self.setCentralWidget(central)

    @Slot()
    def _on_session_opened(self) -> None:
        self.refresh_profiles()
        self.launch_button.setEnabled(bool(self._visible_providers))

    def refresh_profiles(self) -> None:
        self.profile_list.clear()
        profiles = self.session_manager.list_profiles()
        for profile in profiles:
            self.profile_list.addItem(f"{profile.provider_id} · {profile.browser}")
        if not profiles:
            self.profile_list.addItem("No hay perfiles creados todavía.")

    @Slot()
    def _on_thread_finished(self) -> None:
        thread = self.sender()
        if not isinstance(thread, QThread):
            return
        self._sessions = [item for item in self._sessions if item[0] is not thread]
        thread.deleteLater()
        self.launch_button.setEnabled(bool(self._visible_providers))

    @Slot(str)
    def _show_browser_error(self, message: str) -> None:
        QMessageBox.critical(self, "No se pudo abrir/cerrar el navegador", message)

    def open_provider(self) -> None:
        index = self.provider_list.currentRow()
        if index < 0 or index >= len(self._visible_providers):
            QMessageBox.warning(self, "Aztlan-route", "Selecciona un proveedor habilitado.")
            return

        provider = self._visible_providers[index]
        browser = self.browser_choice.currentData()
        self.launch_button.setEnabled(False)
        thread = QThread(self)
        worker = BrowserSessionWorker(provider, browser, self.profile_root)
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.opened.connect(self._on_session_opened)
        worker.failed.connect(self._show_browser_error)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._sessions.append((thread, worker))
        thread.start()

    def closeEvent(self, event) -> None:
        for thread, worker in reversed(self._sessions[:]):
            try:
                if thread.isRunning():
                    QMetaObject.invokeMethod(
                        worker, "close", Qt.ConnectionType.BlockingQueuedConnection
                    )
            except Exception:
                # A failed session must not prevent the remaining sessions from closing.
                pass
            finally:
                if thread.isRunning():
                    thread.quit()
                    thread.wait()
        self._sessions.clear()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
