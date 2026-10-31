"""Pääikkuna: välilehdet Skanneri ja Tallennetut kuplat."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from ..config import Config, default_db_path
from ..storage import Storage
from .bubbles_tab import BubblesTab
from .scanner_tab import ScannerTab


class MainWindow(QMainWindow):
    def __init__(self, storage: Storage, cfg: Config):
        super().__init__()
        self.setWindowTitle("LPPLS-kuplaskanneri")
        self.resize(1280, 820)
        self.scanner = ScannerTab(storage, cfg)
        self.bubbles = BubblesTab(storage, cfg)
        tabs = QTabWidget()
        tabs.addTab(self.scanner, "Skanneri")
        tabs.addTab(self.bubbles, "Tallennetut kuplat")
        self.setCentralWidget(tabs)

        self.scanner.bubbles_changed.connect(self.bubbles.reload)
        for tab in (self.scanner, self.bubbles):
            tab.status_message.connect(lambda m: self.statusBar().showMessage(m, 15000))
        self.statusBar().showMessage(
            f"Tietokanta: {storage.path} · Tutkimuskäyttöön, ei sijoitussuositus")

    def closeEvent(self, event):
        for worker in (self.scanner.worker, self.bubbles.worker):
            if worker is not None:
                worker.requestInterruption()
                worker.wait(30000)
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LPPLS-kuplaskanneri")
    storage = Storage(default_db_path())
    win = MainWindow(storage, Config())
    win.show()
    code = app.exec()
    storage.close()
    return code
