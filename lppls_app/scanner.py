"""Tulevien kuplien skannaus: LPPLS-sovitus moneen as_of-päivään päättyvään ikkunaan."""
from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .config import Config
from .model import LPPLSResult, fit_lppls, from_years, is_qualified, to_years


@dataclass
class WindowFit:
    length: int
    result: LPPLSResult | None
    sign: str | None  # 'pos' | 'neg' | None


@dataclass
class ScanResult:
    ticker: str
    as_of: pd.Timestamp
    series: pd.Series  # hinnat as_of-päivään asti
    fits: list[WindowFit] = field(default_factory=list)
    conf_pos: float = 0.0
    conf_neg: float = 0.0
    sign: str | None = None
    tc_median: pd.Timestamp | None = None
    tc_p10: pd.Timestamp | None = None
    tc_p90: pd.Timestamp | None = None
    best: LPPLSResult | None = None  # mediaani-tc:tä lähin hyväksytty sovitus
    runup: float = 0.0     # nousu runup_days-jakson pohjasta
    drawdown: float = 0.0  # lasku saman jakson huipusta
    detected: bool = False
    method: str = "P"      # "P" pitkä, "L" lyhyt
    state: str = "ei"      # "kupla" | "lähellä" | "ei"

    @property
    def confidence(self) -> float:
        return max(self.conf_pos, self.conf_neg)

    @property
    def move(self) -> float:
        """Kuplan suuntainen hinnanmuutos log-asteikolla (+100 % ≙ −50 %)."""
        if self.sign == "neg":
            return 1.0 / (1.0 - self.drawdown) - 1.0 if self.drawdown < 1 else np.inf
        return self.runup

    @property
    def change(self) -> float:
        """Toteutunut muutos kuplan suuntaan: nousu (+) tai lasku (−)."""
        return -self.drawdown if self.sign == "neg" else self.runup


STATE_RANK = {"kupla": 2, "lähellä": 1, "ei": 0}


@dataclass
class DualScan:
    """Saman tunnuksen pitkä (P) ja lyhyt (L) skannaus samalta as_of-päivältä."""
    long: ScanResult
    short: ScanResult

    @property
    def ticker(self) -> str:
        return self.long.ticker

    @property
    def as_of(self) -> pd.Timestamp:
        return self.long.as_of

    @property
    def detected(self) -> bool:
        return self.long.detected or self.short.detected

    @property
    def method(self) -> str | None:
        """Kupla havaittu: "P", "L", "P+L" tai None."""
        return "+".join(sr.method for sr in (self.long, self.short) if sr.detected) or None

    @property
    def primary(self) -> ScanResult:
        """Kuplan tiedot (tc, sovite) otetaan havainneesta menetelmästä, tasatilanteessa pitkästä."""
        return max((self.long, self.short), key=lambda sr: STATE_RANK[sr.state])


def window_lengths(n_points: int, cfg: Config) -> list[int]:
    """window_count tasavälistä pituutta; dataa pidemmät ikkunat jäävät pois."""
    lengths = np.rint(np.linspace(cfg.window_min, cfg.window_max, cfg.window_count)).astype(int)
    return [int(L) for L in lengths if L <= n_points]


def _fit_window(args) -> tuple[int, LPPLSResult | None]:
    length, t, y, tc_max_frac, m_bounds, omega_bounds, n_starts = args
    t1, t2 = t[0], t[-1]
    tc_bounds = (t2 + 1.0 / 365.25, t2 + tc_max_frac * (t2 - t1))
    res = fit_lppls(t, y, tc_bounds, m_bounds, omega_bounds, n_starts, seed=length)
    return length, res


def _jobs(series: pd.Series, cfg: Config):
    t_all = to_years(series.index)
    y_all = np.log(series.to_numpy(dtype=float))
    for L in window_lengths(len(series), cfg):
        yield (L, t_all[-L:], y_all[-L:], cfg.tc_max_frac,
               cfg.m_search, cfg.omega_search, cfg.n_starts)


