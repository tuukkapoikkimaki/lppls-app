"""Yhteiset käyttöliittymäpalat: kuvaajapaneeli PNG-tallennuksella."""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)


class ChartPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(9, 5.5), layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.default_name = "kuva.png"

        self.save_btn = QPushButton("Tallenna PNG")
        self.save_btn.clicked.connect(self.save_png)
        bar = QHBoxLayout()
        bar.addWidget(NavigationToolbar2QT(self.canvas, self))
        bar.addStretch()
        bar.addWidget(self.save_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.canvas, 1)

    def clear(self, message: str = ""):
        self.ax.clear()
        self.ax.set_axis_off()
        if message:
            self.ax.text(0.5, 0.5, message, ha="center", va="center", color="grey")
        self.canvas.draw_idle()

    def redraw(self, default_name: str):
        self.ax.set_axis_on()
        self.default_name = default_name
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
