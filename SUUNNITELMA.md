# LPPLS-kuplaskanneri – työpöytäsovellus (Python, Linux)

## Konteksti
Käyttäjä haluaa työpöytäsovelluksen, joka havaitsee **tulevia** kuplia (ei menneitä)
Didier Sornetten LPPLS-mallilla. Sovellus hakee seurattaville tunnuksille vain tarvittavan
määrän tuoretta dataa (noin 3 vuotta), sovittaa mallin useaan tähän päivään päättyvään
ikkunaan ja hälyttää, jos riittävän moni sovitus ennustaa kriittisen hetken tc
**tulevaisuuteen**. Havaitut kuplat tallennetaan SQLiteen. "Päivitä sarjat" -napilla
seurataan, toteutuiko ennuste. Kuvia tarkastellaan sovelluksessa (log-hinta pisteinä,
sovite mustana viivana, tc punaisena katkoviivana) ja napista syntyy PNG.
Testaukseen käytetään historiallisia kuplia (Bitcoin 2017, Shanghai Composite 2007 ja
2015) **as-of-tilassa**: sovellukselle kerrotaan, että "tänään" on menneisyyden päivä.

Malli: `ln p(t) = A + B·(tc−t)^m + C1·(tc−t)^m·cos(ω·ln(tc−t)) + C2·(tc−t)^m·sin(ω·ln(tc−t))`, t < tc

## Teknologia
PySide6, matplotlib (`FigureCanvasQTAgg`), yfinance (`BTC-USD`, `000001.SS`, ei API-avainta),
numpy/scipy/pandas, sqlite3, `concurrent.futures.ProcessPoolExecutor` (rinnakkaiset sovitukset), pytest.

## Arkkitehtuuri ja tiedonkulku
```
watchlist (SQLite) ──► Skannaa (as_of = tänään | testipäivä)
                           │
     fetch(ticker, as_of − 3 v … as_of) ──► price_cache (SQLite, vanhenee 1 vrk)
                           │
                           ▼
              ScanSession (muistissa)
                ikkunat: pituus 60–750 kauppapäivää, kaikki päättyvät as_of-päivään
                fit_lppls() jokaiselle ikkunalle rinnakkain
                           │
                           ▼
              confidence = qualified fits, joiden tc ∈ (as_of, as_of + horisontti] / kaikki
                           │
               ├─ confidence < kynnys → näkyy taulukossa, ei tallenneta
               └─ confidence ≥ kynnys → Storage.save_bubble()  + seuranta
                                          │
              "Päivitä sarjat" ──► tracker.update_all() → evaluate_outcome()
```
Ennuste jäädytetään tallennushetkellä, ja seurannassa sitä verrataan uuteen dataan.
Kerrokset: `model`, `scanner` ja `tracker` ovat puhdasta Pythonia ilman Qt:ta, `storage`
hoitaa vain SQLiten ja `gui` on ohut kerros niiden päällä.

## Sijainti
Projekti luodaan kansioon `~/Desktop/Hommat/10_projektit/lppls-app/` (muiden projektien,
kuten `tilastokeskus`, rinnalle), ja istunto siirretään sinne. Tämä suunnitelma tallennetaan
projektiin tiedostoksi `SUUNNITELMA.md`. Lisäksi tulevat `git init`, `.gitignore` (venv,
`__pycache__`, `*.db`) ja virtuaaliympäristö `.venv`.

## Rakenne
```
lppls-app/
  SUUNNITELMA.md
  README.md         # asennus ja käyttö
  pyproject.toml
  lppls_app/
    __main__.py
    config.py        # polut, kynnykset, ikkunaparametrit, horisontti
    data.py          # fetch(ticker, start, end) välimuistin kautta, load_csv()
    model.py         # lppls(), fit_lppls(), LPPLSResult, is_qualified()
    scanner.py       # scan_ticker(ticker, as_of) -> ScanResult; scan_watchlist()
    tracker.py       # update_all(), evaluate_outcome()
    storage.py       # skeema, välimuisti, watchlist, kuplat, seuranta
    plot.py          # draw_scan(), draw_tracked()
    gui/
      main_window.py # QTabWidget: "Skanneri" | "Tallennetut kuplat"
      scanner_tab.py
      bubbles_tab.py
      workers.py     # ScanWorker, UpdateWorker (QThread)
  tests/  test_model.py  test_scanner.py  test_storage.py  test_tracker.py
```

## Sovitus (`model.py`)
- Filimonov & Sornette (2013): lineaariset A, B, C1, C2 ratkaistaan `lstsq`:llä, ja
  (tc, m, ω) etsitään useasta satunnaisesta alkupisteestä (noin 10 kpl) `scipy.optimize.minimize`-funktiolla.
  Tämä on nopeampaa kuin differential_evolution, mikä on tärkeää, koska sovituksia on paljon.
