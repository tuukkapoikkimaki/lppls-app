"""Sovelluksen asetukset: polut, ikkunat ja kynnysarvot."""
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


def default_db_path() -> Path:
    env = os.environ.get("LPPLS_DB")
    if env:
        return Path(env)
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "lppls-app" / "bubbles.db"


# 75 yleisintä osakeindeksiä; kaikki tarkistettu Yahoo Financesta (5 v päivädataa) 31.10.2026
INDEX_WATCHLIST = [
    # Yhdysvallat
    ("^GSPC", "S&P 500"),
    ("^DJI", "Dow Jones Industrial Average"),
    ("^IXIC", "Nasdaq Composite"),
    ("^NDX", "Nasdaq 100"),
    ("^RUT", "Russell 2000"),
    ("^RUI", "Russell 1000"),
    ("^RUA", "Russell 3000"),
    ("^NYA", "NYSE Composite"),
    ("^W5000", "Wilshire 5000"),
    ("^DWCF", "Dow Jones U.S. Total Stock Market"),
    ("^OEX", "S&P 100"),
    ("^SPXEW", "S&P 500 Equal Weight"),
    ("^SP400", "S&P MidCap 400"),
    ("^SP600", "S&P SmallCap 600"),
    ("^SOX", "PHLX Semiconductor"),
    ("^NDXT", "Nasdaq 100 Technology"),
    ("^NYFANG", "NYSE FANG+"),
    ("^NBI", "Nasdaq Biotechnology"),
    ("^BKX", "KBW Bank"),
    ("^DJT", "Dow Jones Transportation"),
    ("^DJU", "Dow Jones Utilities"),
    ("^XAU", "Philadelphia Gold & Silver"),
    # Amerikka muut
    ("^GSPTSE", "S&P/TSX Composite (Kanada)"),
    ("^MXX", "IPC (Meksiko)"),
    ("^BVSP", "Ibovespa (Brasilia)"),
    # Eurooppa
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^STOXX", "Stoxx Europe 600"),
    ("^N100", "Euronext 100"),
    ("^FTSE", "FTSE 100 (UK)"),
    ("^FTMC", "FTSE 250 (UK)"),
    ("^FTAS", "FTSE All-Share (UK)"),
    ("^GDAXI", "DAX (Saksa)"),
    ("^MDAXI", "MDAX (Saksa)"),
    ("^SDAXI", "SDAX (Saksa)"),
    ("^TECDAX", "TecDAX (Saksa)"),
    ("^FCHI", "CAC 40 (Ranska)"),
    ("^CN20", "CAC Next 20 (Ranska)"),
    ("^AEX", "AEX (Alankomaat)"),
    ("^AMX", "AMX (Alankomaat)"),
    ("^BFX", "BEL 20 (Belgia)"),
    ("^IBEX", "IBEX 35 (Espanja)"),
    ("FTSEMIB.MI", "FTSE MIB (Italia)"),
    ("^SSMI", "SMI (Sveitsi)"),
    ("^ATX", "ATX (Itävalta)"),
    ("^ISEQ", "ISEQ Overall (Irlanti)"),
    ("PSI20.LS", "PSI (Portugali)"),
    ("GD.AT", "Athens General (Kreikka)"),
    ("XU100.IS", "BIST 100 (Turkki)"),
    # Pohjoismaat
    ("^OMXH25", "OMX Helsinki 25"),
    ("^OMX", "OMX Stockholm 30"),
    ("^OMXSPI", "OMX Stockholm All-Share"),
    ("^OMXC25", "OMX Copenhagen 25"),
    # Aasia ja Tyynimeri
    ("^N225", "Nikkei 225 (Japani)"),
    ("^HSI", "Hang Seng (Hongkong)"),
    ("^HSCE", "Hang Seng China Enterprises"),
    ("000001.SS", "Shanghai Composite"),
    ("399001.SZ", "Shenzhen Component"),
    ("^TWII", "TAIEX (Taiwan)"),
    ("^KS11", "KOSPI (Etelä-Korea)"),
    ("^KQ11", "KOSDAQ (Etelä-Korea)"),
    ("^STI", "Straits Times (Singapore)"),
    ("^BSESN", "BSE Sensex (Intia)"),
    ("^NSEI", "Nifty 50 (Intia)"),
    ("^NSMIDCP", "Nifty Next 50 (Intia)"),
    ("^CRSLDX", "Nifty 500 (Intia)"),
    ("^NSEBANK", "Nifty Bank (Intia)"),
    ("^CNXIT", "Nifty IT (Intia)"),
    ("^JKSE", "Jakarta Composite (Indonesia)"),
    ("^KLSE", "FTSE Bursa Malaysia KLCI"),
    ("^AXJO", "S&P/ASX 200 (Australia)"),
    ("^AORD", "All Ordinaries (Australia)"),
    ("^NZ50", "S&P/NZX 50 (Uusi-Seelanti)"),
    # Lähi-itä ja Afrikka
    ("^TA125.TA", "TA-125 (Israel)"),
    ("^J203.JO", "FTSE/JSE All Share (Etelä-Afrikka)"),
    ("^JN0U.JO", "FTSE/JSE Top 40 (Etelä-Afrikka)"),
]

