import numpy as np
import pandas as pd
import pytest

from lppls_app.config import Config
from lppls_app.model import lppls, to_years


@pytest.fixture
def cfg():
    # Kevyempi skannaus testeihin
    return Config(window_min=120, window_max=480, window_count=10, n_starts=6, workers=1,
                  short_window_count=8)


def synthetic_bubble(as_of="2020-06-01", tc="2020-07-15", n=600, noise=0.01, seed=1, B=-1.2):
    """Arkipäiväinen LPPLS-sarja, joka päättyy as_of-päivään ennen tc:tä."""
    idx = pd.bdate_range(end=as_of, periods=n)
    t = to_years(idx)
    y = lppls(t, to_years(tc), 0.5, 9.0, 6.0, B, 0.06 * abs(B) / 1.2, 0.02 * abs(B) / 1.2)
    y = y + np.random.default_rng(seed).normal(0, noise, n)
    return pd.Series(np.exp(y), index=idx)


def random_walk(as_of="2020-06-01", n=600, seed=3):
    idx = pd.bdate_range(end=as_of, periods=n)
    steps = np.random.default_rng(seed).normal(0, 0.01, n)
    return pd.Series(100 * np.exp(np.cumsum(steps)), index=idx)