- **tc rajataan tulevaisuuteen:** tc ∈ (as_of, as_of + 0.5·ikkunan pituus].
- `is_qualified()`: 0.1<m<0.9, 6<ω<13, |C|/|B|<1, värähtelyjä ≥ 2.5, B<0 (positiivinen kupla)
  tai B>0 (negatiivinen eli "antikupla", romahdusta seuraava pohja). Molemmat raportoidaan erikseen.

## Skannaus (`scanner.py`)
- Ikkunat: pituudet 60…750 kauppapäivää 10 päivän välein (noin 70 sovitusta/tunnus, säädettävä).
- `ScanResult`: confidence (+ ja − erikseen), tc-jakauma (mediaani, 10–90 %), mediaanisovitus kuvaa varten, ikkunoiden lukumäärä.
- **Kupla havaittu**, kun confidence ≥ 0.3 (säädettävä) ja mediaani-tc on horisontin
  (oletus 6 kk) sisällä.
- `as_of`-parametri kulkee läpi koko ketjun, joten testitila ja oikea käyttö ajavat samaa koodia.
- Rinnakkaistus `ProcessPoolExecutor`illa ja edistyminen signaaleina käyttöliittymälle.

## SQLite-skeema (`storage.py`)
```sql
CREATE TABLE watchlist      (ticker TEXT PRIMARY KEY, name TEXT, added TEXT, active INTEGER DEFAULT 1);
CREATE TABLE price_cache    (ticker TEXT, date TEXT, price REAL, fetched_at TEXT, PRIMARY KEY (ticker, date));
CREATE TABLE scans          (id INTEGER PRIMARY KEY, ticker TEXT, as_of TEXT, run_at TEXT,
                             conf_pos REAL, conf_neg REAL, tc_median TEXT, tc_p10 TEXT, tc_p90 TEXT);
CREATE TABLE bubbles        (id INTEGER PRIMARY KEY, ticker TEXT, scan_id INTEGER REFERENCES scans(id),
                             detected_as_of TEXT, is_test INTEGER, sign TEXT, confidence REAL,
                             tc TEXT, tc_p10 TEXT, tc_p90 TEXT,
                             m REAL, omega REAL, A REAL, B REAL, C1 REAL, C2 REAL, r2 REAL,
                             status TEXT DEFAULT 'odottaa', actual_peak_date TEXT,
                             actual_peak_price REAL, max_drawdown REAL, last_updated TEXT, note TEXT);
CREATE TABLE bubble_prices  (bubble_id INTEGER REFERENCES bubbles(id) ON DELETE CASCADE,
                             date TEXT, price REAL, PRIMARY KEY (bubble_id, date));
CREATE TABLE tracked_prices (ticker TEXT, date TEXT, price REAL, PRIMARY KEY (ticker, date));
```
- `scans` tallentaa jokaisen skannauksen tunnusluvut (pieni rivi), jolloin confidence-
  historiaa voi myöhemmin piirtää ajan yli ilman, että raakasovituksia säilytetään.
- `bubble_prices` on jäädytetty tilannekuva, ja `tracked_prices` on tunnuskohtainen jatkosarja.
- `is_test=1` erottaa as-of-testiajot oikeista havainnoista (suodatin käyttöliittymässä).
- Duplikaattisuoja: sama ticker + sign + tc (±5 pv) aktiivisena → päivitetään eikä lisätä uutta.

## Seuranta (`tracker.py`)
- `update_all()` hakee aktiivisille kuplille datan inkrementaalisesti `tracked_prices`-tauluun.
  Testikuplille "tänään" on oikea tämä päivä, jolloin historiallinen toteuma näkyy heti.
- `evaluate_outcome()`, Δ = väli tc_p10…tc_p90 (vähintään ±30 pv):
  **toteutui** = huippu välillä ja sen jälkeen pudotus ≥ 15 %; **ei toteutunut** = väli ohitettu
  ilman ehdon täyttymistä; **odottaa** = väli kesken. Kynnykset ovat säädettäviä.
- Yhden tunnuksen virhe ei katkaise muiden päivitystä.

## Käyttöliittymä
**Skanneri-välilehti**
- Seurantalista: lisää/poista tunnus (oletuksena esim. `^GSPC`, `^NDX`, `BTC-USD`, `ETH-USD`, `000001.SS`, `GC=F`)
- **Skannaa kaikki** / **Skannaa valittu**, edistymispalkki
- Testitila: valintaruutu "As-of-päivä" + päivämäärä (pikavalinnat: BTC 2017-12-01, SSE 2007-10-01, SSE 2015-06-01)
- Tulostaulukko: tunnus, confidence +/−, mediaani-tc, tc-väli, päiviä tc:hen ja tila (🔴 kupla / 🟡 lähellä / ⚪ ei)
- Kuvaaja valitulle: log-hinnat, mediaanisovite jatkettuna tc:hen, tc punainen katkoviiva,
  tc_p10–p90 vaaleana kaistana, as_of harmaana viivana. Nappi **Tallenna PNG**.

