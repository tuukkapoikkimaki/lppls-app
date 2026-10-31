"""Taustasäikeet: skannaus ja sarjojen päivitys, jotta käyttöliittymä ei jäädy."""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QThread, Signal

from ..config import Config
from ..data import DataError, get_prices
from ..scanner import make_executor, scan_series
from ..storage import Storage
from ..tracker import update_all


class ScanWorker(QThread):
    progress = Signal(int, int, str)        # tehty, yhteensä, viesti
    result = Signal(object)                 # ScanResult
    failed = Signal(str, str)               # tunnus, virhe

    def __init__(self, tickers: list[str], as_of: pd.Timestamp, cfg: Config, db_path: str):
        super().__init__()
        self.tickers, self.as_of, self.cfg, self.db_path = tickers, as_of, cfg, db_path

    def run(self):
        storage = Storage(self.db_path)
        executor = make_executor(self.cfg)
        try:
            n = len(self.tickers)
            for i, ticker in enumerate(self.tickers):
                if self.isInterruptionRequested():
                    break
                self.progress.emit(i * 100, n * 100, f"Haetaan {ticker}…")
                start = self.as_of - pd.Timedelta(days=self.cfg.lookback_days)
                try:
                    series = get_prices(storage, ticker, start, self.as_of,
                                        self.cfg.cache_max_age_hours)
                except DataError as e:
                    self.failed.emit(ticker, str(e))
                    continue

                def on_fit(done, total, i=i, ticker=ticker):
                    self.progress.emit(i * 100 + done * 100 // total, n * 100,
                                       f"Sovitetaan {ticker} ({done}/{total})")

                self.result.emit(scan_series(ticker, series, self.as_of, self.cfg,
                                             executor, on_fit))
        finally:
            executor.shutdown(cancel_futures=True)
            storage.close()


class UpdateWorker(QThread):
    progress = Signal(int, int)
    done = Signal(str)

    def __init__(self, cfg: Config, db_path: str):
        super().__init__()
        self.cfg, self.db_path = cfg, db_path

    def run(self):
        storage = Storage(self.db_path)
        try:
            summary = update_all(storage, self.cfg, progress=self.progress.emit)
            self.done.emit(summary.text())
        except Exception as e:  # näytetään käyttäjälle, ei kaadeta sovellusta
            self.done.emit(f"Päivitys epäonnistui: {e}")
        finally:
            storage.close()
