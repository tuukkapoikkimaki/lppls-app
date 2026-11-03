# LPPLS-kuplaskanneri

Työpöytäsovellus, joka etsii **tulevia** kuplia Didier Sornetten LPPLS-mallilla
(log-periodic power law singularity). Sovellus sovittaa mallin moneen tähän päivään
päättyvään aikaikkunaan ja hälyttää, kun riittävän moni sovitus ennustaa kriittisen
hetken *tc* lähitulevaisuuteen. Skannauksia on kaksi: **pitkä (P)**, jossa on 24 ikkunaa
(~0,5–4 v), ja **lyhyt (L)**, jossa on 52 ikkunaa (~6 vk – 1 v). Havaitut kuplat tallennetaan, ja niiden toteutumista
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
   stablecoineja) sekä 66 kuplille altista kohdetta: teemarahastot (puolijohteet, tekoäly,
   uraani, puhdas energia, kultakaivokset, kvanttilaskenta, generatiivinen tekoäly, datakeskukset,
   kyberturvallisuus, ydinvoima, avaruus, bioteknologia …), momentum-osakkeet (NVDA, TSLA, PLTR …),
   S&P 500 -sektorit, asuntomarkkina-ETF:t ja maa-ETF:t (Brasilia, Vietnam, Argentiina,
   Puola). Listaa voi rajata hakukentällä (esim. "intia", "vehnä"; "=F" näyttää
   futuurit ja "-USD" kryptot). Omia
   tunnuksia lisätään Yahoo Finance -tunnuksilla, esim. `NVDA`.
2. *Skannaa kaikki* skannaa listassa näkyvät tunnukset (hakukenttä rajaa joukkoa), ja
   *Skannaa valitut* vain valitut. Jokainen tunnus skannataan molemmilla menetelmillä.
   Yksi tunnus vie noin 20 s (4 ytimellä), joten koko lista (220 tunnusta) vie noin 1¼ tuntia.

   Raaka-aineiden hinnat ovat jatkuvia lähimmän sopimuksen futuurisarjoja. Sopimuksen
   vaihtuessa (roll) sarjaan voi tulla pieni hyppy, joka voi häiritä sovitusta.
3. Taulukossa: confidence molemmille menetelmille (*C P* = pitkä, *C L* = lyhyt; + = kupla,
   − = antikupla), muutos 2 v ja 1 v, mediaani-tc, tc-väli ja tila kummallekin menetelmälle
   (🔴 kupla / 🟡 lähellä / ⚪ ei). tc-sarakkeet tulevat kuplan havainneesta menetelmästä.
   Rivin valinta piirtää kuvaajan. Nuolet ← / → vaihtavat pitkän ja lyhyen menetelmän
   kuvaajan välillä, ja *Tallenna PNG* tallentaa näkyvän kuvaajan.
4. **Kupla tallentuu automaattisesti** *Tallennetut kuplat* -välilehdelle, kun **kumpi tahansa**
   menetelmä antaa tilan 🔴 kupla, ja seuranta alkaa. Jokainen skannaus tallentaa lisäksi
   C P- ja C L -arvot, joista muodostuu confidence-historia.

**Testitila:** avaa vasemman reunan *Testaus historiallisilla kuplilla* -osio ja ruksaa *Testitila: as-of-päivä*, jolloin sovellus olettaa, että "tänään"
on valittu päivä. Pikavalinnoissa on Bitcoin 2017-12-01, Shanghai 2007-10-01 ja Shanghai 2015-06-01.
Testikuplat merkitään erikseen.

**Tallennetut kuplat**
- *Päivitä sarjat* hakee seurattaville tunnuksille uuden datan, skannaa ne molemmilla
  menetelmillä (uudet confidence-pisteet; jo tänään skannatut ohitetaan) ja arvioi jokaisen kuplan:
  - **toteutui**: havainnon jälkeen huippu, jota seuraa ≥ 15 %:n pudotus 90 päivän sisällä
    (antikuplalla pohja ja nousu)
  - **ei toteutunut**: ennustettu tc-väli (vähintään ±30 pv) ohitettiin ilman käännettä
  - **odottaa**: väli on vielä kesken
