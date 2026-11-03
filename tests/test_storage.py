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
    # havaitsemispäivän conf-arvot tulevat skannauksesta
    assert b["conf_pos"] == pytest.approx(detected.conf_pos)
    assert b["conf_neg"] == pytest.approx(detected.conf_neg)
    assert store.list_bubbles()[0]["conf_pos"] == pytest.approx(detected.conf_pos)
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


def test_upgrade_from_v6_adds_quantum_etf(tmp_path):
    import sqlite3

    db = tmp_path / "v6.db"
    s = Storage(db)
    s.con.execute("DELETE FROM watchlist WHERE ticker='QTUM'")
    s.remove_ticker("TSLA")  # käyttäjä poisti
    s.con.execute("PRAGMA user_version=6")
    s.con.commit()
    before = len(s.list_watchlist())
    s.close()

    tickers = [r["ticker"] for r in Storage(db).list_watchlist()]
    assert "QTUM" in tickers
    assert "TSLA" not in tickers
    assert len(tickers) == before + 1  # v9-teemat olivat jo kannassa


def test_upgrade_from_v8_adds_ai_themes_only(tmp_path):
    from lppls_app.config import THEME_V9

    db = tmp_path / "v8.db"
    s = Storage(db)
    s.con.executemany("DELETE FROM watchlist WHERE ticker=?", [(t,) for t in THEME_V9])
    s.remove_ticker("NVDA")  # käyttäjä poisti
    s.con.execute("PRAGMA user_version=8")
    s.con.commit()
    before = len(s.list_watchlist())
    s.close()

    tickers = [r["ticker"] for r in Storage(db).list_watchlist()]
    assert "CHAT" in tickers and "NVDA" not in tickers
    assert len(tickers) == before + len(THEME_V9)


def test_save_dual_and_confidence_history(store, cfg):
    from lppls_app.scanner import scan_both

    dual = scan_both("SYN", synthetic_bubble(), "2020-06-01", cfg)
    bid = store.save_dual(dual, is_test=True)
    b = store.get_bubble(bid)
    assert b["method"] == dual.method
    assert b["conf_pos"] == pytest.approx(dual.long.conf_pos)
    assert b["conf_pos_l"] == pytest.approx(dual.short.conf_pos)
    assert b["move_l"] == pytest.approx(dual.short.change)

    # Uusi ajo samalle päivälle korvaa pisteen, eri päivä lisää uuden
    store.save_scan(dual.short)
    later = scan_series("SYN", synthetic_bubble(), "2020-05-15", cfg.short())
    store.save_scan(later)
    hist = store.confidence_history("SYN", "L", "pos")
    assert list(hist.index) == [pd.Timestamp("2020-05-15"), pd.Timestamp("2020-06-01")]
    assert hist.iloc[0] == pytest.approx(later.conf_pos)
    assert len(store.confidence_history("SYN", "P", "pos")) == 1
    assert store.has_scan("SYN", "2020-06-01", "L") and not store.has_scan("SYN", "2020-06-02", "L")


def test_methods_merge_on_duplicate(store, detected):
    a = store.save_bubble(detected, store.save_scan(detected), is_test=False)
    b = store.save_bubble(detected, store.save_scan(detected), is_test=False, method="L")
    assert a == b and store.get_bubble(a)["method"] == "P+L"


def test_upgrade_from_v7_adds_method_columns(tmp_path):
    import sqlite3

    db = tmp_path / "v7.db"
    con = sqlite3.connect(db)
    # v7-skeeman scans- ja bubbles-taulut ilman uusia sarakkeita
    con.executescript("""
        CREATE TABLE scans (id INTEGER PRIMARY KEY, ticker TEXT, as_of TEXT, run_at TEXT,
            conf_pos REAL, conf_neg REAL, tc_median TEXT, tc_p10 TEXT, tc_p90 TEXT, move REAL);
        CREATE TABLE bubbles (id INTEGER PRIMARY KEY, ticker TEXT, scan_id INTEGER,
            detected_as_of TEXT, is_test INTEGER, sign TEXT, confidence REAL,
            tc TEXT, tc_years REAL, tc_p10 TEXT, tc_p90 TEXT, window_start TEXT,
            m REAL, omega REAL, A REAL, B REAL, C1 REAL, C2 REAL, r2 REAL,
            status TEXT DEFAULT 'odottaa', actual_peak_date TEXT, actual_peak_price REAL,
            max_drawdown REAL, last_updated TEXT, tracking INTEGER DEFAULT 1, note TEXT, move REAL);
        INSERT INTO scans VALUES (1, 'X', '2026-10-01', '2026-10-01T10:00', 0.2, 0, NULL, NULL, NULL, 1.5);
        INSERT INTO bubbles(id, ticker, scan_id, detected_as_of, is_test, sign, confidence, tc)
            VALUES (1, 'X', 1, '2026-10-01', 0, 'pos', 0.2, '2026-12-01');
        PRAGMA user_version=7;""")
    con.close()
    s = Storage(db)
    b = s.get_bubble(1)
    assert b["method"] == "P" and b["conf_pos"] == pytest.approx(0.2)
    assert b["conf_pos_l"] is None and b["move_p"] == pytest.approx(1.5)
    assert len(s.confidence_history("X", "P", "pos")) == 1


def test_ticker_names(store):
    store.add_ticker("OMA", "Oma nimi")
    store.add_ticker("TYHJA")
    store.remove_ticker("OMA")  # poistetunkin nimi löytyy tallennetuille kuplille
    names = store.ticker_names()
    assert names["OMA"] == "Oma nimi"
    assert "TYHJA" not in names
    assert names["QTUM"].startswith("Kvanttilaskenta")  # oletuslistalta
