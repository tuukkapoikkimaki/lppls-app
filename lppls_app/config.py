"""Sovelluksen asetukset: polut, ikkunat ja kynnysarvot."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def default_db_path() -> Path:
    env = os.environ.get("LPPLS_DB")
    if env:
        return Path(env)
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "lppls-app" / "bubbles.db"


DEFAULT_WATCHLIST = [
    ("^GSPC", "S&P 500"),
    ("^NDX", "Nasdaq 100"),
    ("BTC-USD", "Bitcoin"),
    ("ETH-USD", "Ethereum"),
    ("000001.SS", "Shanghai Composite"),
    ("GC=F", "Kulta"),
]

# Historialliset testikuplat (as-of-pikavalinnat)
TEST_PRESETS = [
    ("BTC-USD", "2017-12-01", "Bitcoin 2017"),
    ("000001.SS", "2007-10-01", "Shanghai 2007"),
    ("000001.SS", "2015-06-01", "Shanghai 2015"),
]


@dataclass
class Config:
    # Datan haku
    lookback_days: int = 3 * 365
    cache_max_age_hours: float = 24.0

    # Sovitusikkunat (kauppapäiviä); kaikki päättyvät as_of-päivään
    window_min: int = 60
    window_max: int = 750
    window_step: int = 15
    n_starts: int = 10
    tc_max_frac: float = 0.5  # tc ≤ as_of + 0.5·ikkunan pituus

    # Hakualue on väljempi kuin kuplaehdot, jotta optimi ei jää rajalle
    m_search: tuple[float, float] = (0.01, 0.99)
    omega_search: tuple[float, float] = (2.0, 25.0)

    # Kuplaehdot (Sornetten suodatin)
    m_bounds: tuple[float, float] = (0.1, 0.9)
    omega_bounds: tuple[float, float] = (6.0, 13.0)
    max_c_over_b: float = 1.0
    min_oscillations: float = 2.5

    # Havainto
    horizon_days: int = 182
    confidence_threshold: float = 0.15
    near_threshold: float = 0.05  # 🟡 "lähellä"

    # Seuranta
    min_tolerance_days: int = 30
    crash_threshold: float = 0.15
    crash_window_days: int = 90

    # Rinnakkaisuus
    workers: int = max(1, (os.cpu_count() or 2) - 1)
