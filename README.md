# LPPLS-kuplaskanneri

Työpöytäsovellus, joka etsii **tulevia** kuplia Didier Sornetten LPPLS-mallilla
(log-periodic power law singularity). Sovellus sovittaa mallin moneen tähän päivään
päättyvään aikaikkunaan ja hälyttää, kun riittävän moni sovitus ennustaa kriittisen
hetken *tc* lähitulevaisuuteen. Havaitut kuplat tallennetaan, ja niiden toteutumista
seurataan.

> Tutkimus- ja opiskelukäyttöön. LPPLS-ennuste ei ole sijoitussuositus.

## Asennus ja käynnistys

```bash
cd ~/Desktop/Hommat/10_projektit/lppls-app
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m lppls_app
```

Asennuksen jälkeen sovelluksen voi käynnistää myös komennolla `.venv/bin/lppls-app`.

## Käyttö

**Skanneri**
1. Seurantalistalla on valmiina 75 yleisintä osakeindeksiä eri puolilta maailmaa,
   39 raaka-ainetta (futuurit: energia, metallit, viljat, pehmeät raaka-aineet, karja ja
   maitotuotteet sekä S&P GSCI -indeksi), 40 suurinta kryptovaluuttaa (ilman
   stablecoineja) sekä 40 kuplille altista kohdetta: teemarahastot (puolijohteet, tekoäly,
   uraani, puhdas energia, kultakaivokset, kvanttilaskenta …), momentum-osakkeet (NVDA, TSLA, PLTR …),
   S&P 500 -sektorit, asuntomarkkina-ETF:t ja maa-ETF:t (Brasilia, Vietnam, Argentiina,
   Puola). Listaa voi rajata hakukentällä (esim. "intia", "vehnä"; "=F" näyttää
   futuurit ja "-USD" kryptot). Omia
   tunnuksia lisätään Yahoo Finance -tunnuksilla, esim. `NVDA`.
2. *Skannaa kaikki* skannaa listassa näkyvät tunnukset (hakukenttä rajaa joukkoa), ja
   *Skannaa valitut* vain valitut. Yksi tunnus vie noin 9 s (4 ytimellä), joten koko
   lista (195 tunnusta) vie noin 27 minuuttia.

   Raaka-aineiden hinnat ovat jatkuvia lähimmän sopimuksen futuurisarjoja. Sopimuksen
   vaihtuessa (roll) sarjaan voi tulla pieni hyppy, joka voi häiritä sovitusta.
3. Taulukossa: confidence (+ = kupla, − = antikupla), mediaani-tc, tc-väli ja tila
   🔴 kupla / 🟡 lähellä / ⚪ ei. Rivin valinta piirtää kuvaajan, ja *Tallenna PNG* tallentaa sen.
4. **Kupla tallentuu automaattisesti** *Tallennetut kuplat* -välilehdelle, ja seuranta alkaa.

**Testitila:** avaa vasemman reunan *Testaus historiallisilla kuplilla* -osio ja ruksaa *Testitila: as-of-päivä*, jolloin sovellus olettaa, että "tänään"
on valittu päivä. Pikavalinnoissa on Bitcoin 2017-12-01, Shanghai 2007-10-01 ja Shanghai 2015-06-01.
Testikuplat merkitään erikseen.

**Tallennetut kuplat**
- *Päivitä sarjat* hakee seurattaville tunnuksille uuden datan ja arvioi jokaisen kuplan:
  - **toteutui**: havainnon jälkeen huippu, jota seuraa ≥ 15 %:n pudotus 90 päivän sisällä
    (antikuplalla pohja ja nousu)
  - **ei toteutunut**: ennustettu tc-väli (vähintään ±30 pv) ohitettiin ilman käännettä
  - **odottaa**: väli on vielä kesken
- *Conf +* ja *Conf −* ovat luottamusindikaattorit havaitsemispäivänä, eli niiden ikkunoiden
  osuus, jotka näkivät nousukuplan (+) tai antikuplan (−).
- *Ero (pv)* kertoo, kuinka paljon todellinen käänne poikkesi ennustetusta tc:stä.
- Kuvaajassa havaintohetken data on sinisenä, toteuma oranssina, sovite mustana ja tc punaisena.

## Miten havainto toimii

Kuplaksi luokitellaan vain tilanne, jossa **sekä** LPPLS-malli että hinnannousu täyttävät ehdot.