- *Menetelmä* kertoo, mikä havaitsi kuplan: P, L tai P+L.
- *C P ±* ja *C L ±* ovat luottamusindikaattorit havaitsemispäivänä, eli niiden ikkunoiden
  osuus, jotka näkivät nousukuplan (+) tai antikuplan (−). Ennen lyhyttä menetelmää
  tallennetuilla kuplilla C L on "–".
- *Ero (pv)* kertoo, kuinka paljon todellinen käänne poikkesi ennustetusta tc:stä.
- Kuvaajassa havaintohetken data on sinisenä, toteuma oranssina, sovite mustana ja tc punaisena.
  Oikealla asteikolla on confidence-historia kuplan suuntaan: **C P punaisena** ja
  **C L vihreänä**. Jokainen skannaus lisää pisteen; samalta päivältä näytetään viimeisin.
- Työkalurivin nuolet ← / → vaihtavat näkymää: 1) log-hinta, 2) hinta ilman logaritmia
  koko seuratulla jaksolla.

**Kuvaajat (molemmat välilehdet)**
- **Periodi:** kuvan alla on viivamainen valitsin. Vedä kahvoista periodin alkua ja loppua,
  tai vedä kahvojen välistä janaa, jolloin koko periodi liukuu. Pystyakseli sovitetaan
  valitun periodin dataan.
- **Zoomaus:** paina hiiren rullaa kuvan päällä, niin zoomaus kytkeytyy päälle. Rulla eteen
  zoomaa lähemmäs ja taakse kauemmas, ja kursorin kohta pysyy paikallaan. Uusi rullan
  painallus lopettaa zoomauksen. Koti-painike (⌂) palauttaa koko kuvan.

## Miten havainto toimii

Kuplaksi luokitellaan vain tilanne, jossa **sekä** LPPLS-malli että hinnannousu täyttävät ehdot.

**1. Sovitukset:** noin 4 vuotta päivittäisiä päätöskursseja. Pitkässä menetelmässä ikkunoita on 24 tasavälein
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
| kriittinen hetki tc | as-of < tc ≤ as-of + 0.13·ikkuna (lyhyt: 0.2) | sama (vain tulevaisuuteen) |
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

**5. Lyhyt menetelmä (L):** 52 tasavälistä ikkunaa 30–252 kauppapäivää (~6 vk – 1 v; lyhin
kuten Sornetten lyhyen aikaskaalan indikaattoreissa). Confidence-rajat ja horisontti ovat samat
kuin pitkässä menetelmässä, mutta nousuehto lasketaan vuoden pohjasta: **≥ 50 %** kuplalle ja
≥ 25 % lähellä-tilalle (antikuplalla lasku ≥ 33 %). Lisäksi tc-raja on väljempi:
**tc ≤ as-of + 0,2 · ikkuna** (pitkässä 0,13), jotta lyhyt menetelmä varoittaa aikaisemmin.

Kalibrointi lyhyelle menetelmälle (13 kuplatilannetta 1–8 viikkoa ennen huippua ja 29 vertailua):

| tc-raja | Kuplatilanteista kupla | Vertailuista kupla / lähellä |
|---|---|---|
| 0,13 | 3/13 | 1/29 / 1 |
| **0,20** | **8/13** | 1/29 / 3 |

Väljemmällä rajalla lyhyt havaitsee esim. BTC 2017 31 päivää, Shanghai 2007 43 päivää ja
Shanghai 2015 39 päivää ennen huippua sekä BTC huhtikuu 2021 (tc 22.4., huippu 13.4.).
Vertailujen ainoa kupla on KWEB:n antikupla tänään (sama myös raja-arvolla 0,13); lähellä-tilaan
nousevat S&P 500 7/2007 ja 12/2021 sekä DAX 6/2014. Nasdaq 2000 tunnistuu vasta 9 päivää
ennen huippua, eikä Nikkei 1989 (vuoden nousu +24 %) tunnistu ollenkaan.

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