# Raaka-aineiden futuurit (jatkuva lähin sopimus) + 2 raaka-aineindeksiä; kaikki tarkistettu
# Yahoo Financesta 1.11.2026. Mini/micro-sopimukset (QM, MGC …) jätetty pois kaksoiskappaleina.
COMMODITY_WATCHLIST = [
    # Energia
    ("CL=F", "Raakaöljy WTI"),
    ("BZ=F", "Raakaöljy Brent"),
    ("NG=F", "Maakaasu Henry Hub"),
    ("TTF=F", "Maakaasu TTF (Eurooppa)"),
    ("HO=F", "Lämmitysöljy"),
    ("RB=F", "Bensiini RBOB"),
    # Jalometallit
    ("GC=F", "Kulta"),
    ("SI=F", "Hopea"),
    ("PL=F", "Platina"),
    ("PA=F", "Palladium"),
    # Teollisuusmetallit
    ("HG=F", "Kupari"),
    ("ALI=F", "Alumiini"),
    ("AUP=F", "Alumiini, Midwest-preemio"),
    ("ZNC=F", "Sinkki"),
    ("HRC=F", "Kuumavalssattu teräs"),
    ("TIO=F", "Rautamalmi"),
    # Viljat ja öljykasvit
    ("ZC=F", "Maissi"),
    ("ZW=F", "Vehnä (Chicago)"),
    ("KE=F", "Vehnä (Kansas City)"),
    ("ZS=F", "Soijapapu"),
    ("ZM=F", "Soijarouhe"),
    ("ZL=F", "Soijaöljy"),
    ("ZO=F", "Kaura"),
    ("ZR=F", "Riisi"),
    # Pehmeät raaka-aineet
    ("KC=F", "Kahvi"),
    ("CC=F", "Kaakao"),
    ("SB=F", "Sokeri"),
    ("CT=F", "Puuvilla"),
    ("OJ=F", "Appelsiinimehu"),
    ("LBR=F", "Sahatavara"),
    # Karja ja maitotuotteet
    ("LE=F", "Elävä nauta"),
    ("GF=F", "Syöttönauta"),
    ("HE=F", "Lihasika"),
    ("DC=F", "Maito (Class III)"),
    ("DY=F", "Kuivattu hera"),
    ("CSC=F", "Juusto"),
    ("CB=F", "Voi"),
    # Raaka-aineindeksit
    ("^SPGSCI", "S&P GSCI -raaka-aineindeksi"),
    ("GD=F", "S&P GSCI -futuuri"),
]

