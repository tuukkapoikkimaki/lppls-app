"""Rakentaa dokumentin docs/LPPLS_kuplaskanneri_teoria.pdf.

    python docs/make_figures.py   # kuvat (verkkoyhteys)
    python docs/build_pdf.py
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

HERE = Path(__file__).parent
OUT = HERE / "LPPLS_kuplaskanneri_teoria.pdf"
NOTO = Path("/usr/share/fonts/truetype/noto")
DEJAVU = Path("/usr/share/fonts/truetype/dejavu")

# DejaVu: perus- ja lihavoitu (sisältää ∈ → ≤ −); kursiivit Notosta, koska DejaVu-kursiivia ei ole
pdfmetrics.registerFont(TTFont("Serif", DEJAVU / "DejaVuSerif.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Bold", DEJAVU / "DejaVuSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Italic", NOTO / "NotoSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Serif-BoldItalic", NOTO / "NotoSerif-BoldItalic.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", DEJAVU / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold",
                              italic="Serif-Italic", boldItalic="Serif-BoldItalic")

BODY = ParagraphStyle("body", fontName="Serif", fontSize=9.2, leading=13.2,
                      alignment=TA_JUSTIFY, spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.3, leading=10.8, spaceAfter=2)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.2, leading=10.4, alignment=0, spaceAfter=0)
CAPTION = ParagraphStyle("caption", parent=BODY, fontSize=8.2, leading=10.6, spaceAfter=8,
                         textColor=colors.HexColor("#333333"))
H1 = ParagraphStyle("h1", fontName="Sans-Bold", fontSize=12.5, leading=16, spaceBefore=9,
                    spaceAfter=4, textColor=colors.HexColor("#1f2a44"))
H2 = ParagraphStyle("h2", fontName="Sans-Bold", fontSize=10.3, leading=13, spaceBefore=6,
                    spaceAfter=3, textColor=colors.HexColor("#1f2a44"))
TITLE = ParagraphStyle("title", fontName="Sans-Bold", fontSize=17, leading=21,
                       alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#1f2a44"))
SUB = ParagraphStyle("sub", parent=BODY, alignment=TA_CENTER, fontSize=9.6, spaceAfter=10,
                     textColor=colors.HexColor("#555555"))
ABSTRACT = ParagraphStyle("abstract", parent=BODY, fontSize=9.2, leading=12.8,
                          leftIndent=0.6 * cm, rightIndent=0.6 * cm)

TEXT_WIDTH = A4[0] - 2 * 2.3 * cm
_eq_no = 0


def P(text, style=BODY):
    return Paragraph(text, style)


def eq(tex: str, size: float = 11.5):
    """Yhtälö matplotlibin mathtextillä, numeroituna oikeaan reunaan."""
    global _eq_no
    _eq_no += 1
    plt.rcParams["mathtext.fontset"] = "cm"
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=300, format="png", bbox_inches="tight", pad_inches=0.03,
                transparent=True)
    plt.close(fig)
    buf.seek(0)
    img = Image(buf)
    scale = 72 / 300
    img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
    if img.drawWidth > TEXT_WIDTH - 1.5 * cm:
        k = (TEXT_WIDTH - 1.5 * cm) / img.drawWidth
        img.drawWidth *= k
        img.drawHeight *= k
    t = Table([[img, P(f"({_eq_no})", BODY)]], colWidths=[TEXT_WIDTH - 1.2 * cm, 1.2 * cm])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER"), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def figure(name: str, caption: str, width=14.2 * cm):
    img = Image(str(HERE / "fig" / name))
    k = width / img.imageWidth
    img.drawWidth, img.drawHeight = width, img.imageHeight * k
    return KeepTogether([img, P(caption, CAPTION)])


def table(rows, widths, header=True):
    data = [[P(c, CELL) if isinstance(c, str) else c for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9aa3b5")),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eaf2")))
    t.setStyle(TableStyle(style))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Serif", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawCentredString(A4[0] / 2, 1.3 * cm, str(doc.page))
    if doc.page > 1:
        canvas.drawString(2.3 * cm, A4[1] - 1.4 * cm, "LPPLS-kuplaskanneri – teoria ja havaitsemisen ehdot")
    canvas.restoreState()


def story():
    s = []
    s += [P("LPPLS-kuplaskanneri", TITLE),
          P("Teoria, hintadatan käyttö ja kuplien havaitsemisen ehdot", SUB)]

    s += [P("Tiivistelmä", H2), P(
        "Tässä dokumentissa kuvataan LPPLS-kuplaskanneri, Pythonilla toteutettu työpöytäsovellus, "
        "joka etsii osake- ja kryptomarkkinoilta kuplia ennen kuin ne puhkeavat. Tavoitteena on "
        "korvata jälkikäteen tehtävä arvio ennakoivalla, toistettavalla ja läpinäkyvällä menetelmällä, "
        "jonka jokainen raja-arvo on perusteltu kirjallisuudella. Sovelluksen perustana "
        "on Didier Sornetten ja kollegoiden kehittämä LPPLS-malli (<i>log-periodic power law "
        "singularity</i>). Mallin mukaan sijoittajien laumakäyttäytyminen saa kuplan aikana hinnan "
        "kasvamaan nopeammin kuin eksponentiaalisesti. Kasvu kiihtyy kohti kriittistä hetkeä "
        "<i>t<sub>c</sub></i>, jolloin romahduksen todennäköisyys on suurimmillaan, ja kiihtyvään "
        "trendiin liittyy log-periodisia värähtelyjä, jotka tihenevät <i>t<sub>c</sub></i>:tä "
        "lähestyttäessä. Sovellus hakee jokaiselle seurattavalle tunnukselle noin kolmen vuoden "
        "päivittäiset päätöskurssit Yahoo Financesta ja sovittaa mallin hintojen logaritmeihin "
        "42 eri pituisessa aikaikkunassa, jotka kaikki päättyvät tarkastelupäivään. Sovitus tehdään "
        "Filimonovin ja Sornetten menetelmällä: neljä lineaarista parametria ratkaistaan suoraan "
        "pienimmän neliösumman menetelmällä, ja vain kolme epälineaarista parametria haetaan "
        "numeerisesti. Jokainen sovitus tarkistetaan kirjallisuudesta poimituilla ehdoilla. Niiden "
        "ikkunoiden osuus, jotka läpäisevät ehdot ja ennustavat <i>t<sub>c</sub></i>:n puolen vuoden "
        "sisään, muodostaa luottamusindikaattorin. Tilanne luokitellaan kuplaksi, kun "
        "luottamusindikaattori on vähintään 10 % ja hinta on lisäksi vähintään kaksinkertaistunut "
        "kahdessa vuodessa. Jälkimmäinen ehto perustuu Greenwoodin, Shleiferin ja Youn havaintoon, "
        "että näin suuri nousu nostaa romahduksen todennäköisyyden yli puoleen. Havaitut kuplat "
        "tallennetaan tietokantaan, ja sovellus seuraa, toteutuiko ennustettu käänne: kupla katsotaan "
        "toteutuneeksi, jos ennustetun hetken lähellä tulee huippu ja sitä seuraa vähintään 15 %:n "
        "pudotus. Ehtoja testattiin historiallisilla kuplilla, kuten Bitcoinin vuoden 2017, "
        "Shanghain pörssin vuosien 2007 ja 2015 sekä Nasdaqin vuoden 2000 kuplilla, ja ne "
        "tunnistivat kuusi kahdeksasta. Kriittisen hetken arvio osui 0–4 viikon päähän "
        "todellisesta huipusta. Menetelmä on tutkimuksen ja opiskelun "
        "väline, ei sijoitussuositus.", ABSTRACT)]

    # 1
    s += [P("1  Johdanto", H1), P(
        "Rahoitusmarkkinoiden kupla on tilanne, jossa hinta irtoaa perustekijöistään ja nousee "
        "itseään ruokkivasti: nousu houkuttelee uusia ostajia, jotka nostavat hintaa edelleen. "
        "Kuplat tunnistetaan yleensä vasta jälkikäteen, kun romahdus on jo tapahtunut. Sornette "
        "esittää, että kuplilla on mitattava ”sormenjälki”: hinta kasvaa nopeammin kuin "
        "eksponentiaalisesti, ja kasvuun liittyy tiheneviä värähtelyjä (Sornette 2003; Johansen &amp; "
        "Sornette 2010). Jos sormenjälki löytyy hintasarjasta ajoissa, kuplan loppumisajankohtaa "
        "voidaan arvioida etukäteen."),
      P("LPPLS-kuplaskanneri soveltaa tätä ajatusta järjestelmällisesti. Sovellus käy läpi "
        "seurantalistan (oletuksena 75 osakeindeksiä sekä Bitcoin, Ethereum ja kulta), sovittaa "
        "mallin jokaiseen sarjaan, luokittelee tuloksen ja tallentaa havaitut kuplat. Myöhemmin "
        "se hakee uutta dataa ja tarkistaa, toteutuiko ennuste. Luvussa 2 esitellään mallin teoria, "
        "luvussa 3 kuvataan, miten hintadataa käytetään parametrien estimointiin, luvussa 4 "
        "käydään läpi kuplan ehdot, ja luvussa 5 arvioidaan menetelmän osuvuutta ja rajoituksia.")]

    # 2
    s += [P("2  Mallin teoria", H1), P("2.1  Rationaalinen kupla ja romahdusriski", H2), P(
        "LPPLS-malli pohjautuu Johansenin, Ledoit’n ja Sornetten (2000) JLS-malliin. Siinä hinta "
        "<i>p</i> noudattaa prosessia"),
      eq(r"\frac{dp}{p} = \mu(t)\,dt + \sigma(t)\,dW - \kappa\,dj"),
      P("missä <i>μ</i> on hinnan odotettu kasvuvauhti, <i>σ dW</i> satunnaista vaihtelua ja "
        "<i>j</i> hyppyprosessi, joka saa arvon 1 romahduksen sattuessa. Romahdus pudottaa hintaa "
        "osuuden <i>κ</i>. Romahduksen todennäköisyyttä aikayksikköä kohden kuvaa riskifunktio "
        "<i>h</i>(<i>t</i>). Mallissa sijoittajat ovat rationaalisia: niin kauan kuin romahdusta ei "
        "ole tapahtunut, hinnan odotettu muutos on nolla (arbitraasittomuus). Tästä seuraa"),
      eq(r"\mathrm{E}[dp] = 0 \quad\Rightarrow\quad \mu(t) = \kappa\, h(t)"),
      P("Hinnan on siis noustava sitä nopeammin, mitä suurempi romahdusriski on, jotta sijoittajat "
        "saavat korvauksen riskin kantamisesta. Kuplan aikana riski kasvaa, koska sijoittajat "
        "matkivat toisiaan: laumakäyttäytyminen voimistuu, kunnes yhä suurempi osa markkinasta "
        "toimii samaan suuntaan. Ilmiö muistuttaa fysiikan faasimuutosta, jossa järjestelmä "
        "lähestyy kriittistä pistettä. Kun sijoittajien vuorovaikutusverkostolla on hierarkkinen "
        "rakenne, riskifunktio saa muodon"),
      eq(r"h(t) \approx B'\,(t_c-t)^{m-1} + C'\,(t_c-t)^{m-1}\cos\!\left(\omega \ln(t_c-t) - \phi'\right)"),
      P("Integroimalla yhtälön (2) kasvuvauhti ajan yli saadaan odotetulle log-hinnalle LPPLS-yhtälö"),
      eq(r"\ln \mathrm{E}[p(t)] = A + B\,(t_c-t)^m + C\,(t_c-t)^m \cos\!\left(\omega\ln(t_c-t)-\phi\right),"
         r"\quad t<t_c"),
      P("2.2  Parametrien tulkinta", H2), P(
        "<b><i>t<sub>c</sub></i></b> on kriittinen hetki eli kuplan todennäköisin loppumisajankohta. "
        "Se ei ole varma romahduspäivä: Johansen ja Sornette (2010) arvioivat, että noin kolmasosa "
        "kuplista päättyy pehmeään laskuun ilman romahdusta. <b><i>m</i></b> ∈ (0, 1) kuvaa "
        "kiihtyvyyttä. Log-hinnan kasvuvauhti on −<i>mB</i>(<i>t<sub>c</sub></i> − <i>t</i>)<super><i>m</i>−1</super>, "
        "ja se kasvaa rajatta, kun <i>t</i> → <i>t<sub>c</sub></i>. Itse hinta pysyy silti äärellisenä, "
        "ja tätä kutsutaan äärellisen ajan singulariteetiksi. <b><i>B</i></b> &lt; 0 tarkoittaa "
        "kiihtyvää nousua eli positiivista kuplaa, ja <i>B</i> &gt; 0 kiihtyvää laskua eli "
        "antikuplaa. <b><i>ω</i></b> on värähtelyjen log-taajuus: peräkkäisten värähtelyjen "
        "etäisyydet <i>t<sub>c</sub></i>:stä pienenevät suhteessa "
        "λ = e<super>2π/ω</super>, joten esimerkiksi arvolla <i>ω</i> = 9 jokainen jakso on noin "
        "puolet edellisestä. <b><i>C</i></b> ja <b><i>φ</i></b> ovat värähtelyn amplitudi ja vaihe, "
        "ja <b><i>A</i></b> on log-hinta hetkellä <i>t<sub>c</sub></i>. Kuva 1 havainnollistaa "
        "mallin osia."),
      figure("kuva1_malli.png",
             "<b>Kuva 1.</b> Synteettinen LPPLS-kupla. Katkoviiva on pelkkä potenssilakitrendi, ja musta "
             "käyrä lisää siihen log-periodiset värähtelyt. Siniset pisteet ovat kohinaisia "
             "”havaintoja”. Kasvu kiihtyy ja värähtelyt tihenevät kohti kriittistä hetkeä "
             "<i>t<sub>c</sub></i>.")]

    # 3
    s += [P("3  Miten hintadataa käytetään estimointiin", H1), P("3.1  Aineisto", H2), P(
        "Sovellus hakee Yahoo Financesta päivittäiset päätöskurssit, jotka on korjattu osingoilla ja "
        "osakesplittauksilla. Data haetaan noin kolmen vuoden ajalta tarkastelupäivään "
        "<i>t</i><sub>2</sub> asti. Malliin syötetään hintojen logaritmit "
        "<i>y<sub>i</sub></i> = ln <i>p<sub>i</sub></i> hetkillä <i>t<sub>i</sub></i>, jotka on "
        "ilmaistu desimaalivuosina. Logaritmin ansiosta suhteelliset muutokset ovat samassa "
        "mittakaavassa riippumatta hintatasosta. Malli näkee vain hetkeä <i>t</i><sub>2</sub> "
        "edeltävän datan, joten arvio on aidosti ennakoiva. Testitilassa <i>t</i><sub>2</sub> "
        "voidaan asettaa menneisyyteen, jolloin historiallisia kuplia voi tutkia ilman, että "
        "malli ”näkee” tulevaisuutta. Haettu data tallennetaan SQLite-välimuistiin."),
      P("3.2  Sovitus linearisoimalla", H2), P(
        "Yhtälössä (4) on seitsemän parametria, ja niiden suora optimointi on epävakaata, koska "
        "virhefunktiolla on paljon paikallisia minimejä. Filimonov ja Sornette (2013) "
        "kirjoittavat kosinitermin uudelleen muotoon"),
      eq(r"y(t) = A + B f(t) + C_1 g(t) + C_2 k(t),\quad f=(t_c-t)^m,\ g=f\cos(\omega\ln(t_c-t)),\ "
         r"k=f\sin(\omega\ln(t_c-t))", size=10.5),
      P("missä <i>C</i><sub>1</sub> = <i>C</i> cos <i>φ</i> ja <i>C</i><sub>2</sub> = <i>C</i> sin "
        "<i>φ</i>. Kun epälineaariset parametrit (<i>t<sub>c</sub></i>, <i>m</i>, <i>ω</i>) on "
        "kiinnitetty, malli on lineaarinen parametrien <i>β</i> = (<i>A</i>, <i>B</i>, "
        "<i>C</i><sub>1</sub>, <i>C</i><sub>2</sub>) suhteen, ja ne saadaan suoraan pienimmän "
        "neliösumman ratkaisuna:"),
      eq(r"\mathbf{y} = X\boldsymbol{\beta} + \boldsymbol{\varepsilon},\quad "
         r"X_i = \left[1,\ f_i,\ g_i,\ k_i\right],\quad "
         r"\hat{\boldsymbol{\beta}} = (X^{\top}X)^{-1}X^{\top}\mathbf{y}"),
      P("Numeerisesti on siis haettava vain kolme parametria minimoimalla jäännösneliösumma:"),
      eq(r"(\hat t_c,\hat m,\hat\omega) = \arg\min\ F(t_c,m,\omega),\qquad "
         r"F = \sum_{i=1}^{N}\left(y_i - X_i\hat{\boldsymbol{\beta}}\right)^2"),
      P("Sovellus käyttää Nelder–Mead-simpleksimenetelmää (Nelder &amp; Mead 1965) kymmenestä "
        "satunnaisesta alkupisteestä ja valitsee niistä pienimmän <i>F</i>:n. Hakualue on "
        "<i>m</i> ∈ [0.01, 0.99], <i>ω</i> ∈ [2, 25] ja <i>t</i><sub>2</sub> &lt; <i>t<sub>c</sub></i> "
        "≤ <i>t</i><sub>2</sub> + 0.2Δ<i>t</i>, missä Δ<i>t</i> = <i>t</i><sub>2</sub> − "
        "<i>t</i><sub>1</sub> on ikkunan pituus (Zhang, Zhang &amp; Sornette 2016). Hakualue on "
        "tarkoituksella väljempi kuin luvun 4 hyväksymisehdot, jotta optimi ei jää keinotekoisesti "
        "rajalle. Koska <i>t<sub>c</sub></i> rajataan tulevaisuuteen, malli etsii vain kuplia, "
        "jotka eivät ole vielä päättyneet."),
      P("3.3  Monta ikkunaa ja luottamusindikaattori", H2), P(
        "Yksittäinen sovitus on herkkä sille, mistä päivästä aikaikkuna alkaa, koska kuplan "
        "alkuhetkeä ei tunneta. Siksi sovitus tehdään 42 ikkunaan, joiden pituudet ovat 125, 140, …, "
        "740 kauppapäivää ja jotka kaikki päättyvät hetkeen "
        "<i>t</i><sub>2</sub>. Jokainen ikkuna antaa oman arvionsa parametreista. "
        "Luottamusindikaattori (<i>LPPLS confidence</i>) on niiden ikkunoiden osuus, joiden "
        "sovitus läpäisee luvun 4.1 suodattimen ja joiden <i>t<sub>c</sub></i> osuu horisontin "
        "<i>H</i> = 6 kk sisään:"),
      eq(r"\mathrm{CI}(t_2) = \frac{1}{K}\sum_{k=1}^{K}\mathbf{1}\!\left[\,\mathrm{sovitus}\ k\ "
         r"\mathrm{hyv\ddot{a}ksytty}\ \wedge\ t_2 < t_c^{(k)} \leq t_2 + H\,\right]"),
      P("Hyväksyttyjen ikkunoiden <i>t<sub>c</sub></i>-arvioista lasketaan mediaani sekä 10 %:n "
        "ja 90 %:n prosenttipisteet, jotka muodostavat ennustevälin. Kuvaan piirretään sovitus, "
        "jonka <i>t<sub>c</sub></i> on lähimpänä mediaania. Kuvissa 2 ja 3 menetelmää on sovellettu "
        "Shanghain pörssin vuoden 2015 kuplaan tilanteessa 1.6.2015."),
      figure("kuva2_shanghai.png",
             "<b>Kuva 2.</b> Shanghai Composite, tarkastelupäivä 1.6.2015. Malli käytti vain sinisiä "
             "pisteitä. Mediaani-<i>t<sub>c</sub></i> oli 7.6.2015, ja todellinen huippu tuli "
             "12.6.2015, minkä jälkeen indeksi laski yli 40 % (oranssit pisteet)."),
      figure("kuva3_ikkunat.png",
             "<b>Kuva 3.</b> Samat tiedot ikkunoittain. Jokainen vaakaviiva on yksi sovitusikkuna, "
             "joka päättyy 1.6.2015. Sinisten ikkunoiden sovitukset läpäisivät suodattimen, ja "
             "punaiset merkit ovat niiden <i>t<sub>c</sub></i>-arviot. Luottamusindikaattori oli "
             "7/41 ≈ 17 %. Ikkunoita on 41 eikä 42, koska kolmen vuoden aineistossa oli vain 727 kauppapäivää.")]

    # 4
    s += [P("4  Kuplan havaitsemisen ehdot", H1), P("4.1  Sovituksen suodatin", H2), P(
        "Optimointi löytää aina jonkin parhaan sovituksen myös satunnaisesta sarjasta. Siksi "
        "jokainen sovitus tarkistetaan ehdoilla, jotka sulkevat pois fysikaalisesti "
        "mielettömät ja tilastollisesti heikot sovitukset. Värähtelyjen voimakkuutta suhteessa "
        "trendiin mittaa vaimennus (<i>damping</i>), ja värähtelyjen määrää ikkunassa "
        "puolijaksojen lukumäärä:"),
      eq(r"D = \frac{m\,|B|}{\omega\,|C|},\quad |C|=\sqrt{C_1^2+C_2^2},\qquad\qquad "
         r"O = \frac{\omega}{\pi}\ln\frac{t_c-t_1}{t_c-t_2}"),
      P("Sovituksen tarkkuutta mitataan log-hinnan jäännösten neliökeskiarvolla"),
      eq(r"\mathrm{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\left(y_i-\hat y_i\right)^2}"),
      P("Taulukossa 1 ovat sovelluksen käyttämät rajat. Ehto <i>D</i> ≥ 1 takaa likimain, että "
        "yhtälön (3) riskifunktio pysyy ei-negatiivisena. Zhang, Zhang ja Sornette (2016) "
        "käyttävät tätä rajaa, mutta tämän sovelluksen kalibroinnissa se hylkäsi seitsemän "
        "kahdeksasta tunnetusta kuplasta. Siksi käytössä on Wheatleyn ym. (2019) Bitcoin-tutkimuksen "
        "raja <i>D</i> ≥ 0.5 ja sen väljempi <i>ω</i>-alue. Ehto <i>O</i> ≥ 2.5 estää mallia "
        "selittämästä yksittäistä heilahdusta ”värähtelyksi”."),
      table([["Ehto", "Raja", "Peruste ja lähde"],
             ["eksponentti <i>m</i>", "0.1 &lt; <i>m</i> &lt; 0.9",
              "kasvu kiihtyy, mutta hinta pysyy äärellisenä (Zhang ym. 2016)"],
             ["log-taajuus <i>ω</i>", "4 &lt; <i>ω</i> &lt; 25",
              "realistinen värähtely (Wheatley ym. 2019)"],
             ["vaimennus <i>D</i>", "<i>D</i> ≥ 0.5", "värähtelyt eivät hallitse trendiä (Wheatley ym. 2019)"],
             ["puolijaksot <i>O</i>", "<i>O</i> ≥ 2.5", "aitoa värähtelyä, ei kohinaa (Zhang ym. 2016)"],
             ["kriittinen hetki", "<i>t</i><sub>2</sub> &lt; <i>t<sub>c</sub></i> ≤ <i>t</i><sub>2</sub> + 0.13Δ<i>t</i>",
              "ennuste on lähellä ja tulevaisuudessa (Zhang ym. 2016)"],
             ["sovitusvirhe", "RMSE ≤ 0.15", "kalibroitu testikuplilla; kryptovaluutat ovat volatiileja"],
             ["suunta", "<i>B</i> &lt; 0 / <i>B</i> &gt; 0", "kupla / antikupla"]],
            [3.2 * cm, 4.6 * cm, TEXT_WIDTH - 7.8 * cm]),
      P("<b>Taulukko 1.</b> Yksittäisen sovituksen hyväksymisehdot.", CAPTION),
      P("4.2  Hinnannousun ehto", H2), P(
        "LPPLS-muoto voi löytyä myös hitaasta ja vaatimattomasta noususta. Kuplalta edellytetään "
        "siksi lisäksi suurta toteutunutta nousua. Greenwood, Shleifer ja You (2019) tutkivat "
        "toimialaportfolioita vuosilta 1926–2014. Kun nousu kahden vuoden aikana oli 100 %, "
        "40 %:n romahduksen todennäköisyys seuraavien kahden vuoden aikana oli noin 53 %. "
        "50 %:n nousulla todennäköisyys oli noin 20 %. Sovellus laskee nousun kahden vuoden "
        "pohjasta:"),
      eq(r"R(t_2) = \frac{p(t_2)}{\min_{\,t_2-730\,\mathrm{pv}\ \leq\ t\ \leq\ t_2}\, p(t)} - 1"),
      P("Kuplalta vaaditaan <i>R</i> ≥ 1 eli hinnan kaksinkertaistuminen. Antikuplalta vaaditaan "
        "vastaavasti vähintään 50 %:n lasku kahden vuoden huipusta. Log-asteikolla molemmat ovat "
        "yhtä suuria muutoksia (ln 2)."),
      P("4.3  Luokittelu ja seuranta", H2), P(
        "Lopullinen luokitus yhdistää luottamusindikaattorin ja hinnannousun (taulukko 2). "
        "Kuplaksi luokiteltu tilanne tallennetaan tietokantaan. Tallennettava ennuste jäädytetään: "
        "parametreja ei myöhemmin päivitetä, vaan ennustetta verrataan uuteen dataan. Seurannassa "
        "etsitään huippu <i>t</i>* havaintopäivän ja ennustevälin lopun välistä. Kupla on "
        "<i>toteutunut</i>, jos huippua seuraa 90 päivän sisällä vähintään 15 %:n pudotus, eli "
        "1 − min <i>p</i>(<i>s</i>)/<i>p</i>(<i>t</i>*) ≥ 0.15. Tila on <i>ei toteutunut</i>, jos "
        "ennusteväli (vähintään ±30 päivää) ohitetaan ilman pudotusta, ja muuten "
        "<i>odottaa</i>."),
      table([["Tila", "Ehdot", "Toiminto"],
             ["kupla", "CI ≥ 10 %, mediaani-<i>t<sub>c</sub></i> ≤ 6 kk ja <i>R</i> ≥ 100 %",
              "tallennus ja seuranta"],
             ["lähellä", "CI ≥ 5 % ja <i>R</i> ≥ 50 %", "näytetään taulukossa"],
             ["ei", "muut", "–"]],
            [2.2 * cm, 8.2 * cm, TEXT_WIDTH - 10.4 * cm]),
      P("<b>Taulukko 2.</b> Skannauksen luokittelu.", CAPTION)]

    # 5
    s += [P("5  Kalibrointi ja rajoitukset", H1), P(
        "Raja-arvot valittiin kokeilemalla eri yhdistelmiä kahdeksalla historiallisella kuplalla "
        "ja yhdellätoista vertailutapauksella (taulukko 3). Kuusi kahdeksasta kuplasta tunnistui, "
        "eikä yksikään vertailutapaus luokittunut kuplaksi. Vertailutapauksia olivat S&amp;P 500 "
        "vuosina 2007 ja 2019, DAX 2014 sekä yhdeksän indeksiä lokakuussa 2026, joista NYSE FANG+ "
        "luokittui tilaan ”lähellä”. Kriittisen hetken arvio osui 0–4 viikon päähän todellisesta "
        "huipusta. Nikkei 1989 jäi tunnistamatta, koska sen nousu kahdessa vuodessa oli vain 69 %. "
        "Bitcoin maaliskuussa 2021 jäi tunnistamatta, koska vain harva ikkuna läpäisi suodattimen."),
      table([["Tapaus (tarkastelupäivä)", "CI", "Nousu 2 v", "Tulos", "Ennuste <i>t<sub>c</sub></i>", "Todellinen huippu"],
             ["Bitcoin 1.12.2017", "21 %", "+2956 %", "kupla", "2.12.2017", "16.12.2017"],
             ["Shanghai 1.10.2007", "15 %", "+414 %", "kupla", "7.11.2007", "16.10.2007"],
             ["Shanghai 10.10.2007", "17 %", "+435 %", "kupla", "24.10.2007", "16.10.2007"],
             ["Shanghai 1.6.2015", "17 %", "+148 %", "kupla", "7.6.2015", "12.6.2015"],
             ["Nasdaq 15.2.2000", "31 %", "+212 %", "kupla", "16.2.2000", "10.3.2000"],
             ["Nasdaq 1.3.2000", "40 %", "+237 %", "kupla", "4.3.2000", "10.3.2000"],
             ["Nikkei 225 15.11.1989", "0 %", "+69 %", "ei", "–", "29.12.1989"],
             ["Bitcoin 15.3.2021", "2 %", "+1311 %", "ei", "–", "13.4.2021"]],
            [4.4 * cm, 1.3 * cm, 1.8 * cm, 1.4 * cm, 2.6 * cm, TEXT_WIDTH - 11.5 * cm]),
      P("<b>Taulukko 3.</b> Historialliset testikuplat nykyisillä ehdoilla.", CAPTION),
      P("Tuloksia on tulkittava varoen. Rajat valittiin samoilla tapauksilla, joilla niitä "
        "testattiin, joten osuvuus uusilla aineistoilla on todennäköisesti heikompi. Parametri "
        "<i>t<sub>c</sub></i> on tunnetusti huonosti määräytyvä: kuplan alku on helpompi tunnistaa "
        "kuin sen loppu, ja eri ikkunat antavat hajanaisia arvioita (Zhang ym. 2016). Malli "
        "kuvaa sisäsyntyisiä kuplia, joten se ei ennakoi ulkoisia shokkeja kuten pandemiaa tai "
        "sotaa. Kupla voi myös päättyä hitaaseen laskuun. Lisäksi Yahoo Financen data voi "
        "sisältää puutteita. Sovellus on tarkoitettu tutkimus- ja opiskelukäyttöön, eikä sen "
        "tulos ole sijoitussuositus.")]

    # Lähteet
    refs = [
        "Filimonov, V. &amp; Sornette, D. (2013). A stable and robust calibration scheme of the "
        "log-periodic power law model. <i>Physica A</i>, 392(17), 3698–3707.",
        "Greenwood, R., Shleifer, A. &amp; You, Y. (2019). Bubbles for Fama. <i>Journal of Financial "
        "Economics</i>, 131(1), 20–43. https://www.nber.org/papers/w23191",
        "Johansen, A., Ledoit, O. &amp; Sornette, D. (2000). Crashes as critical points. "
        "<i>International Journal of Theoretical and Applied Finance</i>, 3(2), 219–255.",
        "Johansen, A. &amp; Sornette, D. (2010). Shocks, crashes and bubbles in financial markets. "
        "<i>Brussels Economic Review</i>, 53(2), 201–253. https://arxiv.org/abs/cond-mat/0210509",
        "Nelder, J. A. &amp; Mead, R. (1965). A simplex method for function minimization. "
        "<i>The Computer Journal</i>, 7(4), 308–313.",
        "Sornette, D. (2003). <i>Why Stock Markets Crash: Critical Events in Complex Financial "
        "Systems</i>. Princeton University Press.",
        "Wheatley, S., Sornette, D., Huber, T., Reppen, M. &amp; Gantner, R. N. (2019). Are Bitcoin "
        "bubbles predictable? Combining a generalized Metcalfe’s law and the log-periodic power law "
        "singularity model. <i>Royal Society Open Science</i>, 6(6), 180538. "
        "https://arxiv.org/abs/1803.05663",
        "Zhang, Q., Zhang, Q. &amp; Sornette, D. (2016). Early warning signals of financial crises "
        "with multi-scale quantile regressions of log-periodic power law singularities. "
        "<i>PLoS ONE</i>, 11(11), e0165819. https://doi.org/10.1371/journal.pone.0165819",
    ]
    s += [P("Lähteet", H1)]
    hang = ParagraphStyle("ref", parent=SMALL, leftIndent=0.6 * cm, firstLineIndent=-0.6 * cm,
                          alignment=0, spaceAfter=3)
    s += [P(r, hang) for r in refs]
    return s


def main():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm,
                            topMargin=2.0 * cm, bottomMargin=2.0 * cm,
                            title="LPPLS-kuplaskanneri: teoria ja havaitsemisen ehdot",
                            author="LPPLS-kuplaskanneri", subject="LPPLS-malli ja kuplien havaitseminen")
    doc.build(story(), onFirstPage=on_page, onLaterPages=on_page)
    print(OUT)


if __name__ == "__main__":
    main()
