import pandas as pd

from lppls_app.scanner import scan_series

from .conftest import random_walk, synthetic_bubble


def test_detects_future_bubble(cfg):
    s = synthetic_bubble(as_of="2020-06-01", tc="2020-07-15")
    sr = scan_series("SYN", s, "2020-06-01", cfg)
    assert sr.detected
    assert sr.sign == "pos"
    assert sr.conf_pos >= 0.5
    assert abs((sr.tc_median - pd.Timestamp("2020-07-15")).days) <= 15
    assert sr.tc_median > sr.as_of


def test_random_walk_low_confidence(cfg):
    sr = scan_series("RW", random_walk(), "2020-06-01", cfg)
    assert not sr.detected
    assert sr.confidence < cfg.confidence_threshold


def test_as_of_cuts_future_data(cfg):
    s = synthetic_bubble(as_of="2020-06-01")
    sr = scan_series("SYN", s, "2020-03-01", cfg)
    assert sr.series.index[-1] <= pd.Timestamp("2020-03-01")
