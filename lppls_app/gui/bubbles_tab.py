"""Tallennetut kuplat -välilehti: ennuste vs. toteuma, sarjojen päivitys."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel,
                               QMessageBox, QProgressBar, QPushButton, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..config import Config
from ..plot import draw_tracked
from ..storage import Storage
from ..tracker import HIT, MISS, PENDING
from .common import ChartPanel
from .workers import UpdateWorker

COLUMNS = ["#", "Tunnus", "Havaittu", "Muutos 2 v", "Ennustettu tc", "tc-väli", "Todellinen käänne",
           "Ero (pv)", "Muutos", "Tila", "Laji", "Seuranta", "Päivitetty"]
STATUS_COLOR = {HIT: QColor(210, 240, 210), MISS: QColor(240, 215, 215),
                PENDING: QColor(255, 245, 205)}


class BubblesTab(QWidget):
    status_message = Signal(str)

    def __init__(self, storage: Storage, cfg: Config, parent=None):
        super().__init__(parent)
        self.storage, self.cfg = storage, cfg
        self.worker: UpdateWorker | None = None
        self._build()
        self.reload()

    def _build(self):
        self.kind_filter = QComboBox()
        self.kind_filter.addItems(["Kaikki", "Oikeat", "Testit"])
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Kaikki tilat", PENDING, HIT, MISS])
        self.ticker_filter = QComboBox()
        for w in (self.kind_filter, self.status_filter, self.ticker_filter):
            w.currentIndexChanged.connect(self.reload)

        self.update_btn = QPushButton("Päivitä sarjat")
        self.update_btn.clicked.connect(self.update_series)
        self.stop_track_btn = QPushButton("Lopeta seuranta")
        self.stop_track_btn.clicked.connect(self.toggle_tracking)
        self.delete_btn = QPushButton("Poista")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(160)
        self.progress.hide()

        top = QHBoxLayout()
        for label, w in (("Laji:", self.kind_filter), ("Tila:", self.status_filter),
                         ("Tunnus:", self.ticker_filter)):
            top.addWidget(QLabel(label))
            top.addWidget(w)
        top.addStretch()
        top.addWidget(self.progress)
        top.addWidget(self.update_btn)
        top.addWidget(self.stop_track_btn)
        top.addWidget(self.delete_btn)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.show_selected)
        self.chart = ChartPanel()

        split = QSplitter(Qt.Vertical)
        split.addWidget(self.table)
        split.addWidget(self.chart)
        split.setSizes([220, 500])
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(split, 1)

    # --- lista ---
    def _filtered(self):
        kind = self.kind_filter.currentIndex()
        status = self.status_filter.currentText()
        ticker = self.ticker_filter.currentText()
        for b in self.storage.list_bubbles():
            if kind == 1 and b["is_test"] or kind == 2 and not b["is_test"]:
                continue
            if status != "Kaikki tilat" and b["status"] != status:
                continue
            if ticker not in ("", "Kaikki tunnukset") and b["ticker"] != ticker:
                continue
            yield b

    def _refresh_ticker_filter(self):
        current = self.ticker_filter.currentText()
        tickers = sorted({b["ticker"] for b in self.storage.list_bubbles()})
        self.ticker_filter.blockSignals(True)
        self.ticker_filter.clear()
        self.ticker_filter.addItems(["Kaikki tunnukset", *tickers])
        if current in tickers:
            self.ticker_filter.setCurrentText(current)
        self.ticker_filter.blockSignals(False)

    def reload(self):
        selected = self.selected_id()
        self._refresh_ticker_filter()
        self.table.setRowCount(0)
        for b in self._filtered():
            row = self.table.rowCount()
            self.table.insertRow(row)
            tc = pd.Timestamp(b["tc"])
            peak = pd.Timestamp(b["actual_peak_date"]) if b["actual_peak_date"] else None
            move = b["max_drawdown"]
            values = [
                str(b["id"]), b["ticker"], b["detected_as_of"],
                f"{b['move']:+.0%}" if b["move"] is not None else "–", b["tc"],
                f"{b['tc_p10']} … {b['tc_p90']}",
                f"{peak:%Y-%m-%d}" if peak is not None else "–",
                str((peak - tc).days) if peak is not None else "–",
                ("−" if b["sign"] != "neg" else "+") + f"{move:.0%}" if move is not None else "–",
                b["status"],
                ("kupla" if b["sign"] != "neg" else "antikupla") + (" (testi)" if b["is_test"] else ""),
                "kyllä" if b["tracking"] else "ei",
                (b["last_updated"] or "")[:16].replace("T", " "),
            ]
            for col, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setData(Qt.UserRole, b["id"])
                if b["status"] in STATUS_COLOR:
                    item.setBackground(STATUS_COLOR[b["status"]])
                self.table.setItem(row, col, item)
            if b["id"] == selected:
                self.table.selectRow(row)
        if self.table.rowCount() == 0:
            self.chart.clear("Ei tallennettuja kuplia. Havaitut kuplat tallentuvat tänne automaattisesti.")
        elif self.selected_id() is None:
            self.table.selectRow(0)

    def selected_id(self) -> int | None:
        items = self.table.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def show_selected(self):
        bubble_id = self.selected_id()
        b = self.storage.get_bubble(bubble_id) if bubble_id is not None else None
        if b is None:
            return
        snap = self.storage.bubble_prices(b["id"])
        follow = self.storage.tracked_prices(b["ticker"], after=b["detected_as_of"])
        draw_tracked(self.chart.ax, b, snap, follow)
        safe = b["ticker"].replace("^", "").replace("=", "")
        self.chart.redraw(f"{safe}_tc-{b['tc']}.png")
        self.stop_track_btn.setText("Lopeta seuranta" if b["tracking"] else "Jatka seurantaa")

    # --- toiminnot ---
    def update_series(self):
        self.update_btn.setEnabled(False)
        self.progress.setValue(0)
        self.progress.show()
        self.worker = UpdateWorker(self.cfg, self.storage.path)
        self.worker.progress.connect(lambda d, t: (self.progress.setMaximum(t), self.progress.setValue(d)))
        self.worker.done.connect(self.on_updated)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _worker_finished(self):
        self.worker = None

    def on_updated(self, text: str):
        self.update_btn.setEnabled(True)
        self.progress.hide()
        self.status_message.emit(text)
        self.reload()
        self.show_selected()

    def toggle_tracking(self):
        b = self.storage.get_bubble(self.selected_id() or -1)
        if b is not None:
            self.storage.set_tracking(b["id"], not b["tracking"])
            self.reload()

    def delete_selected(self):
        bubble_id = self.selected_id()
        if bubble_id is None:
            return
        if QMessageBox.question(self, "Poista kupla", f"Poistetaanko kupla #{bubble_id}?") \
                == QMessageBox.Yes:
            self.storage.delete_bubble(bubble_id)
            self.table.clearSelection()
            self.reload()
