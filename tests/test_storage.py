import pandas as pd
import pytest

from lppls_app.data import get_prices
from lppls_app.scanner import scan_series
from lppls_app.storage import Storage

from .conftest import synthetic_bubble


@pytest.fixture
def store():
    s = Storage(":memory:", seed_watchlist=False)
    yield s
    s.close()


@pytest.fixture
def detected(cfg):
    sr = scan_series("SYN", synthetic_bubble(), "2020-06-01", cfg)
    assert sr.detected
    return sr


def test_watchlist(store):
    store.add_ticker("AAA", "a")
    store.add_ticker("BBB")
    store.remove_ticker("AAA")
    assert [r["ticker"] for r in store.list_watchlist()] == ["BBB"]
    store.add_ticker("AAA")  # palautuu
    assert {r["ticker"] for r in store.list_watchlist()} == {"AAA", "BBB"}


def test_default_watchlist_seeded():
    s = Storage(":memory:")
    assert len(s.list_watchlist()) >= 5


def test_save_and_load_bubble(store, detected):
    scan_id = store.save_scan(detected)
    bid = store.save_bubble(detected, scan_id, is_test=True)
    b = store.get_bubble(bid)
    assert b["ticker"] == "SYN" and b["status"] == "odottaa" and b["is_test"] == 1
    prices = store.bubble_prices(bid)
    assert len(prices) == len(detected.series)
    assert prices.index[-1] == detected.series.index[-1]


def test_duplicate_bubble_updates(store, detected):
    scan_id = store.save_scan(detected)
    a = store.save_bubble(detected, scan_id, is_test=False)
    b = store.save_bubble(detected, scan_id, is_test=False)
    assert a == b
    assert len(store.list_bubbles()) == 1
    assert len(store.bubble_prices(a)) == len(detected.series)


def test_delete_cascades(store, detected):
    bid = store.save_bubble(detected, store.save_scan(detected), is_test=False)
    store.delete_bubble(bid)
    assert store.get_bubble(bid) is None
    assert store.bubble_prices(bid).empty


def test_cache_used_for_historical_range(store):
    calls = []

    def fake_fetch(ticker, start, end):
        calls.append((start, end))
        return pd.Series([1.0, 2.0, 3.0],
                         index=pd.to_datetime(["2015-01-02", "2015-06-01", "2015-12-30"]))

    get_prices(store, "X", "2015-01-01", "2015-12-31", fetch=fake_fetch)
    s = get_prices(store, "X", "2015-01-01", "2015-12-31", fetch=fake_fetch)
    assert len(calls) == 1
    assert len(s) == 3


def test_cache_expires_for_recent_range(store):
    calls = []
    today = pd.Timestamp.today().normalize()

    def fake_fetch(ticker, start, end):
        calls.append(1)
        return pd.Series([1.0, 2.0], index=[today - pd.Timedelta(days=30), today])

    get_prices(store, "X", today - pd.Timedelta(days=31), today, fetch=fake_fetch)
    get_prices(store, "X", today - pd.Timedelta(days=31), today, fetch=fake_fetch)
    assert len(calls) == 1
    get_prices(store, "X", today - pd.Timedelta(days=31), today, max_age_hours=0, fetch=fake_fetch)
    assert len(calls) == 2
