"""Skanneri-välilehti: seurantalista, skannaus ja tulokset."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..config import TEST_PRESETS, Config
from ..plot import draw_scan
from ..storage import Storage
from .common import ChartPanel
from .workers import ScanWorker

STATUS_LABEL = {"kupla": "🔴 kupla", "lähellä": "🟡 lähellä", "ei": "⚪ ei"}
STATUS_COLOR = {"kupla": QColor(255, 220, 220), "lähellä": QColor(255, 245, 205)}
COLUMNS = ["Tunnus", "Conf +", "Conf −", "Mediaani-tc", "tc-väli (10–90 %)", "Päiviä tc:hen", "Tila"]


def _d(ts) -> str:
    return "–" if ts is None else f"{ts:%Y-%m-%d}"


class ScannerTab(QWidget):
    bubbles_changed = Signal()
    status_message = Signal(str)

    def __init__(self, storage: Storage, cfg: Config, parent=None):
        super().__init__(parent)
        self.storage, self.cfg = storage, cfg
        self.results: dict[str, object] = {}  # ScanSession: tunnus -> ScanResult (muistissa)
        self.worker: ScanWorker | None = None
        self._build()
        self.reload_watchlist()
        self.chart.clear("Valitse tunnukset ja paina Skannaa")

    # --- rakenne ---
    def _build(self):
        # Seurantalista
        self.watch = QListWidget()
        self.watch.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.watch.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.filter = QLineEdit(placeholderText="Hae listasta…", clearButtonEnabled=True)
        self.filter.textChanged.connect(self.apply_filter)
        self.new_ticker = QLineEdit(placeholderText="esim. NVDA tai ^OMXH25")
        self.new_ticker.returnPressed.connect(self.add_ticker)
        add_btn = QPushButton("Lisää")
        add_btn.clicked.connect(self.add_ticker)
        rm_btn = QPushButton("Poista valitut")
        rm_btn.clicked.connect(self.remove_tickers)
        add_row = QHBoxLayout()
        add_row.addWidget(self.new_ticker, 1)
        add_row.addWidget(add_btn)
        self.wbox = wbox = QGroupBox("Seurantalista")
        wl = QVBoxLayout(wbox)
        wl.addWidget(self.filter)
        wl.addWidget(self.watch, 1)
        wl.addLayout(add_row)
        wl.addWidget(rm_btn)

        # Testitila
        self.asof_check = QCheckBox("Testitila: as-of-päivä")
        self.asof_date = QDateEdit(QDate.currentDate(), calendarPopup=True)
        self.asof_date.setDisplayFormat("yyyy-MM-dd")
        self.asof_date.setEnabled(False)
        self.asof_check.toggled.connect(self.asof_date.setEnabled)
        self.presets = QComboBox()
        self.presets.addItem("Pikavalinta…")
        for ticker, date, label in TEST_PRESETS:
            self.presets.addItem(f"{label} ({ticker}, {date})", (ticker, date))
        self.presets.activated.connect(self.apply_preset)
        tbox = QGroupBox("Testaus historiallisilla kuplilla")
        tl = QVBoxLayout(tbox)
        tl.addWidget(self.asof_check)
        tl.addWidget(self.asof_date)
        tl.addWidget(self.presets)

        # Skannaus
        self.scan_all_btn = QPushButton("Skannaa kaikki")
        self.scan_all_btn.clicked.connect(lambda: self.start_scan(all_=True))
        self.scan_sel_btn = QPushButton("Skannaa valitut")
        self.scan_sel_btn.clicked.connect(lambda: self.start_scan(all_=False))
        self.stop_btn = QPushButton("Keskeytä")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)
        self.progress = QProgressBar()
        self.progress_label = QLabel("")
        self.progress_label.setWordWrap(True)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(wbox, 1)
        ll.addWidget(tbox)
        ll.addWidget(self.scan_all_btn)
        ll.addWidget(self.scan_sel_btn)
        ll.addWidget(self.stop_btn)
        ll.addWidget(self.progress)
        ll.addWidget(self.progress_label)

        # Tulokset + kuvaaja
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

        right = QSplitter(Qt.Vertical)
        right.addWidget(self.table)
        right.addWidget(self.chart)
        right.setSizes([200, 500])

        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([310, 890])
        lay = QHBoxLayout(self)
        lay.addWidget(split)

    # --- seurantalista ---
    def reload_watchlist(self):
        self.watch.clear()
        for row in self.storage.list_watchlist():
            label = row["ticker"] + (f"  –  {row['name']}" if row["name"] else "")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, row["ticker"])
            self.watch.addItem(item)
        self.wbox.setTitle(f"Seurantalista ({self.watch.count()})")
        self.apply_filter(self.filter.text())

    def apply_filter(self, text: str):
        text = text.strip().lower()
        for i in range(self.watch.count()):
            item = self.watch.item(i)
            item.setHidden(bool(text) and text not in item.text().lower())

    def add_ticker(self):
        ticker = self.new_ticker.text().strip().upper()
        if ticker:
            self.storage.add_ticker(ticker)
            self.new_ticker.clear()
            self.reload_watchlist()

    def remove_tickers(self):
        for item in self.watch.selectedItems():
            self.storage.remove_ticker(item.data(Qt.UserRole))
        self.reload_watchlist()

    def apply_preset(self, index: int):
        data = self.presets.itemData(index)
        if not data:
            return
        ticker, date = data
        self.asof_check.setChecked(True)
        self.asof_date.setDate(QDate.fromString(date, "yyyy-MM-dd"))
        self.storage.add_ticker(ticker)
        self.reload_watchlist()
        for i in range(self.watch.count()):
            item = self.watch.item(i)
            item.setSelected(item.data(Qt.UserRole) == ticker)
            if item.isSelected():
                self.watch.scrollToItem(item)

    # --- skannaus ---
    def as_of(self) -> pd.Timestamp:
        if self.asof_check.isChecked():
            return pd.Timestamp(self.asof_date.date().toString("yyyy-MM-dd"))
        return pd.Timestamp.today().normalize()

    def start_scan(self, all_: bool):
        # "Kaikki" = listassa näkyvät, eli hakusuodatin rajaa skannausta
        items = ([self.watch.item(i) for i in range(self.watch.count())
                  if not self.watch.item(i).isHidden()] if all_
                 else self.watch.selectedItems())
        tickers = [it.data(Qt.UserRole) for it in items]
        if not tickers:
            QMessageBox.information(self, "Ei tunnuksia", "Valitse vähintään yksi tunnus.")
            return
        self.is_test = self.asof_check.isChecked()
        self.results.clear()
        self.table.setRowCount(0)
        self.chart.clear("Skannataan…")
        self._set_running(True)
        self.worker = ScanWorker(tickers, self.as_of(), self.cfg, self.storage.path)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)  # QThread.finished: run() on palannut
        self.worker.start()

    def stop_scan(self):
        if self.worker:
            self.worker.requestInterruption()
            self.progress_label.setText("Keskeytetään nykyisen tunnuksen jälkeen…")

    def _set_running(self, running: bool):
        for w in (self.scan_all_btn, self.scan_sel_btn):
            w.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def on_progress(self, done: int, total: int, msg: str):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.progress_label.setText(msg)

    def on_failed(self, ticker: str, err: str):
        self.status_message.emit(err)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(ticker))
        self.table.setItem(row, len(COLUMNS) - 1, QTableWidgetItem("⚠ virhe: " + err))

    def on_result(self, sr):
        self.results[sr.ticker] = sr
        scan_id = self.storage.save_scan(sr)
        status = sr.status(self.cfg)
        if sr.detected:
            bubble_id = self.storage.save_bubble(sr, scan_id, self.is_test)
            self.status_message.emit(
                f"Kupla havaittu: {sr.ticker}, tc ≈ {sr.tc_median:%Y-%m-%d} – "
                f"tallennettu (#{bubble_id}) ja seuranta aloitettu")
            self.bubbles_changed.emit()

        row = self.table.rowCount()
        self.table.insertRow(row)
        days = "–" if sr.tc_median is None else str((sr.tc_median - sr.as_of).days)
        values = [sr.ticker, f"{sr.conf_pos:.0%}", f"{sr.conf_neg:.0%}", _d(sr.tc_median),
                  f"{_d(sr.tc_p10)} … {_d(sr.tc_p90)}" if sr.tc_p10 is not None else "–",
                  days, STATUS_LABEL[status]]
        for col, v in enumerate(values):
            item = QTableWidgetItem(v)
            item.setData(Qt.UserRole, sr.ticker)
            if status in STATUS_COLOR:
                item.setBackground(STATUS_COLOR[status])
            self.table.setItem(row, col, item)
        if self.table.rowCount() == 1:
            self.table.selectRow(0)

    def on_finished(self):
        self._set_running(False)
        self.progress.setValue(self.progress.maximum())
        found = sum(1 for sr in self.results.values() if sr.detected)
        self.progress_label.setText(f"Valmis: {len(self.results)} skannattu, {found} kuplaa")
        self.worker = None

    def show_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        sr = self.results.get(items[0].data(Qt.UserRole))
        if sr is None:
            self.chart.clear("Ei tulosta")
            return
        draw_scan(self.chart.ax, sr)
        safe = sr.ticker.replace("^", "").replace("=", "")
        self.chart.redraw(f"{safe}_asof-{sr.as_of:%Y-%m-%d}.png")
