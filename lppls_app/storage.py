"""SQLite-tallennus: seurantalista, hintavälimuisti, skannaukset, kuplat ja seuranta."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from .config import (COMMODITY_WATCHLIST, CRYPTO_WATCHLIST, DEFAULT_WATCHLIST, INDEX_WATCHLIST,
                     THEME_V9, THEME_WATCHLIST)
from .model import from_years
from .scanner import DualScan, ScanResult

SCHEMA_VERSION = 9  # 2: 75 indeksiä, 3: move-sarake, 4: 39 raaka-ainetta, 5: 40 kryptoa,
                    # 6: 40 teemaa/osaketta/sektoria, 7: kvanttilaskenta (QTUM),
                    # 8: lyhyt menetelmä (method-sarakkeet, scan_id_l),
                    # 9: 25 tekoäly- ja teemarahastoa

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY, name TEXT, added TEXT, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS price_cache (
    ticker TEXT, date TEXT, price REAL, fetched_at TEXT, PRIMARY KEY (ticker, date));
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY, ticker TEXT, as_of TEXT, run_at TEXT,
    conf_pos REAL, conf_neg REAL, tc_median TEXT, tc_p10 TEXT, tc_p90 TEXT, move REAL,
    method TEXT DEFAULT 'P');
CREATE TABLE IF NOT EXISTS bubbles (
    id INTEGER PRIMARY KEY, ticker TEXT, scan_id INTEGER REFERENCES scans(id),
    detected_as_of TEXT, is_test INTEGER, sign TEXT, confidence REAL,
    tc TEXT, tc_years REAL, tc_p10 TEXT, tc_p90 TEXT, window_start TEXT,
    m REAL, omega REAL, A REAL, B REAL, C1 REAL, C2 REAL, r2 REAL,
    status TEXT DEFAULT 'odottaa', actual_peak_date TEXT, actual_peak_price REAL,
    max_drawdown REAL, last_updated TEXT, tracking INTEGER DEFAULT 1, note TEXT,
    move REAL, method TEXT DEFAULT 'P', scan_id_l INTEGER REFERENCES scans(id));
CREATE TABLE IF NOT EXISTS bubble_prices (
    bubble_id INTEGER REFERENCES bubbles(id) ON DELETE CASCADE,
    date TEXT, price REAL, PRIMARY KEY (bubble_id, date));
CREATE TABLE IF NOT EXISTS tracked_prices (
    ticker TEXT, date TEXT, price REAL, PRIMARY KEY (ticker, date));
"""


