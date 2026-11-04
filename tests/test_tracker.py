import numpy as np
import pandas as pd

from lppls_app.storage import Storage
from lppls_app.scanner import scan_series
from lppls_app.tracker import HIT, MISS, PENDING, evaluate_outcome, update_all

from .conftest import synthetic_bubble

BUBBLE = {"detected_as_of": "2020-05-29", "tc": "2020-07-15", "tc_p10": "2020-07-01", "tc_p90": "2020-07-30", "sign": "pos"}


def _series(points):
    idx = pd.to_datetime([d for d, _ in points])
    return pd.Series([p for _, p in points], index=idx, dtype=float)


def test_hit_when_peak_then_crash(cfg):
    s = _series([("2020-06-01", 100), ("2020-07-10", 130), ("2020-08-01", 100)])
    o = evaluate_outcome(BUBBLE, s, "2020-09-01", cfg)
    assert o.status == HIT
    assert o.peak_date == pd.Timestamp("2020-07-10")
    assert o.drawdown > 0.2


def test_pending_before_window_ends(cfg):
    s = _series([("2020-06-01", 100), ("2020-07-10", 110)])
    assert evaluate_outcome(BUBBLE, s, "2020-07-12", cfg).status == PENDING


def test_miss_when_no_crash(cfg):
    days = pd.bdate_range("2020-06-01", "2021-03-01")
    s = pd.Series(np.linspace(100, 150, len(days)), index=days)
    assert evaluate_outcome(BUBBLE, s, "2021-03-01", cfg).status == MISS


def test_early_peak_is_found(cfg):
    s = _series([("2020-06-01", 100), ("2020-06-10", 140), ("2020-06-25", 100), ("2020-07-20", 105)])
    o = evaluate_outcome(BUBBLE, s, "2020-09-01", cfg)
    assert o.status == HIT and o.peak_date == pd.Timestamp("2020-06-10")


def test_negative_bubble_rebound(cfg):
    b = dict(BUBBLE, sign="neg")
    s = _series([("2020-06-01", 100), ("2020-07-10", 70), ("2020-08-15", 90)])
    assert evaluate_outcome(b, s, "2020-09-01", cfg).status == HIT


def test_update_all_incremental(cfg):
    store = Storage(":memory:", seed_watchlist=False)
    sr = scan_series("SYN", synthetic_bubble(), "2020-06-01", cfg)
    store.save_bubble(sr, store.save_scan(sr), is_test=True)
    calls = []

    def fake_fetch(ticker, start, end):
        calls.append(pd.Timestamp(start))
        days = pd.bdate_range(start, end)
        # huippu heinäkuussa ja romahdus
        peak = pd.Timestamp("2020-07-14")
        vals = [200 * (1 - 0.004 * abs((d - peak).days)) for d in days]
        return pd.Series(vals, index=days)

    s1 = update_all(store, cfg, today="2020-09-30", fetch=fake_fetch)
    assert s1.new_rows > 0 and not s1.errors
    b = store.list_bubbles()[0]
    assert b["status"] == HIT

    s2 = update_all(store, cfg, today="2020-10-05", fetch=fake_fetch)
    assert calls[1] > pd.Timestamp("2020-09-29")  # jatkaa siitä mihin jäi
    assert s2.new_rows <= 5


def test_rescan_tracked_saves_both_methods_once(cfg):
    from lppls_app.scanner import scan_both
    from lppls_app.tracker import UpdateSummary, rescan_tracked

    store = Storage(":memory:", seed_watchlist=False)
    sr = scan_series("SYN", synthetic_bubble(), "2020-06-01", cfg)
    store.save_bubble(sr, store.save_scan(sr), is_test=True)
    series = synthetic_bubble(as_of="2020-06-01")
    scans = []

    def fake_scan(ticker, s, as_of, cfg, executor=None, progress=None):
        scans.append(ticker)
        return scan_both(ticker, s, as_of, cfg)

    summary = UpdateSummary()
    kw = dict(today="2020-06-01", scan=fake_scan, prices=lambda *a, **k: series)
    rescan_tracked(store, cfg, summary, **kw)
    assert summary.rescanned == ["SYN"] and scans == ["SYN"]
    assert len(store.confidence_history("SYN", "L", "pos")) == 1
    rescan_tracked(store, cfg, summary, **kw)  # sama päivä: ei uudelleen
    assert scans == ["SYN"]


def test_turn_is_first_peak_with_5_percent_drop(cfg):
    from lppls_app.tracker import find_turn

    # 4 %:n notkahdus ei ole käänne; 120 -> 113 (−5,8 %) on
    s = _series([("2020-06-01", 100), ("2020-06-05", 110), ("2020-06-08", 106),
                 ("2020-06-20", 120), ("2020-06-25", 113), ("2020-07-10", 130)])
    assert find_turn(s, pos=True, threshold=0.05) == pd.Timestamp("2020-06-20")
    o = evaluate_outcome(BUBBLE, pd.concat([s, _series([("2020-08-01", 95)])]), "2020-12-01", cfg)
    assert o.peak_date == pd.Timestamp("2020-06-20") and o.status == HIT  # 120 -> 95 = −21 %


def test_turn_without_big_drop_is_miss(cfg):
    s = _series([("2020-06-01", 100), ("2020-07-10", 120), ("2020-07-15", 113),
                 ("2020-08-01", 118), ("2020-10-01", 125)])
    o = evaluate_outcome(BUBBLE, s, "2020-12-01", cfg)
    assert o.peak_date == pd.Timestamp("2020-07-10") and o.status == MISS


def test_no_turn_yet_is_pending(cfg):
    s = _series([("2020-06-01", 100), ("2020-07-01", 110), ("2020-07-05", 107)])  # −2,7 %
    o = evaluate_outcome(BUBBLE, s, "2020-07-06", cfg)
    assert o.status == PENDING and o.peak_date is None


def test_turn_after_window_is_miss(cfg):
    s = _series([("2020-06-01", 100), ("2020-10-01", 150), ("2020-10-10", 100)])
    assert evaluate_outcome(BUBBLE, s, "2021-01-01", cfg).status == MISS


def test_antibubble_turn_is_5_percent_rise_from_low(cfg):
    from lppls_app.tracker import find_turn

    s = _series([("2020-06-01", 100), ("2020-06-10", 80), ("2020-06-12", 83),
                 ("2020-07-01", 70), ("2020-07-05", 74)])
    assert find_turn(s, pos=False, threshold=0.05) == pd.Timestamp("2020-07-01")
