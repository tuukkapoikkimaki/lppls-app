"""Havaittujen kuplien seuranta: jatkodatan haku ja toteuman arviointi."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .config import Config
from .data import DataError, NoDataError, fetch_yahoo, get_prices
from .scanner import scan_both

PENDING, HIT, MISS = "odottaa", "toteutui", "ei toteutunut"


@dataclass
class Outcome:
    status: str
    peak_date: pd.Timestamp | None = None
    peak_price: float | None = None
    drawdown: float | None = None  # pos: pudotus huipusta, neg: nousu pohjasta


@dataclass
class UpdateSummary:
    updated: list[str] = field(default_factory=list)
    new_rows: int = 0
    rescanned: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        msg = f"{len(self.updated)} sarjaa päivitetty, {self.new_rows} uutta päivää"
        if self.rescanned:
            msg += f", {len(self.rescanned)} tunnusta skannattu (C P ja C L)"
        if self.errors:
            msg += f", {len(self.errors)} virhettä: " + "; ".join(
                f"{t}: {e}" for t, e in self.errors.items())
        return msg


def tolerance(bubble, cfg: Config) -> tuple[pd.Timestamp, pd.Timestamp]:
    tc = pd.Timestamp(bubble["tc"])
    pad = pd.Timedelta(days=cfg.min_tolerance_days)
    lo = min(pd.Timestamp(bubble["tc_p10"] or tc), tc - pad)
    hi = max(pd.Timestamp(bubble["tc_p90"] or tc), tc + pad)
    return lo, hi


def find_turn(prices: pd.Series, pos: bool, threshold: float) -> pd.Timestamp | None:
    """Ensimmäinen käänne: huippu, jonka jälkeen hinta on laskenut threshold verran
    siihenastisesta huipusta (antikuplalla pohja, josta hinta on noussut threshold verran).
    """
    if prices.empty:
        return None
    if pos:
        move = 1.0 - prices / prices.cummax()
    else:
        move = prices / prices.cummin() - 1.0
    hit = move[move >= threshold - 1e-12]
    if hit.empty:
        return None
    before = prices[prices.index <= hit.index[0]]
    return before.idxmax() if pos else before.idxmin()


def evaluate_outcome(bubble, prices: pd.Series, today, cfg: Config) -> Outcome:
    """Vertaa jäädytettyä ennustetta toteutuneisiin hintoihin.

    Toteutunut käänne on havainnon jälkeinen ensimmäinen huippu, josta hinta on pudonnut
    turn_threshold (5 %) verran (antikuplalla pohja, josta noussut 5 %). Kupla toteutuu, jos
    käänne osuu viimeistään toleranssivälin loppuun ja sitä seuraa vähintään
    crash_threshold-suuruinen pudotus (antikuplalla nousu) crash_window_days-päivän sisällä.
    """
    today = pd.Timestamp(today).normalize()
    _, hi = tolerance(bubble, cfg)
    pos = bubble["sign"] != "neg"
    # Aikainen käänne näkyy negatiivisena erona tc:hen
    seg = prices[prices.index > pd.Timestamp(bubble["detected_as_of"])]
    peak_date = find_turn(seg, pos, cfg.turn_threshold)
    if peak_date is None:
        return Outcome(PENDING if today <= hi else MISS)
    peak = float(seg[peak_date])
    after = prices[(prices.index > peak_date)
                   & (prices.index <= peak_date + pd.Timedelta(days=cfg.crash_window_days))]
    if after.empty:
        move = 0.0
    elif pos:
        move = 1.0 - float(after.min()) / peak
    else:
        move = float(after.max()) / peak - 1.0

    if peak_date > hi:  # käänne tuli vasta ennustevälin jälkeen
        status = MISS
    elif move >= cfg.crash_threshold:
        status = HIT
    elif today <= peak_date + pd.Timedelta(days=cfg.crash_window_days):
        status = PENDING  # pudotus voi vielä syventyä
    else:
        status = MISS
    return Outcome(status, peak_date, peak, move)


def bubble_series(storage, bubble) -> pd.Series:
    """Jäädytetty tilannekuva + havainnon jälkeinen seurantadata."""
    snap = storage.bubble_prices(bubble["id"])
    follow = storage.tracked_prices(bubble["ticker"], after=bubble["detected_as_of"])
    return pd.concat([snap, follow]).sort_index().pipe(lambda s: s[~s.index.duplicated()])


def update_all(storage, cfg: Config, today=None, fetch=fetch_yahoo,
               progress=None) -> UpdateSummary:
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    summary = UpdateSummary()
    bubbles = [b for b in storage.list_bubbles() if b["tracking"]]
    tickers = sorted({b["ticker"] for b in bubbles})
    for i, ticker in enumerate(tickers, 1):
        first = min(pd.Timestamp(b["detected_as_of"]) for b in bubbles if b["ticker"] == ticker)
        have = storage.tracked_prices(ticker, after=first)
        # Aukoton jatkosarja havainnosta eteenpäin; muuten haetaan alusta (esim. uusi testikupla)
        if not have.empty and have.index[0] <= first + pd.Timedelta(days=7):
            start = have.index[-1] + pd.Timedelta(days=1)
        else:
            start = first + pd.Timedelta(days=1)
        if start <= today:
            try:
                summary.new_rows += storage.add_tracked_prices(ticker, fetch(ticker, start, today))
                summary.updated.append(ticker)
            except NoDataError:
                if start < today - pd.Timedelta(days=7):  # tuore väli voi olla tyhjä
                    summary.errors[ticker] = "ei uutta dataa"
            except DataError as e:
                summary.errors[ticker] = str(e)
        if progress:
            progress(i, len(tickers))

    for b in bubbles:
        o = evaluate_outcome(b, bubble_series(storage, b), today, cfg)
        storage.update_outcome(b["id"], o.status, o.peak_date, o.peak_price, o.drawdown)
    return summary


def rescan_tracked(storage, cfg: Config, summary: UpdateSummary, executor=None, today=None,
                   progress=None, stop=lambda: False, scan=scan_both, prices=get_prices) -> None:
    """Ajaa pitkän ja lyhyen skannauksen seurattaville tunnuksille tälle päivälle.

    Tallentaa vain skannausrivit (confidence-historia); kuplia ei tallenneta tai päivitetä
    tästä, vaan Skanneri-välilehdeltä. Jo tänään skannatut tunnukset ohitetaan.
    """
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    tickers = [t for t in storage.tracked_tickers()
               if not (storage.has_scan(t, today, "P") and storage.has_scan(t, today, "L"))]
    for i, ticker in enumerate(tickers):
        if stop():
            break
        try:
            series = prices(storage, ticker, today - pd.Timedelta(days=cfg.lookback_days), today,
                            cfg.cache_max_age_hours)
            dual = scan(ticker, series, today, cfg, executor,
                        (lambda d, t, i=i, ticker=ticker: progress(
                            i * 100 + d * 100 // t, len(tickers) * 100,
                            f"Skannataan {ticker} ({i + 1}/{len(tickers)})")) if progress else None)
        except Exception as e:  # yksi virhe ei katkaise muita
            summary.errors[ticker] = f"skannaus: {e}"
            continue
        storage.save_scan(dual.long)
        storage.save_scan(dual.short)
        summary.rescanned.append(ticker)