**1. Sovitukset:** noin 4 vuotta päivittäisiä päätöskursseja. Ikkunoita on 24 tasavälein
125–1008 kauppapäivää eli noin puolesta vuodesta neljään vuoteen (lyhin kuten Zhang,
Zhang & Sornette 2016). Kaikki ikkunat päättyvät
as-of-päivään. A, B, C1 ja C2 ratkaistaan lineaarisesti, ja (tc, m, ω) haetaan Nelder–Meadilla
(Filimonov & Sornette 2013).

**2. Sovituksen suodatin**, jonka jokaisen ikkunan sovituksen pitää läpäistä:

| Ehto | Raja | Lähde |
|---|---|---|
| eksponentti m | 0.1 – 0.9 | Zhang, Zhang & Sornette 2016 |
| log-taajuus ω | 4 – 25 | Wheatley ym. 2018 (Bitcoin-LPPLS), lppls-kirjasto |
| damping m\|B\|/(ω\|C\|) | ≥ 0.5 | sama |
| puolivärähtelyt ω/π·ln((tc−t1)/(tc−t2)) | ≥ 2.5 | Zhang, Zhang & Sornette 2016 |
| kriittinen hetki tc | as-of < tc ≤ as-of + 0.13·ikkuna | sama (vain tulevaisuuteen) |
| sovitusvirhe (log-RMSE) | ≤ 0.15 | kalibroitu testikuplilla |
| B | < 0 kupla, > 0 antikupla | |

**3. Confidence** on niiden ikkunoiden osuus, jotka läpäisevät suodattimen ja joiden tc osuu
6 kuukauden sisään. Raja on ≥ 10 %.

**4. Hinnannousu 2 vuodessa** (nykyhinta / 2 vuoden pohja): **≥ 100 %**. Greenwood,
Shleifer & You (2019) havaitsivat, että 100 %:n nousu kahdessa vuodessa nostaa 40 %:n
romahduksen todennäköisyyden noin 53 %:iin, kun 50 %:n nousulla se on noin 20 %.
Antikuplalla vastaava ehto on lasku ≥ 50 %.

| Tila | Ehdot |
|---|---|
| 🔴 kupla | confidence ≥ 10 %, mediaani-tc 6 kk sisällä, muutos ≥ 100 % |
| 🟡 lähellä | confidence ≥ 5 % ja muutos ≥ 50 % |
| ⚪ ei | muut |

Testikuplilla 6/8 tunnistuu kupliksi: BTC 2017, Shanghai 2007 (kaksi päivää), Shanghai 2015 ja
Nasdaq 2000 (kaksi päivää). Nikkei 1989 jää tunnistamatta (nousu vain +69 %), samoin BTC
maaliskuu 2021. Kalibrointi on tehty samoilla tapauksilla, joten tarkkuus uusilla
aineistoilla on todennäköisesti heikompi.

Kaikki rajat ovat tiedostossa [lppls_app/config.py](lppls_app/config.py).

### Lähteet
- Filimonov, V. & Sornette, D. (2013). A stable and robust calibration scheme of the log-periodic power law model. *Physica A* 392.
- Zhang, Q., Zhang, Q. & Sornette, D. (2016). Early warning signals of financial crises with multi-scale quantile regressions of LPPLS. *PLoS ONE* 11(11). https://pmc.ncbi.nlm.nih.gov/articles/PMC5091919/
- Wheatley, S., Sornette, D. ym. (2018). Are Bitcoin bubbles predictable? https://arxiv.org/abs/1803.05663
- Greenwood, R., Shleifer, A. & You, Y. (2019). Bubbles for Fama. *Journal of Financial Economics* 131(1). https://www.nber.org/papers/w23191
- Johansen, A. & Sornette, D. (2010). Shocks, crashes and bubbles in financial markets. https://arxiv.org/abs/cond-mat/0210509

## Tiedostot

| Polku | Sisältö |
|---|---|
| `lppls_app/model.py` | LPPLS-yhtälö, sovitus, suodatin |
| `lppls_app/scanner.py` | ikkunoiden sovitus rinnakkain, confidence |
| `lppls_app/data.py` | Yahoo-haku välimuistin kautta, CSV-tuonti |
| `lppls_app/storage.py` | SQLite: seurantalista, välimuisti, skannaukset, kuplat |
| `lppls_app/tracker.py` | sarjojen päivitys ja toteuman arviointi |
| `lppls_app/plot.py` | kuvaajat |
| `lppls_app/gui/` | PySide6-käyttöliittymä |

Tietokanta: `~/.local/share/lppls-app/bubbles.db` (polun voi vaihtaa ympäristömuuttujalla `LPPLS_DB`).

## Testit

```bash
.venv/bin/pytest
```
