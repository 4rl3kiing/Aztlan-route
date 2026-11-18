"""Qt desktop application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_data_dir
from PySide6.QtCore import QMetaObject, QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from playwright.sync_api import sync_playwright

from . import __version__
from .authentication import detect_authentication_challenge
from .browser import launch_provider
from .conversations import ConversationStore
from .providers import Provider, load_providers
from .sessions import SessionManager


class BrowserSessionWorker(QObject):
    """Owns Playwright and its browser context entirely on a dedicated Qt thread."""

    opened = Signal()
    failed = Signal(str)
    closed = Signal()
    authentication_state = Signal(str, str, str)

    def __init__(self, provider: Provider, browser: str, profile_root: Path) -> None:
        super().__init__()
        self.provider = provider
        self.browser = browser
        self.profile_root = profile_root
        self._driver = None
        self._context = None
        self._page = None
        self._auth_timer = None
        self._authentication_status = "awaiting_user"

    @Slot()
    def start(self) -> None:
        try:
            self._driver = sync_playwright().start()
            self._context = launch_provider(
                self._driver, self.provider, self.browser, self.profile_root
            )
            self._page = self._context.pages[0] if self._context.pages else None
            self._auth_timer = QTimer(self)
            self._auth_timer.setInterval(2000)
            self._auth_timer.timeout.connect(self._inspect_authentication_challenge)
            self._auth_timer.start()
            self.authentication_state.emit(self.provider.id, self.browser, self._authentication_status)
        except Exception as exc:
            try:
                self._stop_resources()
            except Exception:
                pass
            self.failed.emit(str(exc))
            return
        self.opened.emit()

    @Slot()
    def _inspect_authentication_challenge(self) -> None:
        """Detect common challenge indicators without reading page text or secrets."""
        if self._page is None:
            return
        try:
            url = self._page.url or ""
            title = self._page.title()
            challenge = detect_authentication_challenge(
                url=url,
                title=title,
                captcha_element_count=self._page.locator(
                    'iframe[src*="captcha" i], [id*="captcha" i], [class*="captcha" i]'
                ).count(),
                mfa_element_count=self._page.locator(
                    'input[autocomplete="one-time-code"], input[name*="otp" i], '
                    'input[name*="verification-code" i]'
                ).count(),
            )
        except Exception:
            # A transient navigation or closed page must not terminate the browser session.
            return
        if challenge and challenge != self._authentication_status:
            self._authentication_status = challenge
            self.authentication_state.emit(self.provider.id, self.browser, challenge)

    @Slot()
    def confirm_authenticated(self) -> None:
        """Record the operator's explicit confirmation; this is not API verification."""
        self._authentication_status = "authenticated_user_confirmed"
        self.authentication_state.emit(self.provider.id, self.browser, self._authentication_status)

    def _stop_resources(self) -> None:
        errors = []
        if self._auth_timer is not None:
            self._auth_timer.stop()
            self._auth_timer = None
        self._page = None
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
        self._sessions: list[tuple[QThread, BrowserSessionWorker, str, str]] = []
        self._auth_states: dict[str, str] = {}
        self._closing = False
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

        layout.addWidget(QLabel("Sesiones de navegador activas"))
        self.active_sessions = QListWidget()
        layout.addWidget(self.active_sessions)
        self.authentication_status_label = QLabel("Autenticación: sin sesión seleccionada")
        layout.addWidget(self.authentication_status_label)
        self.confirm_authentication_button = QPushButton("Confirmar que ya inicié sesión")
        self.confirm_authentication_button.setEnabled(False)
        self.confirm_authentication_button.clicked.connect(self.confirm_selected_authentication)
        layout.addWidget(self.confirm_authentication_button)

        self.close_session_button = QPushButton("Cerrar sesión seleccionada")
        self.close_session_button.setEnabled(False)
        self.close_session_button.clicked.connect(self.close_selected_session)
        self.active_sessions.currentRowChanged.connect(self._on_active_session_selected)
        layout.addWidget(self.close_session_button)
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

    @staticmethod
    def _session_key(provider_id: str, browser: str) -> str:
        return f"{provider_id}:{browser}"

    def _on_active_session_selected(self, row: int) -> None:
        valid = 0 <= row < len(self._sessions)
        self.close_session_button.setEnabled(valid)
        self.confirm_authentication_button.setEnabled(valid)
        if not valid:
            self.authentication_status_label.setText("Autenticación: sin sesión seleccionada")
            return
        _thread, _worker, provider_id, browser = self._sessions[row]
        state = self._auth_states.get(self._session_key(provider_id, browser), "awaiting_user")
        self.authentication_status_label.setText(
            f"Autenticación ({provider_id} · {browser}): {self._authentication_label(state)}"
        )

    @staticmethod
    def _authentication_label(state: str) -> str:
        labels = {
            "awaiting_user": "esperando autenticación manual",
            "captcha_required": "CAPTCHA detectado; requiere resolución manual",
            "mfa_required": "MFA detectado; requiere verificación manual",
            "authenticated_user_confirmed": "confirmada por el usuario (no verifica acceso API)",
        }
        return labels.get(state, "estado desconocido")

    @Slot(str, str, str)
    def _on_authentication_state(self, provider_id: str, browser: str, state: str) -> None:
        self._auth_states[self._session_key(provider_id, browser)] = state
        self.refresh_active_sessions()
        row = self.active_sessions.currentRow()
        if 0 <= row < len(self._sessions):
            self._on_active_session_selected(row)

    def refresh_active_sessions(self) -> None:
        selected = self.active_sessions.currentRow()
        self.active_sessions.clear()
        for _thread, _worker, provider_id, browser in self._sessions:
            state = self._auth_states.get(self._session_key(provider_id, browser), "awaiting_user")
            self.active_sessions.addItem(
                f"{provider_id} · {browser} — {self._authentication_label(state)}"
            )
        if self._sessions:
            self.active_sessions.setCurrentRow(min(max(selected, 0), len(self._sessions) - 1))

    def confirm_selected_authentication(self) -> None:
        index = self.active_sessions.currentRow()
        if index < 0 or index >= len(self._sessions):
            return
        _thread, worker, _provider_id, _browser = self._sessions[index]
        if worker.thread().isRunning():
            QMetaObject.invokeMethod(worker, "confirm_authenticated", Qt.ConnectionType.QueuedConnection)

    def _profile_is_open(self, provider_id: str, browser: str) -> bool:
        return any(
            current_provider == provider_id and current_browser == browser
            for _thread, _worker, current_provider, current_browser in self._sessions
        )

    def close_selected_session(self) -> None:
        index = self.active_sessions.currentRow()
        if index < 0 or index >= len(self._sessions):
            return
        thread, worker, _provider_id, _browser = self._sessions[index]
        try:
            if thread.isRunning():
                QMetaObject.invokeMethod(
                    worker, "close", Qt.ConnectionType.BlockingQueuedConnection
                )
                thread.quit()
                thread.wait()
        except Exception as exc:
            QMessageBox.warning(self, "Aztlan-route", f"No se pudo cerrar la sesión: {exc}")

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
        self.refresh_active_sessions()
        self.close_session_button.setEnabled(self.active_sessions.currentRow() >= 0)
        self.launch_button.setEnabled(bool(self._visible_providers))

    @Slot(str)
    def _show_browser_error(self, message: str) -> None:
        if not self._closing:
            QMessageBox.critical(self, "No se pudo abrir/cerrar el navegador", message)

    def open_provider(self) -> None:
        index = self.provider_list.currentRow()
        if index < 0 or index >= len(self._visible_providers):
            QMessageBox.warning(self, "Aztlan-route", "Selecciona un proveedor habilitado.")
            return

        provider = self._visible_providers[index]
        browser = self.browser_choice.currentData()
        if self._profile_is_open(provider.id, browser):
            QMessageBox.information(
                self, "Sesión existente",
                "Ese perfil ya está abierto. Cierra la sesión actual antes de volver a abrirlo."
            )
            return
        self.launch_button.setEnabled(False)
        thread = QThread(self)
        worker = BrowserSessionWorker(provider, browser, self.profile_root)
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        worker.opened.connect(self._on_session_opened)
        worker.authentication_state.connect(self._on_authentication_state)
        worker.failed.connect(self._show_browser_error)
        worker.failed.connect(thread.quit)
        worker.closed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        self._sessions.append((thread, worker, provider.id, browser))
        self.refresh_active_sessions()
        thread.start()

    def closeEvent(self, event) -> None:
        self._closing = True
        for thread, worker, _provider_id, _browser in reversed(self._sessions[:]):
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
