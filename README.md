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
1. Seurantalistalla on valmiina 75 yleisintä osakeindeksiä eri puolilta maailmaa sekä
   BTC, ETH ja kulta. Listaa voi rajata hakukentällä (esim. "intia", "dax"). Omia
   tunnuksia lisätään Yahoo Finance -tunnuksilla, esim. `NVDA`.
2. *Skannaa kaikki* skannaa listassa näkyvät tunnukset (hakukenttä rajaa joukkoa), ja
   *Skannaa valitut* vain valitut. Yksi tunnus vie noin 15 s (4 ytimellä), joten koko
   lista vie noin 20 minuuttia.
3. Taulukossa: confidence (+ = kupla, − = antikupla), mediaani-tc, tc-väli ja tila
   🔴 kupla / 🟡 lähellä / ⚪ ei. Rivin valinta piirtää kuvaajan, ja *Tallenna PNG* tallentaa sen.
4. **Kupla tallentuu automaattisesti** *Tallennetut kuplat* -välilehdelle, ja seuranta alkaa.

**Testitila:** ruksaa *Testitila: as-of-päivä*, jolloin sovellus olettaa, että "tänään"
on valittu päivä. Pikavalinnoissa on Bitcoin 2017-12-01, Shanghai 2007-10-01 ja Shanghai 2015-06-01.
Testikuplat merkitään erikseen.

**Tallennetut kuplat**
- *Päivitä sarjat* hakee seurattaville tunnuksille uuden datan ja arvioi jokaisen kuplan:
  - **toteutui**: havainnon jälkeen huippu, jota seuraa ≥ 15 %:n pudotus 90 päivän sisällä
    (antikuplalla pohja ja nousu)
  - **ei toteutunut**: ennustettu tc-väli (vähintään ±30 pv) ohitettiin ilman käännettä
  - **odottaa**: väli on vielä kesken
- *Ero (pv)* kertoo, kuinka paljon todellinen käänne poikkesi ennustetusta tc:stä.
- Kuvaajassa havaintohetken data on sinisenä, toteuma oranssina, sovite mustana ja tc punaisena.

## Miten havainto toimii

- Data: noin 3 vuotta päivittäisiä päätöskursseja (yfinance), välimuistissa SQLitessä.
- Ikkunat: 60–750 kauppapäivää 15 päivän välein, kaikki päättyvät as-of-päivään.
- Sovitus: Filimonov & Sornette (2013). A, B, C1 ja C2 ratkaistaan lineaarisesti, ja
  (tc, m, ω) haetaan Nelder–Meadilla 10 alkupisteestä. tc rajataan tulevaisuuteen.
- Suodatin: 0.1 < m < 0.9, 6 < ω < 13, |C|/|B| < 1 ja puolivärähtelyjä ≥ 2.5.
- **Confidence** = niiden ikkunoiden osuus, joiden sovitus läpäisee suodattimen ja
  joiden tc osuu 6 kuukauden sisään. Kupla havaitaan, kun confidence ≥ 15 %.

Kaikki rajat ja kynnykset ovat tiedostossa [lppls_app/config.py](lppls_app/config.py).

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