# 40 suurinta kryptovaluuttaa markkina-arvon mukaan (Yahoo Finance 1.11.2026), ilman
# stablecoineja (USDT, USDC …), joiden hinta on sidottu dollariin. TON puuttuu: Yahoo ei anna historiaa.
CRYPTO_WATCHLIST = [
    ("BTC-USD", "Bitcoin"),
    ("ETH-USD", "Ethereum"),
    ("BNB-USD", "BNB"),
    ("XRP-USD", "XRP"),
    ("SOL-USD", "Solana"),
    ("TRX-USD", "TRON"),
    ("HYPE32196-USD", "Hyperliquid"),
    ("ZEC-USD", "Zcash"),
    ("DOGE-USD", "Dogecoin"),
    ("XMR-USD", "Monero"),
    ("LINK-USD", "Chainlink"),
    ("LEO-USD", "UNUS SED LEO (LEO)"),
    ("ADA-USD", "Cardano"),
    ("XLM-USD", "Stellar"),
    ("NEAR-USD", "NEAR Protocol"),
    ("BCH-USD", "Bitcoin Cash"),
    ("UNI7083-USD", "Uniswap"),
    ("LTC-USD", "Litecoin"),
    ("AVAX-USD", "Avalanche"),
    ("SUI20947-USD", "Sui"),
    ("HBAR-USD", "Hedera"),
    ("SHIB-USD", "Shiba Inu"),
    ("TAO22974-USD", "Bittensor"),
    ("CRO-USD", "Cronos"),
    ("ENA-USD", "Ethena"),
    ("QNT-USD", "Quant"),
    ("OKB-USD", "OKB"),
    ("AAVE-USD", "Aave"),
    ("PEPE24478-USD", "Pepe"),
    ("ONDO-USD", "Ondo"),
    ("DOT-USD", "Polkadot"),
    ("MNT27075-USD", "Mantle"),
    ("WLD-USD", "Worldcoin"),
    ("ICP-USD", "Internet Computer"),
    ("ETC-USD", "Ethereum Classic"),
    ("ARB11841-USD", "Arbitrum"),
    ("POL28321-USD", "Polygon (POL)"),
    ("KAS-USD", "Kaspa"),
    ("ALGO-USD", "Algorand"),
    ("JUP29210-USD", "Jupiter"),
]