**Tallennetut kuplat -välilehti**
- Taulukko: tunnus, havaittu (as_of), ennustettu tc + väli, todellinen huippu, ero päivinä,
  max-pudotus, tila (värikoodattu), testi/oikea. Suodattimet.
- Napit **Päivitä sarjat**, **Tallenna PNG**, **Poista**, **Lopeta seuranta**
- Kuvaaja (`draw_tracked`): tilannekuva sinisenä, havainnon jälkeinen data oranssina,
  jäädytetty sovite, ennustettu tc ja väli sekä todellinen huippu merkittynä.

## Myöhemmin (ei 1. versioon)
Automaattinen skannaus käynnistyksessä tai ajastettuna, työpöytäilmoitus uudesta kuplasta,
confidence-historian kuvaaja `scans`-taulusta ja osumatarkkuustilasto.

## Varmistus
1. `pytest`: synteettinen LPPLS-sarja katkaistuna ennen tc:tä → skanneri antaa korkean
   confidencen ja tc:n tulevaisuuteen ±10 %; satunnaiskävely → matala confidence. Storage
   `:memory:`-kannalla, tracker keinotekoisilla sarjoilla (kaikki kolme tilaa), yfinance mockattuna.
2. As-of-testit sovelluksessa:
   - `BTC-USD` as_of 2017-12-01 → kupla, tc noin joulukuu 2017 ja tammikuu 2018
   - `000001.SS` as_of 2007-10-01 → kupla, tc noin loka- ja marraskuu 2007
   - `000001.SS` as_of 2015-06-01 → kupla, tc noin kesäkuu 2015
   - **Päivitä sarjat** → kaikilla tila "toteutui"
3. Oikea skannaus tällä päivällä koko seurantalistalle valmistuu kohtuullisessa ajassa
   (tavoite < 1 min / 6 tunnusta). Toisella kerralla ei tehdä verkkopyyntöjä (välimuisti).
4. PNG syntyy molemmilta välilehdiltä. Väärä tunnus tai ei verkkoa → virheilmoitus, ei kaatumista.

Huom: työkalu on tutkimus- ja opiskelukäyttöön, eikä LPPLS-ennuste ole sijoitussuositus.

## Toteutuksessa tehdyt muutokset suunnitelmaan
- Optimointi hakee väljemmältä alueelta (m 0.01–0.99, ω 2–25), ja Sornetten suodatin
  (m 0.1–0.9, ω 6–13) ajetaan vasta jälkikäteen. Muuten lähes kaikki sovitukset jäivät rajoille.
- Kynnykset kalibroitiin historiallisilla kuplilla: kupla, kun confidence ≥ 15 % (ei 30 %), ja "lähellä", kun ≥ 5 %.
- Ikkunaväli on 15 päivää (ei 10) nopeuden vuoksi: noin 15 s/tunnus 4 ytimellä.
- Toteuman arvioinnissa käännettä haetaan havaintopäivästä tc-välin loppuun, joten myös
  ennustettua aikaisempi huippu löytyy (näkyy negatiivisena erona).
- Kupla-taulussa on lisäksi sarakkeet `tc_years`, `window_start` ja `tracking`.

## Kuplakriteerien tarkennus (31.10.2026)
Ensimmäinen versio löysi 7 "kuplaa" nykyindekseistä (esim. NZ50, jonka 2 vuoden nousu oli +9 %).
Syyt: suodattimessa ei ollut damping-ehtoa (kaikkien 7 damping oli 0.22–0.47), tc sai olla
jopa 0.5·ikkunan päässä, eikä hinnannousulle ollut mitään vaatimusta.

Muutokset:
- Suodatin: damping ≥ 0.5, ω 4–25, tc ≤ as_of + 0.13·dt, log-RMSE ≤ 0.15, ikkunat 125–750.
  Sornetten ryhmän damping ≥ 1 (Zhang ym. 2016) hylkäsi myös 7/8 testikuplaa, koska
  sovitusmenetelmämme tuottaa pienempiä damping-arvoja, joten käytössä on Wheatleyn ym. (2018) 0.5.
- Uusi hintaehto (Greenwood, Shleifer & You 2019): 2 vuoden nousu ≥ 100 % = kupla, 50 % = lähellä.
- Confidence-raja 15 % → 10 %, koska tiukempi suodatin pienentää osuuksia.

Kalibrointi (19 tapausta, samat fitit eri raja-arvoilla): 6/8 historiallisesta kuplasta
tunnistuu, 0/11 nyky- tai vertailutapauksesta luokittuu kuplaksi ja 1 luokittuu "lähellä"
(NYFANG). Seurannan toteumaehto (≥ 15 %:n pudotus 90 päivässä) on ennallaan.
