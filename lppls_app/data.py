"""Hintadatan haku Yahoo Financesta välimuistin kautta sekä CSV-tuonti."""
from __future__ import annotations

import warnings
from datetime import datetime, timedelta

import pandas as pd


class DataError(Exception):
    pass


class NoDataError(DataError):
    """Väliltä ei löytynyt yhtään kurssia (esim. viikonloppu tai väärä tunnus)."""


def fetch_yahoo(ticker: str, start, end) -> pd.Series:
    """Päivittäiset päätöskurssit väliltä [start, end]."""
    import yfinance as yf

    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    try:
        with warnings.catch_warnings():  # yfinance:n pandas-varoitukset pois
            warnings.simplefilter("ignore")
            df = yf.Ticker(ticker).history(start=start, end=end + pd.Timedelta(days=1),
                                           interval="1d", auto_adjust=True)
    except Exception as e:  # yfinance heittää monenlaisia virheitä
        raise DataError(f"{ticker}: haku epäonnistui ({e})") from e
    if df is None or df.empty or "Close" not in df:
        raise NoDataError(f"{ticker}: ei dataa välillä {start:%Y-%m-%d} – {end:%Y-%m-%d}")
    s = df["Close"].dropna()
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    s.index = idx.normalize()
    s = s[~s.index.duplicated(keep="last")]
    s.name = ticker
    return s.astype(float)


def _cache_covers(s: pd.Series, fetched_at: datetime | None, start, end,
                  max_age: timedelta) -> bool:
    if s.empty or fetched_at is None:
        return False
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if s.index[0] > start + pd.Timedelta(days=10):
        return False
    historical = end < pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    if historical:  # mennyt data ei muutu
        return s.index[-1] >= end - pd.Timedelta(days=10)
    return datetime.now() - fetched_at < max_age


def get_prices(storage, ticker: str, start, end, max_age_hours: float = 24.0,
               fetch=fetch_yahoo) -> pd.Series:
    cached, fetched_at = storage.load_cache(ticker, start, end)
    if _cache_covers(cached, fetched_at, start, end, timedelta(hours=max_age_hours)):
        return cached
    s = fetch(ticker, start, end)
    storage.save_cache(ticker, s)
    return s


def load_csv(path) -> pd.Series:
    """CSV: ensimmäinen sarake päivämäärä, hinnaksi 'close'/'price'/'hinta' tai toinen sarake."""
    df = pd.read_csv(path)
    if df.shape[1] < 2:
        raise DataError("CSV:ssä pitää olla vähintään päivämäärä- ja hintasarake")
    cols = {c.lower(): c for c in df.columns}
    price_col = next((cols[k] for k in ("adj close", "close", "price", "hinta") if k in cols),
                     df.columns[1])
    s = pd.Series(pd.to_numeric(df[price_col], errors="coerce").to_numpy(),
                  index=pd.to_datetime(df.iloc[:, 0], errors="coerce"))
    s = s[s.index.notna()].dropna().sort_index()
    s = s[s > 0]
    if s.empty:
        raise DataError("CSV:stä ei löytynyt kelvollisia hintoja")
    return s
