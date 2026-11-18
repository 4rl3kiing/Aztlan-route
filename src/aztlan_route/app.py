"""Qt desktop application entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from platformdirs import user_data_dir
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from playwright.sync_api import Error as PlaywrightError, sync_playwright

from . import __version__
from .browser import launch_provider
from .providers import load_providers


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Aztlan-route {__version__}")
        self.resize(760, 520)
        self.data_root = Path(user_data_dir("Aztlan-route", "Aztlan"))
        catalog = Path(__file__).with_name("providers.json")
        self.providers = load_providers(catalog)
        self._sessions = []

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("Proveedores disponibles"))
        self.provider_list = QListWidget()
        for provider in self.providers:
            self.provider_list.addItem(
                f"{provider.name} — acceso manual en navegador (sin automatización)"
            )
        self.provider_list.setCurrentRow(0)
        layout.addWidget(self.provider_list)

        layout.addWidget(QLabel("Navegador"))
        self.browser_choice = QComboBox()
        self.browser_choice.addItem("Chromium", "chromium")
        self.browser_choice.addItem("Firefox", "firefox")
        layout.addWidget(self.browser_choice)

        self.launch_button = QPushButton("Abrir sesión del proveedor")
        self.launch_button.clicked.connect(self.open_provider)
        layout.addWidget(self.launch_button)
        layout.addWidget(QLabel(
            "La autenticación se realiza directamente en el sitio oficial. "
            "No se extraen contraseñas ni se automatiza la conversación."
        ))
        self.setCentralWidget(central)

    def open_provider(self) -> None:
        index = self.provider_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "Aztlan-route", "Selecciona un proveedor.")
            return

        provider = self.providers[index]
        browser = self.browser_choice.currentData()
        self.launch_button.setEnabled(False)
        driver = None
        try:
            driver = sync_playwright().start()
            context = launch_provider(
                driver, provider, browser, self.data_root / "profiles"
            )
            # Keep the driver alive for as long as its persistent context is open.
            self._sessions.append((driver, context))
        except (PlaywrightError, OSError, ValueError) as exc:
            if driver is not None:
                driver.stop()
            QMessageBox.critical(self, "No se pudo abrir el navegador", str(exc))
        finally:
            self.launch_button.setEnabled(True)

    def closeEvent(self, event) -> None:
        for driver, context in reversed(self._sessions):
            try:
                context.close()
            finally:
                driver.stop()
        self._sessions.clear()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
