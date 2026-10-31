"""Kuvaajat: log-hinnat pisteinä, LPPLS-sovite mustana ja tc punaisena katkoviivana."""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.axes import Axes

from .model import LPPLSResult, from_years, to_years

PRICE_COLOR = "#1f77b4"
FOLLOW_COLOR = "#ff7f0e"
TC_COLOR = "#d62728"


def _style(ax: Axes, title: str):
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Päivämäärä")
    ax.set_ylabel("ln P")
    ax.grid(True, linestyle=":", alpha=0.7)
    ax.legend(loc="upper center", ncol=4, frameon=True, fontsize=9,
              bbox_to_anchor=(0.5, 1.0))


def _fit_curve(ax: Axes, fit: LPPLSResult, end_years: float | None = None):
    end = min(end_years if end_years is not None else fit.tc, fit.tc - 1e-4)
    t = np.linspace(fit.t1, end, 600)
    dates = pd.DatetimeIndex([from_years(x) for x in t])
    ax.plot(dates, fit.predict(t), color="black", linewidth=1.6, label="LPPLS-sovite")


def _tc_band(ax: Axes, tc, p10, p90):
    if p10 is not None and p90 is not None and p90 > p10:
        ax.axvspan(p10, p90, color=TC_COLOR, alpha=0.08, label="tc 10–90 %")
    ax.axvline(tc, color=TC_COLOR, linestyle=":", linewidth=1.5, label=f"tc {tc:%Y-%m-%d}")


def _sign_text(sign: str | None) -> str:
    return {"pos": "Positiivinen kupla", "neg": "Negatiivinen kupla (antikupla)"}.get(sign, "")


def draw_scan(ax: Axes, sr) -> None:
    """Skannauksen tulos: hinnat as_of-päivään, mediaanisovite ja tc-jakauma."""
    ax.clear()
    s = sr.series
    if sr.best is not None:
        s = s[s.index >= from_years(sr.best.t1) - pd.Timedelta(days=30)]
    ax.scatter(s.index, np.log(s.to_numpy()), s=6, color=PRICE_COLOR, label="Log-hinta")
    if sr.best is not None:
        _fit_curve(ax, sr.best)
        _tc_band(ax, sr.tc_median, sr.tc_p10, sr.tc_p90)
    ax.axvline(sr.as_of, color="grey", linewidth=1, label=f"as of {sr.as_of:%Y-%m-%d}")
    conf = f"confidence +{sr.conf_pos:.0%} / −{sr.conf_neg:.0%}"
    _style(ax, f"{sr.ticker} – {conf}")
    if sr.sign:
        ax.text(0.5, 0.02, _sign_text(sr.sign), transform=ax.transAxes, ha="center", fontsize=10)


def draw_tracked(ax: Axes, bubble, snapshot: pd.Series, follow: pd.Series) -> None:
    """Tallennettu kupla: jäädytetty ennuste vs. havainnon jälkeinen toteuma."""
    ax.clear()
    fit = LPPLSResult(
        tc=bubble["tc_years"], m=bubble["m"], omega=bubble["omega"], A=bubble["A"],
        B=bubble["B"], C1=bubble["C1"], C2=bubble["C2"], rmse=0.0, r2=bubble["r2"],
        t1=float(to_years(bubble["window_start"])), t2=float(to_years(bubble["detected_as_of"])))
    start = pd.Timestamp(bubble["window_start"]) - pd.Timedelta(days=30)
    snap = snapshot[snapshot.index >= start]
    ax.scatter(snap.index, np.log(snap.to_numpy()), s=6, color=PRICE_COLOR, label="Log-hinta (havainto)")
    # Toteumaa näytetään puoli vuotta ennustevälin yli, jotta käänne erottuu
    view_end = pd.Timestamp(bubble["tc_p90"] or bubble["tc"]) + pd.Timedelta(days=180)
    follow = follow[follow.index <= view_end]
    if not follow.empty:
        ax.scatter(follow.index, np.log(follow.to_numpy()), s=6, color=FOLLOW_COLOR,
                   label="Toteuma")
    _fit_curve(ax, fit)
    _tc_band(ax, pd.Timestamp(bubble["tc"]),
             pd.Timestamp(bubble["tc_p10"]) if bubble["tc_p10"] else None,
             pd.Timestamp(bubble["tc_p90"]) if bubble["tc_p90"] else None)
    ax.axvline(pd.Timestamp(bubble["detected_as_of"]), color="grey", linewidth=1, label="havaittu")
    if bubble["actual_peak_date"]:
        ax.plot(pd.Timestamp(bubble["actual_peak_date"]), np.log(bubble["actual_peak_price"]),
                marker="v" if bubble["sign"] != "neg" else "^", color="black", markersize=9,
                linestyle="none", label="toteutunut käänne")
    test = " (testi)" if bubble["is_test"] else ""
    _style(ax, f"{bubble['ticker']}{test} – {bubble['status']}")
    ax.text(0.5, 0.02, _sign_text(bubble["sign"]), transform=ax.transAxes, ha="center", fontsize=10)