def run_fits(series: pd.Series, cfg: Config, executor=None,
             progress: Callable[[int, int], None] | None = None) -> list[WindowFit]:
    jobs = list(_jobs(series, cfg))
    out: dict[int, LPPLSResult | None] = {}
    if executor is None:
        for i, job in enumerate(jobs, 1):
            L, res = _fit_window(job)
            out[L] = res
            if progress:
                progress(i, len(jobs))
    else:
        futures = [executor.submit(_fit_window, job) for job in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            L, res = fut.result()
            out[L] = res
            if progress:
                progress(i, len(jobs))
    return [WindowFit(L, out[L], is_qualified(out[L], cfg)) for L in sorted(out)]


def summarize(ticker: str, series: pd.Series, as_of, fits: list[WindowFit],
              cfg: Config) -> ScanResult:
    as_of = pd.Timestamp(as_of).normalize()
    horizon_end = to_years(as_of + pd.Timedelta(days=cfg.horizon_days))
    sr = ScanResult(ticker, as_of, series, fits, method=cfg.method)
    recent = series[series.index >= as_of - pd.Timedelta(days=cfg.runup_days)]
    if not recent.empty:
        last = float(recent.iloc[-1])
        sr.runup = last / float(recent.min()) - 1.0
        sr.drawdown = 1.0 - last / float(recent.max())
    n = len(fits)
    if n == 0:
        return sr

    def within(f: WindowFit, sign: str) -> bool:
        return f.sign == sign and f.result.tc <= horizon_end

    pos = [f for f in fits if within(f, "pos")]
    neg = [f for f in fits if within(f, "neg")]
    sr.conf_pos, sr.conf_neg = len(pos) / n, len(neg) / n
    chosen = pos if sr.conf_pos >= sr.conf_neg else neg
    if not chosen:
        return sr
    sr.sign = chosen[0].sign
    tcs = np.array([f.result.tc for f in chosen])
    med = float(np.median(tcs))
    sr.tc_median = from_years(med)
    sr.tc_p10 = from_years(float(np.percentile(tcs, 10)))
    sr.tc_p90 = from_years(float(np.percentile(tcs, 90)))
    sr.best = min(chosen, key=lambda f: abs(f.result.tc - med)).result
    sr.detected = (sr.confidence >= cfg.confidence_threshold
                   and med <= horizon_end
                   and sr.move >= cfg.min_runup)
    if sr.detected:
        sr.state = "kupla"
    elif sr.confidence >= cfg.near_threshold and sr.move >= cfg.near_runup:
        sr.state = "lähellä"
    return sr


def scan_series(ticker: str, series: pd.Series, as_of, cfg: Config,
                executor=None, progress=None) -> ScanResult:
    series = series[series.index <= pd.Timestamp(as_of)].dropna()
    series = series[series > 0]
    fits = run_fits(series, cfg, executor, progress) if len(series) >= cfg.window_min else []
    return summarize(ticker, series, as_of, fits, cfg)


def scan_both(ticker: str, series: pd.Series, as_of, cfg: Config,
              executor=None, progress=None) -> DualScan:
    """Ajaa pitkän ja lyhyen menetelmän samaan hintasarjaan."""
    short_cfg = cfg.short()
    n = len(series[(series.index <= pd.Timestamp(as_of)) & (series > 0)].dropna())
    n_long, n_short = len(window_lengths(n, cfg)), len(window_lengths(n, short_cfg))

    def phase(offset):
        if progress is None:
            return None
        return lambda done, _total: progress(offset + done, n_long + n_short)

    long = scan_series(ticker, series, as_of, cfg, executor, phase(0))
    short = scan_series(ticker, series, as_of, short_cfg, executor, phase(n_long))
    return DualScan(long, short)


def make_executor(cfg: Config) -> ProcessPoolExecutor:
    # spawn: turvallinen Qt-säikeistä käynnistettäessä
    return ProcessPoolExecutor(max_workers=cfg.workers, mp_context=mp.get_context("spawn"))
