"""Yhteiset käyttöliittymäpalat: kuvaajapaneeli PNG-tallennuksella."""
from __future__ import annotations

from typing import Callable

from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

Page = tuple[str, Callable[[Axes], None]]  # (nimi, piirtofunktio)


class PagedToolbar(NavigationToolbar2QT):
    """Työkalurivi, jonka ← / → -nuolet selaavat zoomaushistorian lisäksi näkymiä.

    Kun zoomaushistoriassa ei pääse pidemmälle, nuoli vaihtaa edelliseen tai
    seuraavaan näkymään (esim. log-hinta → hinta ilman logaritmia).
    """

    def __init__(self, canvas, panel: "ChartPanel"):
        self.panel = panel
        super().__init__(canvas, panel)

    def _can_nav(self) -> tuple[bool, bool]:
        stack = self._nav_stack
        return stack._pos > 0, stack._pos < len(stack) - 1

    def back(self, *args):
        if self._can_nav()[0]:
            super().back()
        elif self.panel.page > 0:
            self.panel.show_page(self.panel.page - 1)

    def forward(self, *args):
        if self._can_nav()[1]:
            super().forward()
        elif self.panel.page < len(self.panel.pages) - 1:
            self.panel.show_page(self.panel.page + 1)

    def set_history_buttons(self):
        can_back, can_fwd = self._can_nav()
        panel = getattr(self, "panel", None)
        if panel is not None:
            can_back |= panel.page > 0
            can_fwd |= panel.page < len(panel.pages) - 1
        if "back" in self._actions:
            self._actions["back"].setEnabled(can_back)
        if "forward" in self._actions:
            self._actions["forward"].setEnabled(can_fwd)


class ChartPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(9, 5.5), layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.default_name = "kuva.png"
        self.pages: list[Page] = []
        self.page = 0

        self.toolbar = PagedToolbar(self.canvas, self)
        self.page_label = QLabel()
        self.save_btn = QPushButton("Tallenna PNG")
        self.save_btn.clicked.connect(self.save_png)
        bar = QHBoxLayout()
        bar.addWidget(self.toolbar)
        bar.addWidget(self.page_label)
        bar.addStretch()
        bar.addWidget(self.save_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.canvas, 1)

    def clear(self, message: str = ""):
        self.pages = []
        self.page_label.clear()
        for other in list(self.figure.axes):  # oikea asteikko (twinx) pois
            if other is not self.ax:
                other.remove()
        self.ax.clear()
        self.ax.set_axis_off()
        if message:
            self.ax.text(0.5, 0.5, message, ha="center", va="center", color="grey")
        self.toolbar.update()
        self.canvas.draw_idle()

    def redraw(self, default_name: str):
        self.ax.set_axis_on()
        self.default_name = default_name
        self.toolbar.update()
        self.canvas.draw_idle()

    def set_pages(self, pages: list[Page], default_name: str, page: int = 0):
        """Useampi näkymä samasta kohteesta; nuolet ← / → vaihtavat näkymää."""
        self.pages = pages
        self.default_name = default_name
        self.show_page(min(page, len(pages) - 1))

    def show_page(self, index: int):
        self.page = index
        name, draw = self.pages[index]
        draw(self.ax)
        self.ax.set_axis_on()
        self.page_label.setText(f"Näkymä {index + 1}/{len(self.pages)}: {name}  (← / →)")
        self.toolbar.update()  # tyhjentää zoomaushistorian ja päivittää nuolet
        self.canvas.draw_idle()

    def save_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Tallenna kuva", self.default_name,
                                              "PNG-kuva (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            self.figure.savefig(path, dpi=150)
        except OSError as e:
            QMessageBox.warning(self, "Tallennus epäonnistui", str(e))