# Kuplille alttiit teemat, osakkeet, sektorit, asuntomarkkina ja maat (tarkistettu Yahoosta 1.11.2026)
THEME_WATCHLIST = [
    # Teemarahastot
    ("SMH", "Puolijohteet (VanEck)"),
    ("SOXX", "Puolijohteet (iShares)"),
    ("BOTZ", "Robotiikka ja tekoäly"),
    ("AIQ", "Tekoäly ja teknologia"),
    ("ARKK", "ARK Innovation"),
    ("URA", "Uraani"),
    ("URNM", "Uraanikaivosyhtiöt"),
    ("ICLN", "Puhdas energia"),
    ("TAN", "Aurinkoenergia"),
    ("LIT", "Litium ja akut"),
    ("KWEB", "Kiinan internetyhtiöt"),
    ("BITQ", "Kryptoalan yhtiöt"),
    ("WGMI", "Bitcoin-louhijat"),
    ("GDX", "Kultakaivosyhtiöt"),
    ("GDXJ", "Pienet kultakaivosyhtiöt"),
    ("ITA", "Puolustus ja ilmailu (iShares)"),
    ("XAR", "Puolustus ja ilmailu (SPDR)"),
    ("QTUM", "Kvanttilaskenta (Defiance Quantum ETF)"),
    # v9: tekoäly ja muut teemat
    ("CHAT", "Generatiivinen tekoäly (Roundhill)"),
    ("ARTY", "Tekoäly ja teknologia (iShares Future AI & Tech)"),
    ("IGPT", "Tekoäly ja ohjelmistot (Invesco)"),
    ("THNQ", "Tekoäly (ROBO Global)"),
    ("WTAI", "Tekoäly ja innovaatio (WisdomTree)"),
    ("ROBO", "Robotiikka ja automaatio (ROBO Global)"),
    ("DTCR", "Datakeskukset ja digitaalinen infra"),
    ("IGV", "Ohjelmistoyhtiöt (iShares)"),
    ("SKYY", "Pilvipalvelut"),
    ("CIBR", "Kyberturvallisuus"),
    ("GRID", "Sähköverkot ja älyverkko"),
    ("NLR", "Ydinvoima ja uraani (VanEck)"),
    ("REMX", "Harvinaiset maametallit"),
    ("COPX", "Kuparikaivosyhtiöt"),
    ("SIL", "Hopeakaivosyhtiöt"),
    ("UFO", "Avaruusteollisuus"),
    ("ARKX", "Avaruus ja puolustus (ARK)"),
    ("ARKG", "Genomiikka (ARK)"),
    ("XBI", "Bioteknologia (SPDR)"),
    ("FINX", "Fintech"),
    ("BLOK", "Lohkoketjuyhtiöt"),
    ("DRIV", "Sähkö- ja itseohjautuvat autot"),
    ("PAVE", "USA:n infrastruktuuri"),
    ("IPO", "Listautumisannit (Renaissance IPO)"),
    ("MSOS", "Kannabis (USA)"),
    # Momentum-osakkeet
    ("NVDA", "NVIDIA"),
    ("AMD", "AMD"),
    ("AVGO", "Broadcom"),
    ("ARM", "Arm Holdings"),
    ("SMCI", "Super Micro Computer"),
    ("TSM", "TSMC"),
    ("TSLA", "Tesla"),
    ("PLTR", "Palantir"),
    ("MSTR", "Strategy (MicroStrategy)"),
    ("COIN", "Coinbase"),
    # S&P 500 -sektorit
    ("XLK", "Sektori: teknologia"),
    ("XLE", "Sektori: energia"),
    ("XLF", "Sektori: rahoitus"),
    ("XLU", "Sektori: sähkö ja vesi"),
    ("XLV", "Sektori: terveys"),
    ("XLY", "Sektori: kulutustavarat"),
    # Asuntomarkkina
    ("ITB", "Asuntorakentajat (iShares)"),
    ("XHB", "Asuntorakentajat (SPDR)"),
    ("VNQ", "Kiinteistösijoitusyhtiöt (REIT)"),
    # Maat (ETF)
    ("EWZ", "Brasilia (ETF)"),
    ("VNM", "Vietnam (ETF)"),
    ("ARGT", "Argentiina (ETF)"),
    ("EPOL", "Puola (ETF)"),
]

# Skeemaversiossa 9 lisätyt teematunnukset (vanhoihin kantoihin lisätään vain nämä)
THEME_V9 = {"CHAT", "ARTY", "IGPT", "THNQ", "WTAI", "ROBO", "DTCR", "IGV", "SKYY", "CIBR", "GRID",
            "NLR", "REMX", "COPX", "SIL", "UFO", "ARKX", "ARKG", "XBI", "FINX", "BLOK", "DRIV",
            "PAVE", "IPO", "MSOS"}

DEFAULT_WATCHLIST = INDEX_WATCHLIST + COMMODITY_WATCHLIST + CRYPTO_WATCHLIST + THEME_WATCHLIST

# Historialliset testikuplat (as-of-pikavalinnat)
TEST_PRESETS = [
    ("BTC-USD", "2017-12-01", "Bitcoin 2017"),
    ("000001.SS", "2007-10-01", "Shanghai 2007"),
    ("000001.SS", "2015-06-01", "Shanghai 2015"),
]


