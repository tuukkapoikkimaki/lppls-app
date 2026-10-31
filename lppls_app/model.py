"""LPPLS-malli ja sovitus (Filimonov & Sornette 2013).

ln p(t) = A + B·(tc−t)^m + C1·(tc−t)^m·cos(ω·ln(tc−t)) + C2·(tc−t)^m·sin(ω·ln(tc−t))

Aika on desimaalivuosina (ks. to_years). Lineaariset parametrit A, B, C1, C2 ratkaistaan
pienimmän neliösumman menetelmällä, ja epälineaariset (tc, m, ω) haetaan Nelder–Meadilla
useasta satunnaisesta alkupisteestä.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

_EPOCH = pd.Timestamp("1970-01-01")
_DAYS_PER_YEAR = 365.25


def to_years(dates) -> np.ndarray | float:
    """Päivämäärä(t) desimaalivuosiksi vuodesta 1970."""
    if isinstance(dates, (pd.Timestamp, str)):
        return (pd.Timestamp(dates) - _EPOCH).days / _DAYS_PER_YEAR
    idx = pd.DatetimeIndex(dates)
    return ((idx - _EPOCH) / pd.Timedelta(days=1)).to_numpy(dtype=float) / _DAYS_PER_YEAR


def from_years(t: float) -> pd.Timestamp:
    return (_EPOCH + pd.Timedelta(days=t * _DAYS_PER_YEAR)).normalize()


@dataclass
class LPPLSResult:
    tc: float
    m: float
    omega: float
    A: float
    B: float
    C1: float
    C2: float
    rmse: float
    r2: float
    t1: float  # ikkunan alku
    t2: float  # ikkunan loppu (as_of)

    @property
    def C(self) -> float:
        return math.hypot(self.C1, self.C2)

    @property
    def oscillations(self) -> float:
        """Log-periodisten puolivärähtelyjen määrä ikkunassa (Demos & Sornette)."""
        return self.omega / math.pi * math.log((self.tc - self.t1) / (self.tc - self.t2))

    @property
    def tc_date(self) -> pd.Timestamp:
        return from_years(self.tc)

    def predict(self, t: np.ndarray) -> np.ndarray:
        return lppls(t, self.tc, self.m, self.omega, self.A, self.B, self.C1, self.C2)


def lppls(t, tc, m, omega, A, B, C1, C2):
    dt = np.asarray(tc - t, dtype=float)
    f = np.power(dt, m)
    lg = omega * np.log(dt)
    return A + B * f + C1 * f * np.cos(lg) + C2 * f * np.sin(lg)


def _linear_solve(t, y, tc, m, omega):
    """Palauttaa (A, B, C1, C2) ja neliösumman kiinteillä tc, m, ω."""
    dt = tc - t
    if np.any(dt <= 0):
        return None, np.inf
    f = dt ** m
    lg = omega * np.log(dt)
    X = np.column_stack([np.ones_like(t), f, f * np.cos(lg), f * np.sin(lg)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    return coef, float(resid @ resid)


def fit_lppls(
    t: np.ndarray,
    y: np.ndarray,
    tc_bounds: tuple[float, float],
    m_bounds: tuple[float, float] = (0.1, 0.9),
    omega_bounds: tuple[float, float] = (6.0, 13.0),
    n_starts: int = 10,
    seed: int | None = None,
) -> LPPLSResult | None:
    """Sovittaa LPPLS:n log-hintoihin y aikapisteissä t (vuosina)."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(t) < 20:
        return None
    rng = np.random.default_rng(seed)
    bounds = [tc_bounds, m_bounds, omega_bounds]

    def cost(x):
        _, sse = _linear_solve(t, y, *x)
        return sse

    best_x, best_sse = None, np.inf
    for _ in range(n_starts):
        x0 = [rng.uniform(lo, hi) for lo, hi in bounds]
        res = minimize(cost, x0, method="Nelder-Mead", bounds=bounds,
                       options={"xatol": 1e-5, "fatol": 1e-8, "maxiter": 600})
        if res.fun < best_sse:
            best_x, best_sse = res.x, res.fun

    if best_x is None or not np.isfinite(best_sse):
        return None
    tc, m, omega = (float(v) for v in best_x)
    coef, sse = _linear_solve(t, y, tc, m, omega)
    if coef is None:
        return None
    sst = float(((y - y.mean()) ** 2).sum())
    return LPPLSResult(
        tc=tc, m=m, omega=omega,
        A=float(coef[0]), B=float(coef[1]), C1=float(coef[2]), C2=float(coef[3]),
        rmse=math.sqrt(sse / len(y)),
        r2=1.0 - sse / sst if sst > 0 else 0.0,
        t1=float(t[0]), t2=float(t[-1]),
    )


def is_qualified(res: LPPLSResult, cfg) -> str | None:
    """Palauttaa 'pos' (kupla), 'neg' (antikupla) tai None, jos ehdot eivät täyty."""
    if res is None:
        return None
    m_lo, m_hi = cfg.m_bounds
    w_lo, w_hi = cfg.omega_bounds
    eps = 1e-3  # rajalle jääneet sovitukset hylätään
    if not (m_lo + eps < res.m < m_hi - eps and w_lo + eps < res.omega < w_hi - eps):
        return None
    if res.B == 0 or res.C / abs(res.B) >= cfg.max_c_over_b:
        return None
    if res.oscillations < cfg.min_oscillations:
        return None
    return "pos" if res.B < 0 else "neg"
