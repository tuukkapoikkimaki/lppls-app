import numpy as np

from lppls_app.config import Config
from lppls_app.model import fit_lppls, is_qualified, lppls


def test_fit_recovers_parameters():
    t = np.linspace(2000, 2002, 500)
    y = lppls(t, 2002.15, 0.5, 9.0, 5, -1.0, 0.1, 0.05)
    y += np.random.default_rng(1).normal(0, 0.01, len(t))
    r = fit_lppls(t, y, (t[-1] + 0.003, t[-1] + 1.0), (0.01, 0.99), (2, 25), seed=0)
    assert abs(r.tc - 2002.15) < 0.02 * 2
    assert abs(r.m - 0.5) < 0.05
    assert abs(r.omega - 9.0) < 0.9
    assert r.r2 > 0.99
    assert is_qualified(r, Config()) == "pos"


def test_negative_bubble_sign():
    t = np.linspace(2000, 2002, 500)
    y = lppls(t, 2002.15, 0.5, 9.0, 5, +1.0, 0.1, 0.05)
    r = fit_lppls(t, y, (t[-1] + 0.003, t[-1] + 1.0), (0.01, 0.99), (2, 25), seed=0)
    assert is_qualified(r, Config()) == "neg"


def test_too_short_series():
    t = np.linspace(2000, 2000.1, 10)
    assert fit_lppls(t, np.ones(10), (2000.2, 2001)) is None
