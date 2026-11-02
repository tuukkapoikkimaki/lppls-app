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


def test_small_price_rise_is_not_a_bubble(cfg):
    # Sama LPPLS-muoto mutta pieni amplitudi: nousu 2 vuodessa jää alle 100 %
    s = synthetic_bubble(B=-0.2, noise=0.002)
    sr = scan_series("SMALL", s, "2020-06-01", cfg)
    assert sr.runup < cfg.min_runup
    assert not sr.detected


def test_short_config(cfg):
    sc = cfg.short()
    assert sc.method == "L" and sc.window_max == 252 and sc.runup_days == 365
    assert sc.min_runup == 0.5 and sc.confidence_threshold == cfg.confidence_threshold
    assert sc.tc_qual_frac == 0.2 and cfg.tc_qual_frac == 0.13
    assert cfg.method == "P"  # alkuperäinen ei muutu


def test_scan_both_runs_both_methods(cfg):
    from lppls_app.scanner import scan_both, window_lengths

    s = synthetic_bubble(as_of="2020-06-01", tc="2020-07-15")
    calls = []
    dual = scan_both("SYN", s, "2020-06-01", cfg, progress=lambda d, t: calls.append((d, t)))
    assert dual.long.method == "P" and dual.short.method == "L"
    assert len(dual.short.fits) == len(window_lengths(len(s), cfg.short()))
    assert max(f.length for f in dual.short.fits) <= 252
    assert dual.long.detected and dual.method in ("P", "P+L")
    assert dual.primary is dual.long
    total = len(dual.long.fits) + len(dual.short.fits)
    assert calls[-1] == (total, total)  # edistyminen kattaa molemmat vaiheet


def test_short_needs_one_year_rise(cfg):
    from lppls_app.scanner import scan_both

    # Sama muoto pienellä amplitudilla: vuoden nousu jää alle 50 %
    dual = scan_both("SMALL", synthetic_bubble(B=-0.2, noise=0.002), "2020-06-01", cfg)
    assert dual.short.runup < 0.5
    assert not dual.short.detected and dual.method is None
