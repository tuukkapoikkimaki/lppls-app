"""Yhteiset käyttöliittymäpalat: kuvaajapaneeli, periodin valitsin ja rullazoomaus."""
from __future__ import annotations

from typing import Callable

import matplotlib.dates as mdates
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.collections import PathCollection
from matplotlib.figure import Figure
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

Page = tuple[str, Callable[[Axes], None]]  # (nimi, piirtofunktio)

ZOOM_STEP = 0.8  # yksi rullan pykälä eteen: näkymä 80 %:iin


class PagedToolbar(NavigationToolbar2QT):
    """Työkalurivi: koti palauttaa koko kuvan ja ← / → vaihtavat näkymää.

    Matplotlibin oma laatikkozoomaus ja panorointi on poistettu; zoomaus tehdään
    hiiren rullalla (ks. ChartPanel) ja periodi valitaan kuvan alla olevalla valitsimella.
    """

    toolitems = [t for t in NavigationToolbar2QT.toolitems if t[0] in ("Home", "Back", "Forward")]

    def __init__(self, canvas, panel: "ChartPanel"):
        self.panel = panel
        super().__init__(canvas, panel)

    def home(self, *args):
        self.panel.reset_view()

    def back(self, *args):
        if self.panel.page > 0:
            self.panel.show_page(self.panel.page - 1)

    def forward(self, *args):
        if self.panel.page < len(self.panel.pages) - 1:
            self.panel.show_page(self.panel.page + 1)

    def set_history_buttons(self):
        panel = getattr(self, "panel", None)
        if panel is None:
            return
        if "back" in self._actions:
            self._actions["back"].setEnabled(panel.page > 0)
        if "forward" in self._actions:
            self._actions["forward"].setEnabled(panel.page < len(panel.pages) - 1)