def _d(ts) -> str | None:
    return None if ts is None else pd.Timestamp(ts).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Storage:
    def __init__(self, path: str | Path = ":memory:", seed_watchlist: bool = True):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.con = sqlite3.connect(self.path, timeout=30)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA foreign_keys=ON")
        version = self.con.execute("PRAGMA user_version").fetchone()[0]
        self.con.executescript(SCHEMA)
        # Vanhoihin tauluihin puuttuvat sarakkeet (v3: move, v8: method ja scan_id_l)
        added = [("scans", "move", "REAL"), ("bubbles", "move", "REAL"),
                 ("scans", "method", "TEXT DEFAULT 'P'"), ("bubbles", "method", "TEXT DEFAULT 'P'"),
                 ("bubbles", "scan_id_l", "INTEGER REFERENCES scans(id)")]
        for table, col, decl in added:
            cols = {r[1] for r in self.con.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self.con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        if seed_watchlist and version < SCHEMA_VERSION:
            # Uusi kanta saa koko oletuslistan; vanhaan lisätään vain sen jälkeen tulleet
            # tunnukset, eikä käyttäjän poistamia palauteta
            if version == 0:
                seed = DEFAULT_WATCHLIST
            else:
                seed = (INDEX_WATCHLIST if version < 2 else []) + \
                       (COMMODITY_WATCHLIST if version < 4 else []) + \
                       (CRYPTO_WATCHLIST if version < 5 else []) + \
                       (THEME_WATCHLIST if version < 7 else  # v7: +QTUM; muut ohitetaan
                        [x for x in THEME_WATCHLIST if x[0] in THEME_V9] if version < 9 else [])
            self.con.executemany(
                "INSERT INTO watchlist(ticker, name, added, active) VALUES (?,?,?,1) "
                "ON CONFLICT(ticker) DO NOTHING",
                [(t, n, _now()) for t, n in seed])
        self.con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        self.con.commit()

    def close(self):
        self.con.close()

    # --- seurantalista ---
    def list_watchlist(self) -> list[sqlite3.Row]:
        """Oletuslistan tunnukset sen järjestyksessä, käyttäjän lisäämät perässä."""
        rows = self.con.execute(
            "SELECT rowid AS pos, * FROM watchlist WHERE active=1").fetchall()
        order = {t: i for i, (t, _) in enumerate(DEFAULT_WATCHLIST)}
        return sorted(rows, key=lambda r: (order.get(r["ticker"], len(order)), r["pos"]))

    def add_ticker(self, ticker: str, name: str = ""):
        self.con.execute(
            "INSERT INTO watchlist(ticker, name, added, active) VALUES (?,?,?,1) "
            "ON CONFLICT(ticker) DO UPDATE SET active=1", (ticker, name, _now()))
        self.con.commit()

    def ticker_names(self) -> dict[str, str]:
        """Tunnus → nimi: seurantalistalta (myös poistetut), puuttuvat oletuslistalta."""
        names = {t: n for t, n in DEFAULT_WATCHLIST}
        names.update({r["ticker"]: r["name"] for r in self.con.execute(
            "SELECT ticker, name FROM watchlist WHERE name IS NOT NULL AND name != ''")})
        return names

    def remove_ticker(self, ticker: str):
        self.con.execute("UPDATE watchlist SET active=0 WHERE ticker=?", (ticker,))
        self.con.commit()

    # --- hintavälimuisti ---
    def load_cache(self, ticker: str, start, end) -> tuple[pd.Series, datetime | None]:
        rows = self.con.execute(
            "SELECT date, price, fetched_at FROM price_cache "
            "WHERE ticker=? AND date BETWEEN ? AND ? ORDER BY date",
            (ticker, _d(start), _d(end))).fetchall()
        s = pd.Series([r["price"] for r in rows],
                      index=pd.DatetimeIndex([r["date"] for r in rows]), dtype=float)
        fetched = max((r["fetched_at"] for r in rows), default=None)
        return s, (datetime.fromisoformat(fetched) if fetched else None)

    def save_cache(self, ticker: str, series: pd.Series):
        now = _now()
        self.con.executemany(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?,?,?)",
            [(ticker, _d(d), float(p), now) for d, p in series.items()])
        self.con.commit()

    # --- skannaukset ja kuplat ---
    def save_scan(self, sr: ScanResult) -> int:
        cur = self.con.execute(
            "INSERT INTO scans(ticker, as_of, run_at, conf_pos, conf_neg, tc_median, tc_p10, tc_p90, "
            "move, method) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (sr.ticker, _d(sr.as_of), _now(), sr.conf_pos, sr.conf_neg,
             _d(sr.tc_median), _d(sr.tc_p10), _d(sr.tc_p90), sr.change, sr.method))
        self.con.commit()
        return cur.lastrowid

    def save_dual(self, dual: DualScan, is_test: bool) -> int | None:
        """Tallentaa molemmat skannaukset ja kuplan, jos kumpi tahansa menetelmä havaitsi sen."""
        scan_p, scan_l = self.save_scan(dual.long), self.save_scan(dual.short)
        if not dual.detected:
            return None
        return self.save_bubble(dual.primary, scan_p, is_test, method=dual.method, scan_id_l=scan_l)

    def save_bubble(self, sr: ScanResult, scan_id: int, is_test: bool,
                    method: str | None = None, scan_id_l: int | None = None) -> int:
        """Tallentaa havaitun kuplan; sama tunnus + merkki + tc ±5 pv päivittää vanhan.

        scan_id on pitkän ja scan_id_l lyhyen menetelmän skannaus (C P / C L havaitessa).
        """
        b = sr.best
        tc = sr.tc_median
        method = method or sr.method
        dup = self.con.execute(
            "SELECT id, method FROM bubbles WHERE ticker=? AND sign=? AND is_test=? AND tracking=1 "
            "AND ABS(julianday(tc) - julianday(?)) <= 5",
            (sr.ticker, sr.sign, int(is_test), _d(tc))).fetchone()
        if dup:  # menetelmät yhdistetään: aiemmin P, nyt L → P+L
            used = set((dup["method"] or "P").split("+")) | set(method.split("+"))
            method = "+".join(m for m in ("P", "L") if m in used)
        values = dict(
            ticker=sr.ticker, scan_id=scan_id, detected_as_of=_d(sr.as_of), is_test=int(is_test),
            sign=sr.sign, confidence=sr.confidence, tc=_d(tc), tc_years=b.tc,
            tc_p10=_d(sr.tc_p10), tc_p90=_d(sr.tc_p90),
            window_start=_d(from_years(b.t1)),
            m=b.m, omega=b.omega, A=b.A, B=b.B, C1=b.C1, C2=b.C2, r2=b.r2, move=sr.change,
            last_updated=_now(), method=method, scan_id_l=scan_id_l,
        )
        if dup:
            bubble_id = dup["id"]
            sets = ", ".join(f"{k}=?" for k in values)
            self.con.execute(f"UPDATE bubbles SET {sets}, status='odottaa' WHERE id=?",
                             (*values.values(), bubble_id))
            self.con.execute("DELETE FROM bubble_prices WHERE bubble_id=?", (bubble_id,))
        else:
            cols = ", ".join(values)
            marks = ", ".join("?" for _ in values)
            bubble_id = self.con.execute(
                f"INSERT INTO bubbles({cols}) VALUES ({marks})", tuple(values.values())).lastrowid
        self.con.executemany(
            "INSERT INTO bubble_prices VALUES (?,?,?)",
            [(bubble_id, _d(d), float(p)) for d, p in sr.series.items()])
        self.con.commit()
        return bubble_id

    # Havaitsemispäivän conf+/conf− tulevat kuplan skannauksista (s = pitkä, sl = lyhyt);
    # ilman pitkän skannauksen riviä käytetään kuplan omaa confidencea sen suunnan mukaan.
    # Ennen lyhyttä menetelmää tallennetuilla kuplilla C L -arvot ovat NULL.
    _BUBBLE_SELECT = """
        SELECT b.*,
               COALESCE(s.conf_pos, CASE WHEN b.sign = 'neg' THEN 0 ELSE b.confidence END) AS conf_pos,
               COALESCE(s.conf_neg, CASE WHEN b.sign = 'neg' THEN b.confidence ELSE 0 END) AS conf_neg,
               COALESCE(s.move, b.move) AS move_p,
               sl.conf_pos AS conf_pos_l, sl.conf_neg AS conf_neg_l, sl.move AS move_l
        FROM bubbles b LEFT JOIN scans s ON s.id = b.scan_id
                       LEFT JOIN scans sl ON sl.id = b.scan_id_l"""

    def list_bubbles(self) -> list[sqlite3.Row]:
        return self.con.execute(
            self._BUBBLE_SELECT + " ORDER BY b.detected_as_of DESC, b.id DESC").fetchall()

    def get_bubble(self, bubble_id: int) -> sqlite3.Row | None:
        return self.con.execute(self._BUBBLE_SELECT + " WHERE b.id=?", (bubble_id,)).fetchone()

    def bubble_prices(self, bubble_id: int) -> pd.Series:
        rows = self.con.execute(
            "SELECT date, price FROM bubble_prices WHERE bubble_id=? ORDER BY date",
            (bubble_id,)).fetchall()
        return pd.Series([r["price"] for r in rows],
                         index=pd.DatetimeIndex([r["date"] for r in rows]), dtype=float)

    def confidence_history(self, ticker: str, method: str, sign: str | None) -> pd.Series:
        """Confidence kuplan suuntaan as_of-päivittäin; samalta päivältä viimeisin ajo."""
        col = "conf_neg" if sign == "neg" else "conf_pos"
        rows = self.con.execute(
            f"SELECT as_of, {col} AS conf FROM scans WHERE ticker=? AND COALESCE(method, 'P')=? "
            "ORDER BY as_of, run_at, id", (ticker, method)).fetchall()
        latest = {r["as_of"]: r["conf"] for r in rows}
        return pd.Series(list(latest.values()), index=pd.DatetimeIndex(list(latest)), dtype=float)

    def has_scan(self, ticker: str, as_of, method: str) -> bool:
        return self.con.execute(
            "SELECT 1 FROM scans WHERE ticker=? AND as_of=? AND COALESCE(method, 'P')=? LIMIT 1",
            (ticker, _d(as_of), method)).fetchone() is not None

    def delete_bubble(self, bubble_id: int):
        self.con.execute("DELETE FROM bubbles WHERE id=?", (bubble_id,))
        self.con.commit()

    def set_tracking(self, bubble_id: int, active: bool):
        self.con.execute("UPDATE bubbles SET tracking=? WHERE id=?", (int(active), bubble_id))
        self.con.commit()

    def update_outcome(self, bubble_id: int, status: str, peak_date, peak_price, drawdown):
        self.con.execute(
            "UPDATE bubbles SET status=?, actual_peak_date=?, actual_peak_price=?, "
            "max_drawdown=?, last_updated=? WHERE id=?",
            (status, _d(peak_date), peak_price, drawdown, _now(), bubble_id))
        self.con.commit()

    # --- seurantasarjat ---
    def tracked_tickers(self) -> list[str]:
        return [r[0] for r in self.con.execute(
            "SELECT DISTINCT ticker FROM bubbles WHERE tracking=1 ORDER BY ticker")]

    def add_tracked_prices(self, ticker: str, series: pd.Series) -> int:
        before = self.con.total_changes
        self.con.executemany(
            "INSERT OR IGNORE INTO tracked_prices VALUES (?,?,?)",
            [(ticker, _d(d), float(p)) for d, p in series.items()])
        self.con.commit()
        return self.con.total_changes - before

    def tracked_prices(self, ticker: str, after=None) -> pd.Series:
        rows = self.con.execute(
            "SELECT date, price FROM tracked_prices WHERE ticker=? AND date > ? ORDER BY date",
            (ticker, _d(after) or "")).fetchall()
        return pd.Series([r["price"] for r in rows],
                         index=pd.DatetimeIndex([r["date"] for r in rows]), dtype=float)
