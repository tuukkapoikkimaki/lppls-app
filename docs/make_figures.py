"""Dokumentin kuvat: python docs/make_figures.py (vaatii verkkoyhteyden Yahoo-dataa varten)."""
from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from lppls_app.config import Config
from lppls_app.data import fetch_yahoo
from lppls_app.model import from_years, lppls, to_years
from lppls_app.plot import FOLLOW_COLOR, PRICE_COLOR, TC_COLOR
from lppls_app.scanner import make_executor, scan_series

OUT = Path(__file__).parent / "fig"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.grid": True, "grid.linestyle": ":", "grid.alpha": 0.7})


def fig_model():
    """Kuva 1: LPPLS-käyrän osat synteettisellä esimerkillä."""
    tc = 2.0
    t = np.linspace(0, tc - 1e-4, 1500)
    A, B, m, w = 6.0, -1.2, 0.5, 9.0
    C1, C2 = 0.08, 0.03
    full = lppls(t, tc, m, w, A, B, C1, C2)
    trend = lppls(t, tc, m, w, A, B, 0, 0)
    rng = np.random.default_rng(4)
    ts = np.sort(rng.uniform(0, tc - 0.02, 260))
    obs = lppls(ts, tc, m, w, A, B, C1, C2) + rng.normal(0, 0.025, len(ts))

    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.scatter(ts, obs, s=5, color=PRICE_COLOR, label="havaittu log-hinta ln p(t)")
    ax.plot(t, trend, "--", color="grey", lw=1.3, label=r"potenssilaki $A+B(t_c-t)^m$")
    ax.plot(t, full, color="black", lw=1.5, label="LPPLS = potenssilaki + log-periodiset värähtelyt")
    ax.axvline(tc, color=TC_COLOR, ls=":", lw=1.6, label=r"kriittinen hetki $t_c$")
    ax.set_xlabel("aika (vuotta)")
    ax.set_ylabel("ln p")
    ax.legend(loc="upper left", fontsize=7.5, frameon=True)
    ax.annotate("värähtelyt tihenevät\nlähestyttäessä $t_c$:tä", xy=(1.93, 5.78), xytext=(1.22, 4.42),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.8))
    fig.tight_layout()
    fig.savefig(OUT / "kuva1_malli.png", dpi=220)
    plt.close(fig)


def fig_shanghai():
    """Kuvat 2 ja 3: Shanghai Composite, as-of 1.6.2015."""
    cfg = Config()
    as_of = pd.Timestamp("2015-06-01")
    series = fetch_yahoo("000001.SS", as_of - pd.Timedelta(days=cfg.lookback_days), "2015-09-30")
    with make_executor(cfg) as ex:
        sr = scan_series("000001.SS", series, as_of, cfg, executor=ex)
    after = series[series.index > as_of]
    print(f"conf+={sr.conf_pos:.2f} tc={sr.tc_median:%Y-%m-%d} runup={sr.runup:.0%} "
          f"peak={after.idxmax():%Y-%m-%d}")

    # Kuva 2: sovite ja toteuma
    b = sr.best
    start = from_years(b.t1) - pd.Timedelta(days=20)
    snap = sr.series[sr.series.index >= start]
    fig, ax = plt.subplots(figsize=(6.4, 3.1))
    ax.scatter(snap.index, np.log(snap), s=5, color=PRICE_COLOR, label="log-hinta havaintohetkeen asti")
    ax.scatter(after.index, np.log(after), s=5, color=FOLLOW_COLOR, label="toteuma (ei mallin käytössä)")
    tt = np.linspace(b.t1, b.tc - 1e-4, 800)
    ax.plot([from_years(x) for x in tt], b.predict(tt), color="black", lw=1.4, label="LPPLS-sovite")
    ax.axvspan(sr.tc_p10, sr.tc_p90, color=TC_COLOR, alpha=0.08, label=r"$t_c$ 10–90 %")
    ax.axvline(sr.tc_median, color=TC_COLOR, ls=":", lw=1.6,
               label=f"mediaani-$t_c$ {sr.tc_median:%d.%m.%Y}")
    ax.axvline(as_of, color="grey", lw=1, label="havaintohetki 1.6.2015")
    ax.set_ylabel("ln p")
    ax.legend(loc="upper left", fontsize=7, ncol=2)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "kuva2_shanghai.png", dpi=220)
    plt.close(fig)

    # Kuva 3: ikkunat ja hyväksytyt tc-arviot
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    end = sr.series.index[-1]
    idx = sr.series.index
    for f in sr.fits:
        s = idx[-f.length]
        ok = f.sign == "pos" and f.result.tc <= to_years(as_of + pd.Timedelta(days=cfg.horizon_days))
        ax.plot([s, end], [f.length, f.length], color=PRICE_COLOR if ok else "#c8c8c8",
                lw=2.2 if ok else 1.2, solid_capstyle="butt")
        if ok:
            ax.plot(f.result.tc_date, f.length, marker="|", color=TC_COLOR, ms=8, mew=2)
    ax.axvline(as_of, color="grey", lw=1)
    ax.set_ylabel("ikkunan pituus (kauppapäiviä)")
    ax.plot([], [], color=PRICE_COLOR, lw=2.2, label="suodattimen läpäissyt ikkuna")
    ax.plot([], [], color="#c8c8c8", lw=1.2, label="hylätty ikkuna")
    ax.plot([], [], marker="|", color=TC_COLOR, ls="none", ms=8, mew=2, label=r"ikkunan $t_c$-arvio")
    ax.legend(loc="lower left", fontsize=7)
    ax.set_title(f"confidence = {sum(1 for f in sr.fits if f.sign == 'pos')}/{len(sr.fits)}"
                 f" ≈ {sr.conf_pos:.0%}", fontsize=9)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / "kuva3_ikkunat.png", dpi=220)
    plt.close(fig)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    OUT.mkdir(exist_ok=True)
    fig_model()
    fig_shanghai()
