"""Kuvaajat: log-hinnat pisteinä, LPPLS-sovite mustana ja tc punaisena katkoviivana."""
from __future__ import annotations

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.ticker import PercentFormatter

from .model import LPPLSResult, from_years, to_years

PRICE_COLOR = "#1f77b4"
FOLLOW_COLOR = "#ff7f0e"
TC_COLOR = "#d62728"
# Confidence-viivat oikealla asteikolla: pitkä punainen, lyhyt vihreä
CONF_COLORS = {"P": "#c0392b", "L": "#2ca02c"}
CONF_LABELS = {"P": "C P", "L": "C L"}
METHOD_NAMES = {"P": "pitkä", "L": "lyhyt"}


def _reset(ax: Axes):
    """Tyhjentää akselin ja poistaa edellisen piirron oikean asteikon (twinx)."""
    for other in list(ax.figure.axes):
        if other is not ax:
            other.remove()
    ax.clear()


def _style(ax: Axes, title: str, ylabel: str = "ln P"):
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Päivämäärä")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle=":", alpha=0.7)
    handles, labels = ax.get_legend_handles_labels()
    for other in ax.figure.axes:  # oikean asteikon viivat samaan selitteeseen
        if other is not ax:
            h, lab = other.get_legend_handles_labels()
            handles, labels = handles + h, labels + lab
    leg = ax.legend(handles, labels, loc="upper center", ncol=4, frameon=True, fontsize=9,
                    bbox_to_anchor=(0.5, 1.0))
    leg.set_zorder(10)


def _fit_curve(ax: Axes, fit: LPPLSResult, end_years: float | None = None, log: bool = True):
    end = min(end_years if end_years is not None else fit.tc, fit.tc - 1e-4)
    t = np.linspace(fit.t1, end, 600)
    dates = pd.DatetimeIndex([from_years(x) for x in t])
    y = fit.predict(t)
    ax.plot(dates, y if log else np.exp(y), color="black", linewidth=1.6, label="LPPLS-sovite")


def _tc_band(ax: Axes, tc, p10, p90):
    if p10 is not None and p90 is not None and p90 > p10:
        ax.axvspan(p10, p90, color=TC_COLOR, alpha=0.08, label="tc 10–90 %")
    ax.axvline(tc, color=TC_COLOR, linestyle=":", linewidth=1.5, label=f"tc {tc:%Y-%m-%d}")


def _sign_text(sign: str | None) -> str:
    return {"pos": "Positiivinen kupla", "neg": "Negatiivinen kupla (antikupla)"}.get(sign, "")


def _label(ticker: str, name: str = "") -> str:
    return f"{ticker} · {name}" if name else ticker


def draw_scan(ax: Axes, sr, name: str = "") -> None:
    """Skannauksen tulos: hinnat as_of-päivään, mediaanisovite ja tc-jakauma."""
    _reset(ax)
    s = sr.series
    if sr.best is not None:
        s = s[s.index >= from_years(sr.best.t1) - pd.Timedelta(days=30)]
    ax.scatter(s.index, np.log(s.to_numpy()), s=6, color=PRICE_COLOR, label="Log-hinta")
    if sr.best is not None:
        _fit_curve(ax, sr.best)
        _tc_band(ax, sr.tc_median, sr.tc_p10, sr.tc_p90)
    ax.axvline(sr.as_of, color="grey", linewidth=1, label=f"as of {sr.as_of:%Y-%m-%d}")
    conf = f"C {sr.method} +{sr.conf_pos:.0%} / −{sr.conf_neg:.0%}"
    _style(ax, f"{_label(sr.ticker, name)} – {METHOD_NAMES.get(sr.method, '')} menetelmä – {conf}")
    if sr.sign:
        ax.text(0.5, 0.02, _sign_text(sr.sign), transform=ax.transAxes, ha="center", fontsize=10)


def _conf_axis(ax: Axes, conf: dict[str, pd.Series]):
    """Confidence-historia oikealle asteikolle; vain kuvan aikavälille osuvat pisteet."""
    lo, hi = (mdates.num2date(x).replace(tzinfo=None) for x in ax.get_xlim())
    shown = {m: s[(s.index >= lo) & (s.index <= hi)] for m, s in conf.items()}
    if not any(len(s) for s in shown.values()):
        return
    right = ax.twinx()
    top = 0.0
    for m, s in shown.items():
        if len(s):
            right.plot(s.index, s.to_numpy(), color=CONF_COLORS[m], linewidth=1.6, marker="o",
                       markersize=3.5, label=CONF_LABELS[m])
            top = max(top, float(s.max()))
    right.set_ylim(0, min(1.0, max(0.3, top * 1.25)))
    right.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    right.set_ylabel("Confidence")
    right.set_xlim(ax.get_xlim())


def draw_tracked(ax: Axes, bubble, snapshot: pd.Series, follow: pd.Series,
                 log: bool = True, conf: dict[str, pd.Series] | None = None,
                 name: str = "") -> None:
    """Tallennettu kupla: jäädytetty ennuste vs. havainnon jälkeinen toteuma.

    log=False piirtää hinnan sellaisenaan (ilman logaritmia) ja koko seuratun
    kehityksen viimeisimpään päivään asti. conf = {"P": sarja, "L": sarja} piirtää
    menetelmien confidence-historian oikealle asteikolle.
    """
    _reset(ax)
    f = np.log if log else np.asarray
    fit = LPPLSResult(
        tc=bubble["tc_years"], m=bubble["m"], omega=bubble["omega"], A=bubble["A"],
        B=bubble["B"], C1=bubble["C1"], C2=bubble["C2"], rmse=0.0, r2=bubble["r2"],
        t1=float(to_years(bubble["window_start"])), t2=float(to_years(bubble["detected_as_of"])))
    start = pd.Timestamp(bubble["window_start"]) - pd.Timedelta(days=30)
    snap = snapshot[snapshot.index >= start]
    ax.scatter(snap.index, f(snap.to_numpy()), s=6, color=PRICE_COLOR,
               label="Log-hinta (havainto)" if log else "Hinta (havainto)")
    if log:
        # Toteumaa näytetään puoli vuotta ennustevälin yli, jotta käänne erottuu
        view_end = pd.Timestamp(bubble["tc_p90"] or bubble["tc"]) + pd.Timedelta(days=180)
        follow = follow[follow.index <= view_end]
    if not follow.empty:
        ax.scatter(follow.index, f(follow.to_numpy()), s=6, color=FOLLOW_COLOR,
                   label="Toteuma")
    _fit_curve(ax, fit, log=log)
    _tc_band(ax, pd.Timestamp(bubble["tc"]),
             pd.Timestamp(bubble["tc_p10"]) if bubble["tc_p10"] else None,
             pd.Timestamp(bubble["tc_p90"]) if bubble["tc_p90"] else None)
    ax.axvline(pd.Timestamp(bubble["detected_as_of"]), color="grey", linewidth=1, label="havaittu")
    if bubble["actual_peak_date"]:
        ax.plot(pd.Timestamp(bubble["actual_peak_date"]), f(bubble["actual_peak_price"]),
                marker="v" if bubble["sign"] != "neg" else "^", color="black", markersize=9,
                linestyle="none", label="toteutunut käänne")
    if conf:
        _conf_axis(ax, conf)
    test = " (testi)" if bubble["is_test"] else ""
    _style(ax, f"{_label(bubble['ticker'], name)}{test} – {bubble['status']}",
           "ln P" if log else "Hinta")
    ax.text(0.5, 0.02, _sign_text(bubble["sign"]), transform=ax.transAxes, ha="center", fontsize=10)