class RangeSlider(QWidget):
    """Viivamainen valitsin, jossa on kaksi kahvaa: periodin alku ja loppu.

    Arvot ovat osuuksia 0…1 koko aikavälistä. Kahvoja vedetään hiirellä, ja kahvojen
    välistä janaa vetämällä koko valittu periodi liukuu.
    """

    changed = Signal(float, float)
    R = 7  # kahvan säde

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lo, self.hi = 0.0, 1.0
        self._drag: str | None = None
        self._grab = 0.0
        self.setMinimumHeight(2 * self.R + 8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Vedä kahvoista periodin alkua ja loppua, tai keskeltä koko periodia")

    def set_range(self, lo: float, hi: float, emit: bool = False):
        lo, hi = max(0.0, min(lo, 1.0)), max(0.0, min(hi, 1.0))
        self.lo, self.hi = min(lo, hi), max(lo, hi)
        self.update()
        if emit:
            self.changed.emit(self.lo, self.hi)

    def _x(self, v: float) -> float:
        return self.R + v * (self.width() - 2 * self.R)

    def _v(self, x: float) -> float:
        return (x - self.R) / max(1, self.width() - 2 * self.R)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        y = self.height() / 2
        p.setPen(QPen(QColor("#c8ccd4"), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(self._x(0), y), QPointF(self._x(1), y))
        p.setPen(QPen(QColor("#1f77b4"), 4, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(self._x(self.lo), y), QPointF(self._x(self.hi), y))
        p.setPen(QPen(QColor("#1f4e79"), 1.5))
        p.setBrush(QColor("white"))
        for v in (self.lo, self.hi):
            p.drawEllipse(QRectF(self._x(v) - self.R, y - self.R, 2 * self.R, 2 * self.R))

    def mousePressEvent(self, e):
        x = e.position().x()
        d_lo, d_hi = abs(x - self._x(self.lo)), abs(x - self._x(self.hi))
        if min(d_lo, d_hi) <= self.R + 3:
            self._drag = "lo" if d_lo < d_hi or (d_lo == d_hi and x < self._x(self.lo)) else "hi"
        elif self._x(self.lo) < x < self._x(self.hi):
            self._drag, self._grab = "move", self._v(x) - self.lo
        else:  # klikkaus janan ulkopuolelle siirtää lähimmän kahvan
            self._drag = "lo" if d_lo < d_hi else "hi"
            self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        v = min(1.0, max(0.0, self._v(e.position().x())))
        gap = 0.01
        if self._drag == "lo":
            self.lo = min(v, self.hi - gap)
        elif self._drag == "hi":
            self.hi = max(v, self.lo + gap)
        else:
            width = self.hi - self.lo
            self.lo = min(max(0.0, v - self._grab), 1.0 - width)
            self.hi = self.lo + width
        self.update()
        self.changed.emit(self.lo, self.hi)

    def mouseReleaseEvent(self, _):
        self._drag = None


def _visible_y(ax: Axes, x0: float, x1: float) -> np.ndarray:
    """Data-akselille piirrettyjen pisteiden ja viivojen y-arvot välillä x0…x1."""
    ys = []
    for c in ax.collections:
        if isinstance(c, PathCollection) and c.get_offset_transform() == ax.transData:
            xy = np.asarray(c.get_offsets(), dtype=float)
            if xy.size:
                ys.append(xy[(xy[:, 0] >= x0) & (xy[:, 0] <= x1), 1])
    for line in ax.lines:
        if line.get_transform() == ax.transData:  # axvline yms. ohitetaan
            xy = np.asarray(line.get_xydata(), dtype=float)
            if xy.size:
                ys.append(xy[(xy[:, 0] >= x0) & (xy[:, 0] <= x1), 1])
    ys = np.concatenate(ys) if ys else np.array([])
    return ys[np.isfinite(ys)]


class ChartPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(9, 5.5), layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.default_name = "kuva.png"
        self.pages: list[Page] = []
        self.page = 0
        self.home: tuple[tuple[float, float], tuple[float, float]] | None = None
        self.zooming = False

        self.toolbar = PagedToolbar(self.canvas, self)
        self.page_label = QLabel()
        self.zoom_label = QLabel()
        self.save_btn = QPushButton("Tallenna PNG")
        self.save_btn.clicked.connect(self.save_png)
        bar = QHBoxLayout()
        bar.addWidget(self.toolbar)
        bar.addWidget(self.page_label)
        bar.addStretch()
        bar.addWidget(self.zoom_label)
        bar.addWidget(self.save_btn)

        # Periodin valitsin kuvan alla: alku- ja loppupäivä kahvojen vieressä
        self.slider = RangeSlider()
        self.slider.changed.connect(self._on_slider)
        self.start_label, self.end_label = QLabel(), QLabel()
        for lab in (self.start_label, self.end_label):
            lab.setMinimumWidth(80)
        self.end_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        period = QHBoxLayout()
        period.addWidget(QLabel("Periodi:"))
        period.addWidget(self.start_label)
        period.addWidget(self.slider, 1)
        period.addWidget(self.end_label)
        self.period_box = QWidget()
        self.period_box.setLayout(period)
        period.setContentsMargins(6, 0, 6, 2)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.canvas, 1)
        lay.addWidget(self.period_box)

        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self._set_zooming(False)
        self.period_box.setEnabled(False)

    # --- piirto ---
    def clear(self, message: str = ""):
        self.pages = []
        self.home = None
        self.page_label.clear()
        for other in list(self.figure.axes):  # oikea asteikko (twinx) pois
            if other is not self.ax:
                other.remove()
        self.ax.clear()
        self.ax.set_axis_off()
        if message:
            self.ax.text(0.5, 0.5, message, ha="center", va="center", color="grey")
        self.period_box.setEnabled(False)
        self.start_label.clear()
        self.end_label.clear()
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
        self.home = (self.ax.get_xlim(), self.ax.get_ylim())
        self.period_box.setEnabled(True)
        self.slider.set_range(0.0, 1.0)
        self._update_period_labels()
        self.toolbar.update()
        self.canvas.draw_idle()

    def reset_view(self):
        """Koko kuva: alkuperäinen aikaväli ja y-asteikko."""
        if self.home is None:
            return
        self.ax.set_xlim(self.home[0])
        self.ax.set_ylim(self.home[1])
        self.slider.set_range(0.0, 1.0)
        self._update_period_labels()
        self.canvas.draw_idle()

    # --- periodi ---
    def _on_slider(self, lo: float, hi: float):
        if self.home is None:
            return
        h0, h1 = self.home[0]
        self.set_period(h0 + lo * (h1 - h0), h0 + hi * (h1 - h0), from_slider=True)

    def set_period(self, x0: float, x1: float, from_slider: bool = False):
        """Näyttää aikavälin x0…x1 (matplotlibin päivälukuina) ja sovittaa y-asteikon siihen."""
        h0, h1 = self.home[0]
        x0, x1 = max(x0, h0), min(x1, h1)
        if x1 - x0 < 1:  # vähintään päivä
            return
        self.ax.set_xlim(x0, x1)
        ys = _visible_y(self.ax, x0, x1)
        if ys.size:
            lo, hi = float(ys.min()), float(ys.max())
            pad = 0.06 * (hi - lo) if hi > lo else max(abs(hi) * 0.05, 0.1)
            self.ax.set_ylim(lo - pad, hi + pad)
        if not from_slider:
            self.slider.set_range((x0 - h0) / (h1 - h0), (x1 - h0) / (h1 - h0))
        self._update_period_labels()
        self.canvas.draw_idle()

    def _update_period_labels(self):
        x0, x1 = self.ax.get_xlim()
        for lab, x in ((self.start_label, x0), (self.end_label, x1)):
            lab.setText(f"{mdates.num2date(x):%Y-%m-%d}")

    # --- rullazoomaus ---
    def _set_zooming(self, on: bool):
        self.zooming = on
        self.canvas.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)
        self.zoom_label.setText("🔍 Zoomaus päällä: rulla eteen/taakse, rullan painallus lopettaa"
                                if on else "Zoomaus: paina hiiren rullaa")
        self.zoom_label.setStyleSheet("color: #b5520b; font-weight: bold;" if on else "color: grey;")

    def _on_press(self, event):
        if event.button == 2 and self.home is not None:  # keskinäppäin = rullan painallus
            self._set_zooming(not self.zooming)

    def _on_scroll(self, event):
        if not self.zooming or self.home is None or event.xdata is None:
            return
        # Kursorin kohta pysyy paikallaan; eteen = lähemmäs, taakse = kauemmas.
        # Kursori voi olla oikean asteikon (twinx) päällä, joten x muunnetaan pääakselille.
        x = self.ax.transData.inverted().transform((event.x, event.y))[0]
        scale = ZOOM_STEP if event.button == "up" else 1.0 / ZOOM_STEP
        x0, x1 = self.ax.get_xlim()
        new0, new1 = x - (x - x0) * scale, x + (x1 - x) * scale
        h0, h1 = self.home[0]
        if new1 - new0 >= h1 - h0:
            self.reset_view()
            return
        # Pidetään näkymä koko aikavälin sisällä
        if new0 < h0:
            new0, new1 = h0, h0 + (new1 - new0)
        if new1 > h1:
            new0, new1 = h1 - (new1 - new0), h1
        self.set_period(new0, new1)

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
