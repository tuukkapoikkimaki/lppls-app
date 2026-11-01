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


def test_upgrade_adds_indices_and_keeps_user_choices(tmp_path):
    import sqlite3

    from lppls_app.config import (COMMODITY_WATCHLIST, CRYPTO_WATCHLIST, INDEX_WATCHLIST,
                                  THEME_WATCHLIST)

    db = tmp_path / "old.db"
    s = Storage(db, seed_watchlist=False)
    s.add_ticker("NVDA")
    s.add_ticker("^GSPC")
    s.remove_ticker("^GSPC")  # käyttäjä poisti
    s.close()
    con = sqlite3.connect(db)
    con.execute("PRAGMA user_version=1")  # vanha versio
    con.commit()
    con.close()

    s = Storage(db)
    tickers = [r["ticker"] for r in s.list_watchlist()]
    assert "NVDA" in tickers
    assert "^GSPC" not in tickers
    # −^GSPC; NVDA on myös THEME_WATCHLISTissa, joten se ei tuo ylimääräistä
    assert len(tickers) == (len(INDEX_WATCHLIST) + len(COMMODITY_WATCHLIST)
                            + len(CRYPTO_WATCHLIST) + len(THEME_WATCHLIST) - 1)
    assert "CL=F" in tickers
    assert tickers[0] == "^DJI" and tickers[-1] == "EPOL"


def test_upgrade_from_v3_adds_only_commodities(tmp_path):
    import sqlite3

    from lppls_app.config import COMMODITY_WATCHLIST, CRYPTO_WATCHLIST, THEME_WATCHLIST

    db = tmp_path / "v3.db"
    s = Storage(db, seed_watchlist=False)
    s.add_ticker("^GSPC")
    s.add_ticker("GC=F", "Kulta")
    s.close()
    con = sqlite3.connect(db)
    con.execute("PRAGMA user_version=3")
    con.commit()
    con.close()

    tickers = [r["ticker"] for r in Storage(db).list_watchlist()]
    assert "^DJI" not in tickers  # indeksejä ei lisätä uudelleen v3-kantaan
    # ^GSPC + raaka-aineet (GC=F jo oli) + kryptot + teemat
    assert len(tickers) == (1 + len(COMMODITY_WATCHLIST) + len(CRYPTO_WATCHLIST)
                            + len(THEME_WATCHLIST))
    assert "SOL-USD" in tickers