@dataclass
class Config:
    # Datan haku
    lookback_days: int = 1550  # ~4,2 v: riittää 1008 kauppapäivän ikkunaan pyhäpäivineen
    cache_max_age_hours: float = 24.0

    # Sovitusikkunat (kauppapäiviä); kaikki päättyvät as_of-päivään.
    # Lyhin 125 kuten Zhang, Zhang & Sornette (2016); pisin ~4 v (1008), 24 tasavälistä ikkunaa.
    window_min: int = 125
    window_max: int = 1008
    window_count: int = 24
    n_starts: int = 10
    tc_max_frac: float = 0.2  # haku: tc ≤ as_of + 0.2·dt (η = 0.2, sama lähde)

    # Hakualue on väljempi kuin kuplaehdot, jotta optimi ei jää rajalle
    m_search: tuple[float, float] = (0.01, 0.99)
    omega_search: tuple[float, float] = (2.0, 25.0)

    # Sovituksen suodatin. m, värähtelyt ja tc-raja: Zhang, Zhang & Sornette (2016).
    # ω ja damping: Bitcoin-LPPLS (Wheatley ym. 2018) ja lppls-kirjasto; Sornetten ryhmän
    # damping ≥ 1 hylkäsi myös kaikki testikuplat, ks. SUUNNITELMA.md.
    m_bounds: tuple[float, float] = (0.1, 0.9)
    omega_bounds: tuple[float, float] = (4.0, 25.0)
    min_damping: float = 0.5       # m|B|/(ω|C|)
    min_oscillations: float = 2.5  # ω/π·ln((tc−t1)/(tc−t2))
    tc_qual_frac: float = 0.13     # hyväksytty tc ≤ as_of + 0.13·dt
    max_rel_error: float = 0.15    # log-residuaalien RMSE (kalibroitu)

    # Hinnannousuehto (Greenwood, Shleifer & You 2019): 2 vuoden nousu ≥ 100 % → kaatumisen
    # todennäköisyys n. 53 %, 50 % → n. 20 %. Antikuplalle peilikuva log-asteikolla (−50 %).
    runup_days: int = 730
    min_runup: float = 1.00        # kupla
    near_runup: float = 0.50       # lähellä

    # Havainto
    horizon_days: int = 182
    confidence_threshold: float = 0.10
    near_threshold: float = 0.05  # 🟡 "lähellä"

    # Seuranta
    min_tolerance_days: int = 30
    crash_threshold: float = 0.15
    crash_window_days: int = 90

    # Rinnakkaisuus
    workers: int = max(1, (os.cpu_count() or 2) - 1)

    # Menetelmä: "P" = pitkä (yllä olevat ikkunat), "L" = lyhyt (short()-muunnelma)
    method: str = "P"

    # Lyhyt menetelmä: 52 tasavälistä ikkunaa 30–252 kauppapäivää (~6 vk – 1 v).
    # Lyhin ikkuna kuten Sornetten lyhyen aikaskaalan indikaattoreissa (~30 pv).
    # Nousuehto vuodessa: ≥ 50 % kupla, ≥ 25 % lähellä (antikuplalle lasku ≥ 33 % log-peilinä).
    short_window_min: int = 30
    short_window_max: int = 252
    short_window_count: int = 52
    short_runup_days: int = 365
    short_min_runup: float = 0.50
    short_near_runup: float = 0.25
    # Aikaisempi varoitus: hyväksytään koko tc-hakualue (≤ as_of + 0.2·dt), kun pitkässä
    # raja on 0.13·dt. Kalibrointi (13 kuplatilannetta 1–8 vk ennen huippua, 29 vertailua):
    # 0.13 → 3/13, 0.2 → 8/13 kuplista; vertailuista kupla 1/29 molemmilla (KWEB-antikupla).
    short_tc_qual_frac: float = 0.20

    def short(self) -> "Config":
        """Lyhyen menetelmän asetukset; muu suodatin, confidence-rajat ja horisontti ovat samat."""
        return replace(self, method="L",
                       window_min=self.short_window_min, window_max=self.short_window_max,
                       window_count=self.short_window_count, runup_days=self.short_runup_days,
                       min_runup=self.short_min_runup, near_runup=self.short_near_runup,
                       tc_qual_frac=self.short_tc_qual_frac)
