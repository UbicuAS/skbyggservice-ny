#!/usr/bin/env python3
"""
Bygger nettsiden til SK Byggservice AS.

All tekst, alle metabeskrivelser og alle strukturerte data ligger i denne fila.
Skriptet skriver ferdige, statiske HTML-filer ut i prosjektmappa. Det trengs
ingen server eller rammeverk for å vise dem.

    python bygg.py

Se README.md for forhåndsvisning kontra drift.
"""

import hashlib
import html
import json
import re
from datetime import date, timedelta
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # bildemål slås opp for srcset; uten Pillow faller vi tilbake
    Image = None

ROT = Path(__file__).resolve().parent

# --- Faste opplysninger om selskapet ---------------------------------------
# Hentet fra Enhetsregisteret og kundens Facebook-side 7. oktober 2026
# (org.nr. 925 496 774). Telefon og e-post er de Facebook-siden oppgir.
# Tjenestene skal bekreftes av kunden før lansering.
# Gateadresse vises ikke på siden før kunden har bestemt det.
FIRMA = "SK Byggservice AS"
KORTNAVN = "SK Byggservice"
ORGNR = "925 496 774"
POSTNR = "2388"
POSTSTED = "Brumunddal"
KOMMUNE = "Ringsaker"
FYLKE = "Innlandet"
TLF_VIS = "415 73 173"
TLF_URI = "+4741573173"
EPOST = "steffen@skbyggservice.no"
STIFTET = 2020
ANSATTE = 7

# --- Forhåndsvisning kontra drift -------------------------------------------
# skbyggservice.ubicu.cloud er en forhåndsvisning for kunden, ikke en side i
# drift. Den skal ikke dukke opp i Google. Denne ene bryteren styrer alt som
# må av og på samtidig:
#
#   1. noindex, nofollow, noarchive i <head> på hver side
#   2. robots.txt uten sitemap-henvisning (se kommentaren i bygg_robots)
#   3. Synlig stripe nederst på hver side
#   4. Domenet i canonical, og:url, og:image, sitemap og JSON-LD
#
# Den dagen kunden godkjenner: sett FORHANDSVISNING = False, kjør bygg.py, og
# legg filene ut på kundens domene. Se README.md, «Lansering».
FORHANDSVISNING = True

FORHANDSVISNING_DOMENE = "https://skbyggservice.ubicu.cloud"
PRODUKSJONSDOMENE = "https://skbyggservice.no"  # kundens domene – bekreftes før lansering
DOMENE = FORHANDSVISNING_DOMENE if FORHANDSVISNING else PRODUKSJONSDOMENE

# Kontaktskjemaet trenger en mottaker på serveren (f.eks. skjema.php på et
# webhotell). Til den finnes, sender skjemaet ingenting: knappen er ikke en
# send-knapp, og skriptet forklarer hvordan man tar kontakt i stedet. Ingen
# opplysninger forlater nettleseren.
SKJEMA_AKTIVT = False
SKJEMA_MOTTAKER = "/skjema.php"

ROBOTS_META = (
    '<meta name="robots" content="noindex, nofollow, noarchive">'
    if FORHANDSVISNING
    else '<meta name="robots" content="index, follow, max-image-preview:large, '
    'max-snippet:-1, max-video-preview:-1">'
)

# Siden laster bare egne filer. GitHub Pages kan ikke sette HTTP-headere, så
# innholdssikkerheten står som meta-tagg. Inline stil og skript er ikke lov.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; font-src 'self'; media-src 'self'; "
    "connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; upgrade-insecure-requests"
)

# Banneret henger over toppfeltet og følger med når man ruller.
BANNER = (
    f'''<div class="forhandsvisning" role="note">
<strong>Forhåndsvisning</strong><span class="forhandsvisning__sep" aria-hidden="true">·</span>
<span class="forhandsvisning__lang">Utkast til ny nettside for {FIRMA}, laget av Ubicu AS. Ikke publisert – siden er skjult for søkemotorer.</span>
<span class="forhandsvisning__kort">Utkast – ikke publisert</span>
</div>'''
    if FORHANDSVISNING
    else ""
)

# --- Innhold ----------------------------------------------------------------
NAV = [
    ("/#tjenester", "Tjenester"),
    ("/prosjekter/", "Prosjekter"),
    ("/#om-oss", "Om oss"),
    ("/#prosess", "Slik jobber vi"),
    ("/samarbeidspartnere/", "Samarbeid"),
]

# Samarbeidspartnere. Ubicu: teksten bygger på Ubicus egen beskrivelse på ubicu.no
# (tegninger, ansvarlig søker, nabovarsel, 3D-visualisering). Logoen er den hvite
# varianten fra Ubicus logopakke, uendret (profilmanualen: -white på mørk bunn).
UBICU_URL = "https://ubicu.no"
SAMARBEIDSPARTNERE = [
    {
        "id": "ubicu",
        "navn": "Ubicu AS",
        "fag": "Byggesøknader og tegninger",
        "logo": "merkevare/ubicu-logo-hvit.svg",
        "logo_mal": (362, 101),
        "url": UBICU_URL,
        "lenketekst": "ubicu.no",
        "tekst": (
            "Trenger jobben byggesøknad, gjør vi den sammen med Ubicu. De lager tegningene, "
            "sender nabovarsel og tar rollen som ansvarlig søker overfor kommunen – med "
            "3D-visualisering, så du ser bygget før det står der. Så bygger vi."
        ),
    },
]

# (nøkkel, tittel, tekst). Nøkkelen kobler raden til valget i skjemaet.
TJENESTER = [
    (
        "nybygg",
        "Nybygg og tilbygg",
        "Hus, hytter, garasjer og tilbygg. Vi reiser reisverket, tetter bygget "
        "og gjør det ferdig innvendig – med de samme folkene hele veien.",
    ),
    (
        "rehabilitering",
        "Rehabili&shy;tering",
        "Bad og vaskerom, vinduer og dører, kledning, etterisolering og innvendig "
        "oppussing. Vi tar vare på det som er godt, og bytter ut det som ikke er det.",
    ),
    (
        "massetransport",
        "Graving og masse&shy;transport",
        "Vi graver med egen gravemaskin – grøfter, drenering, tomt og uteområder – "
        "og kjører pukk, singel, matjord og andre masser til private og bedrifter, "
        "akkurat den typen og mengden du trenger.",
    ),
    (
        "grunnarbeid",
        "Drenering og grunnarbeid",
        "Ny drenering, grunnarbeid og planering rundt huset, med egne maskiner. "
        "Når jobben trenger mer enn to hender, stiller vi med utstyret.",
    ),
]

FACEBOOK = "https://www.facebook.com/SKbyggserviceas"

# Sentral godkjenning (DiBK), kontrollert i det offentlige registeret 8. okt 2026.
# Siden skal aldri påstå en godkjenning som har gått ut: bygget stopper når datoen
# er passert, og varsler 60 dager før. Fornyes den: sjekk registeret, rett datoen.
SENTRAL_GODKJENNING = {
    "gyldig_til": date(2027, 2, 19),
    "register": f"https://sgregister.dibk.no/enterprises/{ORGNR.replace(' ', '')}",
    "tiltaksklasse": 1,
    # DiBKs offisielle merke, sort boks med gull krone og tekst (primærvarianten).
    # Brukes uendret – DiBK tillater ikke endret form, farge eller rotasjon.
    "merke": "merkevare/sentralt-godkjent.png",
    "omraader": [
        "Tømrerarbeid og montering av trekonstruksjoner",
        "Veg- og grunnarbeider",
        "Vannforsynings- og avløpsanlegg",
        "Landskapsutforming",
    ],
}
# Gaselle-bedrift, kåret av Dagens Næringsliv (opplyst av Marius 8. okt 2026)
GASELLE_AAR = 2025

# Prosjektene er hentet fra kundens egen Facebook-side 7. okt 2026, nyeste først.
# «sitat» er det firmaet selv skrev i innlegget. Der det mangler, er tittel,
# ingress og arbeid skrevet av oss ut fra bildene og må bekreftes av kunden.
# «tid» er året innlegget ble publisert. Sted oppgis bare der firmaet selv har
# oppgitt det, og aldri mer presist enn kommune. Aldri adresse, kundenavn,
# husnummer, bilnummer eller personer. «forside»: vises blant de tre på forsiden.
# Nye bilder: verktoy/lag_bilder.py <bilde> prosjekt-<navn> --bredder 480,800,<bredde>
PROSJEKTER = [
    {
        "slug": "bad-vaskerom-og-drenering",
        "forside": True,
        "tittel": "Nytt bad, vaskerom og drenering",
        "sted": FYLKE,
        "tid": "2026",
        "sitat": "Her fikk kunden nytt bad/vaskerom og ny drenering",
        "ingress": "Et prosjekt med to sider: innvendig et helt nytt bad og vaskerom, "
                   "utvendig ny drenering rundt grunnmuren, så kjelleren holder seg tørr.",
        "arbeid": [
            "Nytt bad med walk-in-dusj og speil med lys",
            "Vaskerom med vaskemaskin og tørketrommel i egen benk",
            "Graving langs grunnmuren med egen gravemaskin",
            "Grunnmursplast, drensrør i pukk og ny kum",
        ],
        "bilder": [
            ("prosjekt-bad-1", "Nytt bad med svart walk-in-dusj, rundt speil med lys og servantskap i eik"),
            ("prosjekt-vaskerom-1", "Vaskerom med vaskemaskin og tørketrommel i svart benk, med døra åpen inn til badet"),
            ("prosjekt-drenering-2", "Gravemaskin i arbeid langs grunnmuren, med ny kum og grunnmursplast"),
            ("prosjekt-drenering-1", "Smal grøft langs grunnmuren med grunnmursplast og drensrør i pukk"),
        ],
    },
    {
        "slug": "terrasse-trapper-og-ferdigplen-hamar",
        "tittel": "Terrasse, trapper og ferdigplen",
        "sted": "Hamar",
        "tid": "2026",
        "sitat": "Bilder av ferdig prosjekt på Hamar",
        "ingress": "Et helt uteområde gjort ferdig på én gang: ny terrasse med brede trapper "
                   "og rekkverk, drenering og ferdigplen, og asfalt der bilen skal stå.",
        "arbeid": [
            "Drenering",
            "Terrasse",
            "Ferdigplen",
            "Fiberpussing",
            "Kjellervinduer og lysekasser",
            "Masseutskifting og asfaltering",
        ],
        "bilder": [
            ("prosjekt-terrasse-1", "Bred trapp i terrassebord opp til ny terrasse med rekkverk, foran et lyseblått hus"),
            ("prosjekt-terrasse-2", "Ny terrasse med trapp og rekkverk, sett fra den nylagte ferdigplenen"),
            ("prosjekt-terrasse-3", "Trapp og terrasse langs husveggen, med pukk og ny plen langs hekken"),
        ],
    },
    {
        "slug": "stottemur-og-nytt-uteomrade",
        "tittel": "Støttemur og nytt uteområde",
        "sted": None,
        "tid": "2025",
        "sitat": None,
        "ingress": "Støttemur i betongblokker, masseutskifting og planering med ny matjord – "
                   "et ryddig uteområde klart for plen.",
        "arbeid": ["Støttemur i betongblokker", "Masseutskifting", "Planering og ny matjord"],
        "bilder": [
            ("prosjekt-stottemur-2", "Gult hus med nyplanert uteområde med matjord, klart for plen"),
            ("prosjekt-stottemur-1", "Støttemur i grå betongblokker langs et nyplanert uteområde"),
        ],
    },
    {
        "slug": "nytt-bolighus-i-to-etasjer",
        "forside": True,
        "tittel": "Nytt bolighus i to etasjer",
        "sted": None,
        "tid": "2025",
        "sitat": None,
        "ingress": "Et nytt hus med mørk stående kledning og balkong i tre. Innvendig lyse gulv, "
                   "malte panelvegger og trapp med svart rekkverk.",
        "arbeid": ["Utvendig kledning og balkong", "Vinduer og listverk", "Panel og gulv innvendig", "Trapp med rekkverk"],
        "bilder": [
            ("prosjekt-nybygg-1", "Nytt bolighus i to etasjer med mørk stående kledning og balkong i tre"),
            ("prosjekt-nybygg-2", "Trapperom med grønne panelvegger, lyst gulv og svart rekkverk"),
            ("prosjekt-nybygg-3", "Stue med tre store vinduer, mørke panelvegger og lyst gulv"),
        ],
    },
    {
        "slug": "garasjebygg-med-fem-porter",
        "tittel": "Garasjebygg med fem porter",
        "sted": None,
        "tid": "2025",
        "sitat": None,
        "ingress": "Et stort garasjebygg i tre med fem leddporter og en åpen langside for lagring – "
                   "fra bindingsverk og takstoler til ferdig kledning.",
        "arbeid": ["Bindingsverk og takstoler", "Utvendig kledning", "Montering av leddporter", "Åpen langside"],
        "bilder": [
            ("prosjekt-garasjebygg-1", "Langt hvitt garasjebygg med fem leddporter"),
            ("prosjekt-garasjebygg-2", "Garasjebygget innvendig med takstoler og bindingsverk"),
            ("prosjekt-garasjebygg-3", "Den åpne langsiden av garasjebygget med stolper og takstoler"),
        ],
    },
    {
        "slug": "terrasse-med-overbygg",
        "tittel": "Terrasse med overbygg og levegg",
        "sted": None,
        "tid": "2024",
        "sitat": None,
        "ingress": "Ny terrasse med takoverbygg ved inngangen, levegger i spiler og bred trapp ned til hagen.",
        "arbeid": ["Terrasse", "Overbygg", "Levegger", "Trapp"],
        "bilder": [
            ("prosjekt-terrasse-overbygg-2", "Ny terrasse med hvitt takoverbygg, levegg i spiler og trapp"),
            ("prosjekt-terrasse-overbygg-1", "Terrasse med levegg i spiler, bord og stoler"),
        ],
    },
    {
        "slug": "nytt-tak-med-takstein",
        "tittel": "Nytt tak med takstein",
        "sted": None,
        "tid": "2023",
        "sitat": None,
        "ingress": "Taket lagt om fra bunnen: nytt undertak, sløyfer og lekter, og ny rød takstein.",
        "arbeid": ["Undertak", "Sløyfer og lekter", "Ny takstein", "Beslag rundt pipa"],
        "bilder": [
            ("prosjekt-tak-1", "Nytt tak med rød takstein og pipe med beslag"),
            ("prosjekt-tak-3", "Ferdig lagt rød takstein mot blå himmel"),
            ("prosjekt-tak-2", "Taket under arbeid, med undertak, sløyfer og lekter"),
        ],
    },
    {
        "slug": "ny-garasje-med-hems",
        "tittel": "Ny garasje med hems",
        "sted": None,
        "tid": "2022",
        "sitat": None,
        "ingress": "Romslig garasje med sort stående kledning, to store portåpninger og hems med trapp innvendig.",
        "arbeid": ["Bindingsverk og tak", "Sort stående kledning", "Hems med trapp", "Innvendig kledning"],
        "bilder": [
            ("prosjekt-garasje-2", "Ny garasje med sort stående kledning og to store portåpninger"),
            ("prosjekt-garasje-1", "Garasjen sett fra siden, med sort kledning og vinduer i gavlen"),
            ("prosjekt-garasje-3", "Garasjen innvendig med hems og trapp i tre"),
        ],
    },
    {
        "slug": "hagestue-med-glassvegger",
        "forside": True,
        "tittel": "Hagestue med glassvegger",
        "sted": None,
        "tid": "2022",
        "sitat": None,
        "ingress": "Lys hagestue med store glassfelt, mørk panel og utsikt over landskapet – "
                   "et ekstra rom til alle årstider.",
        "arbeid": ["Store glassfelt", "Mørk panel", "Himling med innfelt lys", "Gulv"],
        "bilder": [
            ("prosjekt-hagestue-3", "Hagestue med store glassfelt, mørk panel og planter, med utsikt over snødekt landskap"),
            ("prosjekt-hagestue-1", "Hagestue med mørk panel, lenestol og to stoler rundt et lite bord"),
            ("prosjekt-hagestue-2", "Hagestua under arbeid, med glassvegger mot terrassen"),
        ],
    },
    {
        "slug": "nytt-kjokken",
        "tittel": "Nytt kjøkken",
        "sted": None,
        "tid": "2020",
        "sitat": None,
        "ingress": "Montering av nytt kjøkken med grå fronter, benkeplate i tre og integrerte hvitevarer.",
        "arbeid": ["Montering av kjøkkenskap", "Benkeplate i tre", "Integrerte hvitevarer"],
        "bilder": [
            ("prosjekt-kjokken-1", "Nytt kjøkken med grå fronter, benkeplate i tre og integrert ovn og mikrobølgeovn"),
            ("prosjekt-kjokken-2", "Kjøkkenet under montering, med skapene på plass"),
        ],
    },
    {
        "slug": "etterisolering-av-yttervegg",
        "tittel": "Etterisolering av yttervegg",
        "sted": None,
        "tid": "2020",
        "sitat": None,
        "ingress": "Et bedre isolert og tettere hus: ny isolasjon i veggen og vindsperre utenpå – klart for ny kledning.",
        "arbeid": ["Ny isolasjon", "Vindsperre", "Tilpasning rundt vinduer"],
        "bilder": [
            ("prosjekt-etterisolering-2", "Yttervegg med ny isolasjon mellom stenderne"),
            ("prosjekt-etterisolering-1", "Samme vegg med vindsperre montert utenpå isolasjonen"),
        ],
    },
    {
        "slug": "massetransport-matjord-og-pukk",
        "tittel": "Massetransport: matjord og pukk",
        "sted": None,
        "tid": "2020",
        "sitat": None,
        "ingress": "Vi kjører masser med traktor og tipphenger – matjord til hagen og pukk til grunnarbeid, "
                   "levert der du trenger det.",
        "arbeid": ["Matjord", "Pukk", "Levering med tipphenger"],
        "bilder": [
            ("prosjekt-massetransport-1", "Tipphenger som har lagt av et lass med matjord"),
            ("prosjekt-massetransport-2", "Store hauger med pukk foran traktor og tipphenger"),
        ],
    },
]


def prosjektbeskrivelse(p, sted_tekst, maks=158):
    """Metabeskrivelse: tittel, sted, hvem – og så de første arbeidsoperasjonene som får plass."""
    tekst = f"{p['tittel']}{sted_tekst}, utført av {FIRMA} fra {POSTSTED}."
    arbeid = [a.rstrip(".") for a in p.get("arbeid", [])]
    if arbeid and len(f"{tekst} {arbeid[0]}.") <= maks:
        tekst = f"{tekst} {arbeid[0]}"
        for a in arbeid[1:]:
            neste = f"{tekst}, {a[0].lower()}{a[1:]}"
            if len(neste) + 1 > maks:
                break
            tekst = neste
        tekst += "."
    return tekst


def prosjektmeta(p, bilder=True):
    """«Hamar · 2026 · 4 bilder» – sted bare der det finnes."""
    deler = [p.get("sted"), p.get("tid")]
    if bilder:
        deler.append(f"{len(p['bilder'])} bilder")
    return " · ".join(d for d in deler if d)

STEG = [
    ("Befaring", "Vi kommer ut, ser på jobben og hører hva du vil ha. Da blir tilbudet riktig fra start."),
    ("Tilbud", "Du får et skriftlig tilbud med hva som skal gjøres, hva det koster og når vi kan begynne. "
               'Trenger jobben byggesøknad, ordner vi den sammen med <a href="/samarbeidspartnere/">Ubicu</a>.'),
    ("Bygging", "Vi holder deg oppdatert underveis, sier fra tidlig hvis noe endrer seg, og rydder etter oss."),
    ("Overlevering", "Vi går gjennom jobben sammen med deg før vi sier oss ferdige."),
]

# --- Ikoner -----------------------------------------------------------------
PIL_IKON = (
    '<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true" '
    'focusable="false"><path d="M2 8h11m-4.5-4.5L13 8l-4.5 4.5" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="square"/></svg>'
)
TLF_IKON = (
    '<svg width="17" height="17" viewBox="0 0 16 16" fill="none" aria-hidden="true" '
    'focusable="false"><path d="M14.5 11.4v2a1.3 1.3 0 0 1-1.5 1.3 13 13 0 0 1-5.6-2 '
    '12.8 12.8 0 0 1-4-4 13 13 0 0 1-2-5.7A1.3 1.3 0 0 1 2.7 1.5h2a1.3 1.3 0 0 1 1.3 '
    '1.2c.1.6.2 1.3.5 1.9a1.3 1.3 0 0 1-.3 1.4l-.9.8a10.7 10.7 0 0 0 4 4l.8-.9a1.3 1.3 '
    '0 0 1 1.4-.3c.6.3 1.2.4 1.9.5a1.3 1.3 0 0 1 1.1 1.3Z" stroke="currentColor" '
    'stroke-width="1.5" stroke-linejoin="round"/></svg>'
)
STJERNE = '<span class="stjerne" aria-hidden="true"></span>'
# Facebook-«f» (Remix Icon «facebook-fill», Apache 2.0), i tekstfargen
FB_IKON = (
    '<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path fill="currentColor" d="M14 13.5h2.5l1-4H14v-2c0-1.03 0-2 2-2h1.5V2.14c-.326-.043-1.557-.14-2.857-.14'
    'C11.928 2 10 3.657 10 6.7v2.8H7v4h3V22h4v-8.5z"/></svg>'
)
VEKST_IKON = (
    '<svg width="22" height="22" viewBox="0 0 16 16" fill="none" aria-hidden="true" '
    'focusable="false"><path d="M1.5 12.5l4.5-4.5 3 3 5.5-6M10 5h4.5v4.5" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="square"/></svg>'
)


# --- Hjelpere ---------------------------------------------------------------
def e(tekst):
    return html.escape(str(tekst), quote=True)


# Lange ord som ellers sprenger bredden på smale mobiler (320–375 px).
MYKE_DELINGER = {
    "Etterisolering": "Etter&shy;isolering",
    "Massetransport": "Masse&shy;transport",
    "Rehabilitering": "Rehabili&shy;tering",
    "Garasjebygg": "Garasje&shy;bygg",
}


def myk(tekst):
    """Escaper og legger inn myke orddelinger – bare til synlige overskrifter."""
    ut = e(tekst)
    for ord_, delt in MYKE_DELINGER.items():
        ut = ut.replace(ord_, delt)
    return ut


def innholdsmerke(rel):
    """Kort hash av en fils innhold, brukt som versjon i URL-en.

    GitHub Pages sender `cache-control: max-age=600`. Uten en versjon i URL-en
    viser nettleseren en gammel kopi etter en endring. Hashen endres bare når
    fila endres.
    """
    return hashlib.sha256((ROT / rel).read_bytes()).hexdigest()[:10]


_maal = {}


def dims(rel):
    if rel not in _maal:
        if Image is None:
            _maal[rel] = (1600, 900)
        else:
            with Image.open(ROT / rel) as im:
                _maal[rel] = im.size
    return _maal[rel]


def varianter(navn):
    """Alle webp-variantene av et bilde, sortert på bredde: [(bredde, url)]."""
    funnet = []
    for fil in (ROT / "bilder").glob(f"{navn}-*.webp"):
        m = re.fullmatch(re.escape(navn) + r"-(\d+)\.webp", fil.name)
        if m:
            rel = f"bilder/{fil.name}"
            funnet.append((dims(rel)[0], "/" + rel))
    if not funnet:
        raise SystemExit(f"Mangler bildevarianter for «{navn}» i bilder/ – kjør verktoy/lag_bilder.py")
    return sorted(funnet)


def bilde(navn, alt, sizes, klasse="", prioritet=False):
    kilder = varianter(navn)
    srcset = ", ".join(f"{u} {b}w" for b, u in kilder)
    # src peker på en mellomstor variant, så nettlesere uten srcset ikke henter den største
    mellom_b, mellom_u = kilder[min(len(kilder) - 1, len(kilder) // 2)]
    b, h = dims(mellom_u.lstrip("/"))
    attr = []
    if klasse:
        attr.append(f'class="{klasse}"')
    attr += [
        f'src="{mellom_u}"',
        f'srcset="{srcset}"',
        f'sizes="{sizes}"',
        f'width="{b}"',
        f'height="{h}"',
        f'alt="{e(alt)}"',
    ]
    attr += ['fetchpriority="high"', 'decoding="async"'] if prioritet else ['loading="lazy"', 'decoding="async"']
    return "<img " + " ".join(attr) + ">"


def json_ld(*blokker):
    ut = []
    for b in blokker:
        tekst = json.dumps(b, ensure_ascii=False, indent=1)
        ut.append('<script type="application/ld+json">\n' + tekst.replace("</", "<\\/") + "\n</script>")
    return "\n".join(ut)


ORGANISASJON = {
    "@context": "https://schema.org",
    "@type": "GeneralContractor",
    "@id": f"{DOMENE}/#firma",
    "name": FIRMA,
    "url": f"{DOMENE}/",
    "telephone": TLF_URI,
    "email": EPOST,
    "image": f"{DOMENE}/merkevare/delebilde.jpg",
    "foundingDate": str(STIFTET),
    "numberOfEmployees": {"@type": "QuantitativeValue", "value": ANSATTE},
    "identifier": {
        "@type": "PropertyValue",
        "propertyID": "Organisasjonsnummer",
        "value": ORGNR.replace(" ", ""),
    },
    "address": {
        "@type": "PostalAddress",
        "postalCode": POSTNR,
        "addressLocality": POSTSTED,
        "addressRegion": FYLKE,
        "addressCountry": "NO",
    },
    "description": (
        f"{FIRMA} er et snekker- og tømrerfirma fra {POSTSTED} i {KOMMUNE}. Nybygg, tilbygg, "
        f"rehabilitering, graving, drenering og massetransport for private og bedrifter i {FYLKE}."
    ),
    "slogan": "Bygget for å stå.",
    "logo": f"{DOMENE}/merkevare/logo.svg",
    "sameAs": [FACEBOOK],
    "areaServed": [
        {"@type": "AdministrativeArea", "name": KOMMUNE},
        {"@type": "AdministrativeArea", "name": "Hamar"},
        {"@type": "AdministrativeArea", "name": FYLKE},
    ],
    "hasOfferCatalog": {
        "@type": "OfferCatalog",
        "name": "Tjenester",
        "itemListElement": [
            {
                "@type": "Offer",
                "itemOffered": {
                    "@type": "Service",
                    "name": t[1].replace("&shy;", ""),
                    "description": t[2],
                    "areaServed": {"@type": "AdministrativeArea", "name": FYLKE},
                },
            }
            for t in TJENESTER
        ],
    },
    "knowsAbout": [t[1].replace("&shy;", "") for t in TJENESTER],
    "hasCredential": {
        "@type": "EducationalOccupationalCredential",
        "name": "Sentral godkjenning for ansvarsrett",
        "credentialCategory": "Sentral godkjenning",
        "url": SENTRAL_GODKJENNING["register"],
        "recognizedBy": {"@type": "GovernmentOrganization", "name": "Direktoratet for byggkvalitet", "url": "https://dibk.no"},
    },
    "award": f"Gaselle-bedrift {GASELLE_AAR} (Dagens Næringsliv)",
}

NETTSTED = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": f"{DOMENE}/#nettsted",
    "name": FIRMA,
    "url": f"{DOMENE}/",
    "inLanguage": "nb-NO",
    "publisher": {"@id": f"{DOMENE}/#firma"},
}


# --- Felles deler -----------------------------------------------------------
def svg_maal(fil):
    """Bredde og høyde fra width/height i en SVG i merkevare/."""
    tekst = (ROT / "merkevare" / fil).read_text(encoding="utf-8")[:400]
    b = re.search(r'width="([0-9.]+)"', tekst)
    h = re.search(r'height="([0-9.]+)"', tekst)
    if not (b and h):
        raise SystemExit(f"Mangler width/height i merkevare/{fil}")
    return round(float(b.group(1))), round(float(h.group(1)))


def logo(etikett=f"{FIRMA} – til forsiden", fil="logo.svg", klasse="logo"):
    # Kundens egen logo, sporet fra Facebook-forsidebildet av verktoy/spor_logo.py.
    b, h = svg_maal(fil)
    return (
        f'<a class="{klasse}" href="/" aria-label="{e(etikett)}">'
        f'<img src="/merkevare/{fil}?v={innholdsmerke("merkevare/" + fil)}" width="{b}" height="{h}" alt=""></a>'
    )


def topp():
    lenker = "".join(f'<a href="{u}">{n}</a>' for u, n in NAV)
    return f'''<header class="topp">
{BANNER}
<div class="ramme topp__inner">
{logo()}
<nav class="meny" aria-label="Hovedmeny">{lenker}</nav>
<div class="topp__hoyre">
<a class="topp__fb" href="{FACEBOOK}" rel="noopener" aria-label="{FIRMA} på Facebook">{FB_IKON}</a>
<a class="topp__tlf" href="tel:{TLF_URI}" aria-label="Ring oss på {TLF_VIS}">{TLF_IKON}<span>{TLF_VIS}</span></a>
<a class="knapp knapp--liten" href="/#kontakt">Be om befaring</a>
<button class="luke" type="button" aria-expanded="false" aria-controls="mobilmeny" aria-label="Åpne menyen"><span></span></button>
</div>
</div>
</header>
<div class="mobilmeny" id="mobilmeny">
<nav aria-label="Meny for mobil">{lenker}<a href="/#kontakt">Kontakt</a></nav>
<a class="knapp" href="tel:{TLF_URI}">{TLF_IKON}Ring {TLF_VIS}</a>
<a class="mobilmeny__fb" href="{FACEBOOK}" rel="noopener">{FB_IKON}Facebook</a>
<p class="mobilmeny__kontakt"><a href="mailto:{EPOST}">{EPOST}</a><br>{POSTSTED} · {KOMMUNE}</p>
</div>'''


def bunn():
    sider = "".join(f'<li><a href="{u}">{n}</a></li>' for u, n in NAV)
    return f'''<footer class="bunn">
<div class="ramme bunn__topp">
<div>
{logo(FIRMA, "logo-skilt.svg", "logo logo--skilt")}
<p class="bunn__om">Snekkerfirma fra {POSTSTED}. Nybygg, tilbygg, rehabilitering, graving, drenering og massetransport i {KOMMUNE} og omegn.</p>
</div>
<div>
<h2>Kontakt</h2>
<ul>
<li><a href="tel:{TLF_URI}">{TLF_VIS}</a></li>
<li><a href="mailto:{EPOST}">{EPOST}</a></li>
<li><a href="{FACEBOOK}" rel="noopener">Facebook</a></li>
<li>{POSTNR} {POSTSTED}</li>
</ul>
</div>
<div>
<h2>Sider</h2>
<ul>{sider}<li><a href="/personvern/">Personvern</a></li></ul>
</div>
</div>
<svg class="bunn__kjempe" viewBox="0 0 1000 118" aria-hidden="true" focusable="false"><text x="0" y="104" textLength="1000" lengthAdjust="spacingAndGlyphs">SK BYGGSERVICE</text></svg>
<div class="ramme bunn__strek">
<p>© <span id="aarstall">2026</span> {FIRMA} · Org.nr. {ORGNR}</p>
<p><a href="/personvern/">Personvern</a> · Nettside laget i samarbeid med <a href="{UBICU_URL}" rel="noopener">Ubicu AS</a></p>
</div>
</footer>
<script src="/js/side.js?v={innholdsmerke('js/side.js')}" defer></script>'''


def side(filsti, tittel, beskrivelse, kanonisk, innhold, ld=(), ekstra_hode="", kropp_klasse=""):
    strukturert = json_ld(ORGANISASJON, NETTSTED, *ld)
    klasser = " ".join(k for k in (kropp_klasse, "har-banner" if FORHANDSVISNING else "") if k)
    klasse = f' class="{klasser}"' if klasser else ""
    dok = f'''<!DOCTYPE html>
<html lang="nb-NO">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{e(tittel)}</title>
<meta name="description" content="{e(beskrivelse)}">
{f'<link rel="canonical" href="{DOMENE}{kanonisk}">' if kanonisk else ""}
{ROBOTS_META}
<meta name="theme-color" content="#0d0c0a">
<meta name="format-detection" content="telephone=no">

<meta property="og:type" content="website">
<meta property="og:site_name" content="{FIRMA}">
<meta property="og:locale" content="nb_NO">
<meta property="og:title" content="{e(tittel)}">
<meta property="og:description" content="{e(beskrivelse)}">
{f'<meta property="og:url" content="{DOMENE}{kanonisk}">' if kanonisk else ""}
<meta property="og:image" content="{DOMENE}/merkevare/delebilde.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Illustrasjon: råbygg i tre med arbeidslys og sirkelsag">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" href="/merkevare/favicon.svg?v={innholdsmerke('merkevare/favicon.svg')}" type="image/svg+xml">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/fonter/inter-900.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonter/inter-400.woff2" as="font" type="font/woff2" crossorigin>
{ekstra_hode}
<link rel="stylesheet" href="/css/stil.css?v={innholdsmerke('css/stil.css')}">
{strukturert}
</head>
<body{klasse}>
<a class="hopplenke" href="#innhold">Hopp til innholdet</a>
{topp()}
<main id="innhold">
{innhold}
</main>
{bunn()}
</body>
</html>
'''
    ut = ROT / filsti
    ut.parent.mkdir(parents=True, exist_ok=True)
    ut.write_text(dok, encoding="utf-8", newline="\n")


# --- Forsiden ---------------------------------------------------------------
def hero():
    video = ROT / "bilder" / "hero.mp4"
    if video.exists():
        # Video fra Higgsfield eller kunden. Bildet er plakat og reserve.
        plakat = varianter("hero")[-2][1]
        media = (
            f'<video class="hero__media" autoplay muted loop playsinline preload="metadata" '
            f'poster="{plakat}" aria-hidden="true"><source src="/bilder/hero.mp4" type="video/mp4"></video>'
        )
    else:
        media = bilde(
            "hero",
            "Illustrasjon: råbygg i tre om kvelden, med arbeidslys og sirkelsag på en bukk",
            "100vw",
            klasse="hero__media",
            prioritet=True,
        )
    return f'''<section class="hero" aria-labelledby="hero-tittel">
<div class="hero__bakgrunn">
{media}
<div class="hero__lys" aria-hidden="true"></div>
<canvas class="hero__flis" aria-hidden="true"></canvas>
<div class="hero__skygge" aria-hidden="true"></div>
</div>
<div class="ramme hero__innhold">
<h1 class="hero__h1" id="hero-tittel"><span class="stikk hero__stikk"><span class="prikk" aria-hidden="true"></span>Snekker · Tømrer · Graving · Massetransport – {POSTSTED}</span> <span class="hero__tittel"><span class="linje"><span>Bygget</span></span> <span class="linje"><span>for å</span></span> <span class="linje"><span class="hero__fyll">stå.</span></span></span></h1>
<div class="hero__under">
<p class="hero__ingress">{KORTNAVN} er snekkerfirmaet fra {POSTSTED} som tar jobben fra første spadetak til siste list – nybygg, tilbygg, rehabilitering, graving, drenering og massetransport.</p>
<div class="knapperad">
<a class="hero__godkjent" href="#godkjent"><img src="/{SENTRAL_GODKJENNING["merke"]}?v={innholdsmerke(SENTRAL_GODKJENNING["merke"])}" width="425" height="425" alt="Sentralt godkjent – se godkjenningen" decoding="async"></a>
<a class="knapp" href="#kontakt">Be om befaring {PIL_IKON}</a>
<a class="knapp knapp--tom" href="tel:{TLF_URI}">{TLF_IKON}{TLF_VIS}</a>
</div>
</div>
</div>
<div class="hero__fot">
<ul class="ramme hero__fakta">
<li><span>Etablert</span>{STIFTET}</li>
<li><span>Ansatte</span>{ANSATTE}</li>
<li><span>Base</span>{POSTSTED}, {FYLKE}</li>
<li><span>Gaselle</span>{GASELLE_AAR}</li>
</ul>
</div>
</section>'''


def baand():
    ord_ = ["Nybygg", "Tilbygg", "Rehabilitering", "Bad og vaskerom", "Drenering", "Graving", "Massetransport", "Pukk · Singel · Matjord"]
    gruppe = "".join(f"<span>{o}</span>{STJERNE}" for o in ord_)
    return f'''<div class="baand-ramme" aria-hidden="true">
<div class="baand"><div class="baand__spor"><div class="baand__gruppe">{gruppe}</div><div class="baand__gruppe">{gruppe}</div></div></div>
</div>'''


def tjenester():
    rader = []
    for i, (nokkel, tittel, tekst) in enumerate(TJENESTER, 1):
        rader.append(f'''<li class="tjeneste sig">
<a class="tjeneste__lenke" href="#kontakt" data-tjeneste="{nokkel}">
<span class="tjeneste__nr">{i:02d}</span>
<h3>{tittel}</h3>
<p class="tjeneste__tekst">{tekst}</p>
<span class="tjeneste__pil" aria-hidden="true">{PIL_IKON}</span>
<span class="usynlig">– be om befaring</span>
</a>
</li>''')
    return f'''<section class="seksjon tjenester" id="tjenester" aria-labelledby="tjenester-tittel" data-maal="1">
<div class="ramme">
<div class="seksjonstopp">
<p class="stikk"><span class="stikk__maal">1m</span> – Tjenester</p>
<h2 id="tjenester-tittel" class="sig">Hva vi gjør</h2>
<p class="seksjonstopp__ingress sig">Små og store oppdrag innen snekkerarbeid, graving og massetransport. Vi er sju ansatte med verktøy, gravemaskin og traktor, og tar oppdrag for både private og bedrifter.</p>
</div>
<ol class="tjenesteliste">
{''.join(rader)}
</ol>
</div>
</section>'''


KORT_SIZES = "(min-width: 960px) 33vw, (min-width: 620px) 50vw, 100vw"


def prosjektkort(p):
    navn, alt = p["bilder"][0]
    return f'''<a class="prosjektkort sig" href="/prosjekter/{p["slug"]}/">
<div class="prosjektkort__bilde">{bilde(navn, alt, KORT_SIZES)}</div>
<div class="prosjektkort__tekst">
<p class="prosjektkort__meta">{e(prosjektmeta(p))}</p>
<h3>{myk(p["tittel"])}</h3>
<span class="prosjektkort__lenke">Se prosjektet {PIL_IKON}</span>
</div>
</a>'''


def facebookkort():
    return f'''<a class="prosjektkort prosjektkort--fb sig" href="{FACEBOOK}" rel="noopener">
<div class="prosjektkort__tekst">
<p class="prosjektkort__meta">Facebook</p>
<h3>Flere prosjekter på Facebook</h3>
<p>Vi legger ut bilder fra jobbene våre fortløpende – bad, tilbygg, terrasser, drenering og masser.</p>
<span class="prosjektkort__lenke">Til Facebook-siden {PIL_IKON}</span>
</div>
</a>'''


def prosjekter():
    # Forsiden viser de tre nyeste. Er det færre enn tre, fylles plassen med
    # Facebook-kortet. Alle står på /prosjekter/.
    valgt = [p for p in PROSJEKTER if p.get("forside")][:3]
    valgt += [p for p in PROSJEKTER if p not in valgt][: 3 - len(valgt)]
    utvalg = [prosjektkort(p) for p in valgt]
    if len(utvalg) < 3:
        utvalg.append(facebookkort())
    fliser = "\n".join(utvalg)
    return f'''<section class="seksjon prosjekter" id="prosjekter" aria-labelledby="prosjekter-tittel" data-maal="2">
<div class="ramme">
<div class="seksjonstopp">
<p class="stikk"><span class="stikk__maal">2m</span> – Prosjekter</p>
<h2 id="prosjekter-tittel" class="sig">Arbeid vi står for</h2>
<p class="seksjonstopp__ingress sig">Et utvalg av jobbene vi har gjort. Klikk deg inn på et prosjekt for å se flere bilder og hva vi gjorde.</p>
</div>
<div class="prosjektgrid">
{fliser}
</div>
<div class="prosjekter__mer sig"><a class="knapp" href="/prosjekter/">Se flere prosjekter {PIL_IKON}</a></div>
</div>
</section>'''


def om_oss():
    return f'''<section class="seksjon om" id="om-oss" aria-labelledby="om-tittel" data-maal="3">
<div class="ramme">
<div class="om__grid">
<div>
<p class="stikk"><span class="stikk__maal">3m</span> – Om oss</p>
<h2 id="om-tittel" class="sig">Lokale folk.<br>Ordentlig arbeid.</h2>
</div>
<div class="om__tekst sig">
<p>{FIRMA} ble startet i {STIFTET} og holder til i {POSTSTED} i {KOMMUNE}. I dag er vi {ANSATTE} ansatte som tar alt fra små reparasjoner til hele bygg – og som stiller med gravemaskin og traktor når jobben krever det.</p>
<p>Hos oss snakker du med dem som faktisk gjør jobben. Vi holder avtaler, sier fra tidlig hvis noe endrer seg, og leverer arbeid vi gjerne setter navnet vårt på.</p>
</div>
</div>
<div class="tall">
<div class="sig"><b data-tell="{STIFTET}" data-fra="2000">{STIFTET}</b><span>Etablert</span></div>
<div class="sig"><b data-tell="{ANSATTE}">{ANSATTE}</b><span>Ansatte</span></div>
<div class="sig"><b data-tell="{len(TJENESTER)}">{len(TJENESTER)}</b><span>Fagområder</span></div>
</div>
{utmerkelser()}
</div>
</section>'''


def utmerkelser():
    g = SENTRAL_GODKJENNING
    omraader = "".join(f"<li>{e(o)}</li>" for o in g["omraader"])
    return f'''<div class="utmerket" id="godkjent">
<div class="utmerket__kort sig">
<img class="utmerket__godkjent" src="/{g["merke"]}?v={innholdsmerke(g["merke"])}" width="425" height="425" alt="Godkjenningsmerket: Sentralt godkjent" loading="lazy" decoding="async">
<h3>Sentralt godkjent</h3>
<p>Godkjent av Direktoratet for byggkvalitet som utførende i tiltaksklasse {g["tiltaksklasse"]} innen:</p>
<ul class="utmerket__liste">{omraader}</ul>
<a class="utmerket__lenke" href="{e(g["register"])}" rel="noopener">Se godkjenningen i registeret {PIL_IKON}</a>
</div>
<div class="utmerket__kort sig">
<span class="utmerket__merke">{VEKST_IKON}</span>
<h3>Gaselle-bedrift {GASELLE_AAR}</h3>
<p>Kåret av Dagens Næringsliv, som hvert år kårer Norges mest fremgangsrike bedrifter.</p>
</div>
</div>'''


def prosess():
    steg = "".join(
        f'<li class="sig"><span class="steg__nr" aria-hidden="true">{i:02d}</span><h3>{t}</h3><p>{x}</p></li>'
        for i, (t, x) in enumerate(STEG, 1)
    )
    return f'''<section class="seksjon prosess" id="prosess" aria-labelledby="prosess-tittel" data-maal="4">
<div class="ramme">
<div class="seksjonstopp">
<p class="stikk"><span class="stikk__maal">4m</span> – Slik jobber vi</p>
<h2 id="prosess-tittel" class="sig">Fire steg.<br>Ingen over&shy;raskelser.</h2>
</div>
<ol class="steg">{steg}</ol>
</div>
</section>'''


def skjema():
    valg = "".join(f'<option value="{k}">{t.replace("&shy;", "")}</option>' for k, t, _ in TJENESTER)
    if SKJEMA_AKTIVT:
        aapning = f'<form class="skjema" id="skjema" method="post" action="{SKJEMA_MOTTAKER}" data-aktiv="ja">'
        knapp = f'<button class="knapp skjema__send" type="submit">Send forespørsel {PIL_IKON}</button>'
    else:
        # Ikke en send-knapp: skjemaet kan ikke sendes noe sted, verken med eller uten skript.
        aapning = '<form class="skjema" id="skjema" data-aktiv="nei">'
        knapp = f'<button class="knapp skjema__send" type="button">Send forespørsel {PIL_IKON}</button>'
    return f'''{aapning}
<div class="felter-2">
<div class="felt"><label for="navn">Navn</label><input id="navn" name="navn" type="text" autocomplete="name" maxlength="100" required></div>
<div class="felt"><label for="telefon">Telefon</label><input id="telefon" name="telefon" type="tel" autocomplete="tel" inputmode="tel" maxlength="20" pattern="[0-9 +\\(\\)\\-]{{8,20}}" required></div>
</div>
<div class="felter-2">
<div class="felt"><label for="epost">E-post <span>(valgfritt)</span></label><input id="epost" name="epost" type="email" autocomplete="email" maxlength="120"></div>
<div class="felt"><label for="sted">Hvor er jobben?</label><input id="sted" name="sted" type="text" autocomplete="address-level2" maxlength="80" placeholder="F.eks. Brumunddal"></div>
</div>
<div class="felt"><label for="type">Hva gjelder det?</label><select id="type" name="type"><option value="">Velg</option>{valg}<option value="annet">Annet</option></select></div>
<div class="felt"><label for="melding">Fortell kort om jobben</label><textarea id="melding" name="melding" rows="5" maxlength="2000" required></textarea></div>
<div class="skjult-felt" aria-hidden="true"><label for="nettsted">La dette feltet stå tomt</label><input id="nettsted" name="nettsted" type="text" tabindex="-1" autocomplete="off"></div>
{knapp}
<p class="skjema__status" role="status" aria-live="polite"></p>
<p class="skjema__notis">Vi bruker opplysningene bare til å svare deg. Les mer om <a href="/personvern/">personvern</a>.</p>
</form>'''


def kontakt():
    return f'''<section class="seksjon kontakt" id="kontakt" aria-labelledby="kontakt-tittel" data-maal="5">
<div class="ramme kontakt__grid">
<div>
<p class="stikk"><span class="stikk__maal">5m</span> – Kontakt</p>
<h2 id="kontakt-tittel" class="sig">Har du en jobb til oss?</h2>
<p class="kontakt__ingress sig">Fortell kort hva du trenger hjelp til, så ringer vi deg tilbake. Vil du heller ringe selv, er det bare å slå på tråden.</p>
<a class="kontakt__tlf sig" href="tel:{TLF_URI}">{TLF_VIS}</a>
<ul class="kontakt__liste sig">
<li><a href="mailto:{EPOST}">{EPOST}</a></li>
<li>{POSTSTED} · {KOMMUNE} · {FYLKE}</li>
<li>Org.nr. {ORGNR}</li>
</ul>
</div>
<div class="sig">
{skjema()}
</div>
</div>
</section>'''


def bygg_forside():
    hero_kilder = varianter("hero")
    srcset = ", ".join(f"{u} {b}w" for b, u in hero_kilder)
    forhaand = (
        f'<link rel="preload" as="image" type="image/webp" imagesrcset="{srcset}" imagesizes="100vw" fetchpriority="high">'
        if not (ROT / "bilder" / "hero.mp4").exists()
        else ""
    )
    # Målebåndet fortsetter ned langs venstre kant. Hver seksjon starter på en
    # hel meter (1m – Tjenester, 2m – Prosjekter …). js/side.js tegner båndet
    # etter de faktiske posisjonene, og avlesningskroken viser hvor man er.
    maalt = "\n".join([tjenester(), prosjekter(), om_oss(), prosess(), kontakt()])
    maaler = '<div class="maaler" aria-hidden="true"><span class="maaler__tall">1,00</span></div>'
    # Målebåndet sett ovenfra (Higgsfield, illustrasjon): kroken er hektet på
    # bunnen av heroen, og huset står fast nederst i skjermen mens båndet trekkes
    # ut av det. Huset ligger i et spor så det kan være sticky (se stil.css).
    krok = (
        f'<img class="maalebaand-krok" src="/merkevare/maalebaand-krok.webp?v={innholdsmerke("merkevare/maalebaand-krok.webp")}" '
        'width="81" height="62" alt="" aria-hidden="true" decoding="async">'
    )
    hus = (
        '<div class="maalebaand-spor" aria-hidden="true">'
        f'<img class="maalebaand-hus" src="/merkevare/maalebaand-hus.webp?v={innholdsmerke("merkevare/maalebaand-hus.webp")}" '
        'width="168" height="310" alt="" decoding="async"></div>'
    )
    innhold = "\n".join([hero(), baand(), f'<div class="maalt">\n{krok}\n{hus}\n{maalt}\n</div>', maaler])
    side(
        "index.html",
        f"Snekker og tømrer i {POSTSTED} | {FIRMA}",
        f"{FIRMA} er snekkerfirmaet fra {POSTSTED}: nybygg, tilbygg, rehabilitering, "
        f"graving, drenering og massetransport i {KOMMUNE} og {FYLKE}.",
        "/",
        innhold,
        ekstra_hode=forhaand,
        kropp_klasse="forside",
    )


# --- Prosjektsider ----------------------------------------------------------
def brodsmuler_ld(smuler):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": navn, "item": f"{DOMENE}{url}"}
            for i, (navn, url) in enumerate(smuler, 1)
        ],
    }


def bygg_prosjektsider():
    for p in PROSJEKTER:
        bilder = "\n".join(
            f'<a class="prosjektside__bilde lysboks" href="{varianter(n)[-1][1]}" aria-label="Vis større: {e(alt)}">'
            f'{bilde(n, alt, KORT_SIZES)}</a>'
            for n, alt in p["bilder"]
        )
        arbeid = "".join(f"<li>{e(x)}</li>" for x in p["arbeid"])
        andre = "\n".join(prosjektkort(q) for q in PROSJEKTER if q is not p)
        url = f"/prosjekter/{p['slug']}/"
        sitat = (
            f'<blockquote class="prosjektside__sitat"><p>«{e(p["sitat"])}»</p>'
            "<footer>Fra Facebook-siden vår</footer></blockquote>"
            if p.get("sitat")
            else ""
        )
        sted_tittel = f" – {p['sted']}" if p.get("sted") else ""
        sted_tekst = f" i {p['sted']}" if p.get("sted") else ""
        innhold = f'''<article class="prosjektside">
<div class="ramme">
<nav class="brodsmuler" aria-label="Brødsmuler"><a href="/">Forside</a><span aria-hidden="true">/</span><a href="/prosjekter/">Prosjekter</a><span aria-hidden="true">/</span><span aria-current="page">{e(p["tittel"])}</span></nav>
<p class="stikk">Prosjekt · {e(prosjektmeta(p, bilder=False))}</p>
<h1>{myk(p["tittel"])}</h1>
<div class="prosjektside__topp">
<div>
<p class="prosjektside__ingress">{e(p["ingress"])}</p>
{sitat}
</div>
<div class="prosjektside__arbeid">
<h2>Dette gjorde vi</h2>
<ul class="hakeliste">{arbeid}</ul>
</div>
</div>
<div class="prosjektside__galleri">
{bilder}
</div>
<div class="prosjektside__cta">
<h2>Har du en lignende jobb?</h2>
<div class="knapperad"><a class="knapp" href="/#kontakt">Be om befaring {PIL_IKON}</a><a class="knapp knapp--tom" href="tel:{TLF_URI}">{TLF_IKON}{TLF_VIS}</a></div>
</div>
<section class="prosjektside__andre" aria-labelledby="andre-tittel">
<h2 id="andre-tittel">Flere prosjekter</h2>
<div class="prosjektgrid">
{andre}
{facebookkort()}
</div>
</section>
</div>
</article>'''
        side(
            f"prosjekter/{p['slug']}/index.html",
            f"{p['tittel']}{sted_tittel} | {FIRMA}",
            prosjektbeskrivelse(p, sted_tekst),
            url,
            innhold,
            ld=(brodsmuler_ld([("Forside", "/"), ("Prosjekter", "/prosjekter/"), (p["tittel"], url)]),),
            kropp_klasse="undersiden",
        )


def bygg_prosjektoversikt():
    rader = []
    for i, p in enumerate(PROSJEKTER, 1):
        navn, alt = p["bilder"][0]
        url = f"/prosjekter/{p['slug']}/"
        lapper = "".join(f"<li>{e(x)}</li>" for x in p["arbeid"][:5])
        rader.append(f'''<li class="prosjektrad sig">
<a class="prosjektrad__bilde" href="{url}" tabindex="-1" aria-hidden="true">{bilde(navn, alt, "(min-width: 860px) 40vw, 100vw")}</a>
<div class="prosjektrad__tekst">
<p class="prosjektrad__meta"><span class="prosjektrad__nr">{i:02d}</span>{e(prosjektmeta(p))}</p>
<h2><a href="{url}">{myk(p["tittel"])}</a></h2>
<p class="prosjektrad__ingress">{e(p["ingress"])}</p>
<ul class="merkelapper" aria-label="Arbeid i prosjektet">{lapper}</ul>
<a class="prosjektkort__lenke" href="{url}" aria-hidden="true" tabindex="-1">Se prosjektet {PIL_IKON}</a>
</div>
</li>''')
    antall = len(PROSJEKTER)
    innhold = f'''<article class="prosjektside prosjektoversikt">
<div class="ramme">
<nav class="brodsmuler" aria-label="Brødsmuler"><a href="/">Forside</a><span aria-hidden="true">/</span><span aria-current="page">Prosjekter</span></nav>
<p class="stikk">Prosjekter · {antall} jobber</p>
<h1>Arbeid vi står for</h1>
<p class="prosjektside__ingress">Et utvalg av jobbene vi har gjort for private og bedrifter – fra bad og tilbygg til terrasser, graving, drenering og massetransport. Klikk deg inn på et prosjekt for flere bilder og hva vi gjorde.</p>
<ol class="prosjektliste">
{"".join(rader)}
</ol>
<div class="prosjektside__cta">
<h2>Har du en lignende jobb?</h2>
<div class="knapperad"><a class="knapp" href="/#kontakt">Be om befaring {PIL_IKON}</a><a class="knapp knapp--tom" href="{FACEBOOK}" rel="noopener">Flere bilder på Facebook</a></div>
</div>
</div>
</article>'''
    side(
        "prosjekter/index.html",
        f"Prosjekter – bad, terrasse og drenering | {FIRMA}",
        f"Se prosjekter fra {FIRMA}: bad og vaskerom, tilbygg, terrasser, drenering og "
        f"massetransport i {KOMMUNE}, Hamar og {FYLKE}.",
        "/prosjekter/",
        innhold,
        ld=(brodsmuler_ld([("Forside", "/"), ("Prosjekter", "/prosjekter/")]),),
        kropp_klasse="undersiden",
    )


# --- Personvern -------------------------------------------------------------
def bygg_samarbeidspartnere():
    kort = "\n".join(
        f'''<section class="partner" aria-labelledby="partner-{p["id"]}">
<img class="partner__logo" src="/{p["logo"]}?v={innholdsmerke(p["logo"])}" width="{p["logo_mal"][0]}" height="{p["logo_mal"][1]}" alt="{e(p["navn"])}" decoding="async">
<p class="partner__fag">{e(p["fag"])}</p>
<h2 id="partner-{p["id"]}">{e(p["navn"])}</h2>
<p>{e(p["tekst"])}</p>
<a class="partner__lenke" href="{e(p["url"])}" rel="noopener">{e(p["lenketekst"])} {PIL_IKON}</a>
</section>'''
        for p in SAMARBEIDSPARTNERE
    )
    innhold = f'''<article class="tekstside">
<div class="ramme tekstside__ramme">
<p class="stikk">Samarbeid</p>
<h1>Samarbeids&shy;partnere</h1>
<p class="tekstside__ingress">Vi bygger. Til det som må på plass før og rundt byggingen, har vi faste partnere vi stoler på – så du har ett lag hele veien.</p>
{kort}
<div class="knapperad"><a class="knapp" href="/#kontakt">Be om befaring {PIL_IKON}</a></div>
</div>
</article>'''
    side(
        "samarbeidspartnere/index.html",
        f"Samarbeidspartnere | {FIRMA}",
        f"{FIRMA} samarbeider med Ubicu AS om byggesøknader og tegninger – ett lag fra tegning til ferdig bygg.",
        "/samarbeidspartnere/",
        innhold,
        ld=(brodsmuler_ld([("Forside", "/"), ("Samarbeidspartnere", "/samarbeidspartnere/")]),),
        kropp_klasse="undersiden",
    )


def bygg_personvern():
    utkast = (
        '<p class="tekstside__merk">Utkast. Teksten må gjennomgås og godkjennes av '
        f"{FIRMA} før siden lanseres.</p>"
        if FORHANDSVISNING
        else ""
    )
    innhold = f'''<article class="tekstside">
<div class="ramme tekstside__ramme">
<p class="stikk">Personvern</p>
<h1>Personvern&shy;erklæring</h1>
{utkast}
<p class="tekstside__ingress">Her forklarer vi hvilke opplysninger vi tar imot når du kontakter oss, hva vi bruker dem til og hvilke rettigheter du har.</p>

<h2>Behandlingsansvarlig</h2>
<p>{FIRMA}, org.nr. {ORGNR}, {POSTNR} {POSTSTED}. Spørsmål om personvern sender du til <a href="mailto:{EPOST}">{EPOST}</a>.</p>

<h2>Når du kontakter oss</h2>
<p>Ringer du, sender e-post eller bruker kontaktskjemaet, får vi navnet ditt, kontaktopplysningene dine og det du forteller om jobben. Vi bruker opplysningene bare til å svare deg, gi tilbud og gjennomføre oppdraget.</p>
<p>Grunnlaget er at du har bedt oss om noe før en eventuell avtale (personvernforordningen artikkel 6 nr. 1 bokstav b), og vår berettigede interesse i å svare på henvendelser (bokstav f).</p>

<h2>Hvor lenge vi tar vare på opplysningene</h2>
<p>Henvendelser som ikke blir til et oppdrag, sletter vi senest tolv måneder etter siste kontakt. Blir det et oppdrag, oppbevarer vi det regnskapsloven og bokføringsloven krever.</p>

<h2>Informasjonskapsler og sporing</h2>
<p>Nettsiden bruker ingen informasjonskapsler og ingen analyse- eller sporingsverktøy. Skrifter og bilder lastes fra nettsidens egen server, ikke fra tredjeparter.</p>

<h2>Leverandører</h2>
<p>Nettsiden ligger hos en ekstern leverandør, som av sikkerhetshensyn kan føre tekniske logger (blant annet IP-adresse) i en kort periode. Vi deler ikke opplysningene dine med andre, og vi selger dem aldri.</p>

<h2>Rettighetene dine</h2>
<p>Du kan be om innsyn i, retting av og sletting av opplysningene vi har om deg. Kontakt oss på <a href="mailto:{EPOST}">{EPOST}</a>. Mener du at vi behandler opplysningene feil, kan du klage til <a href="https://www.datatilsynet.no/" rel="noopener">Datatilsynet</a>.</p>
</div>
</article>'''
    side(
        "personvern/index.html",
        f"Personvern | {FIRMA}",
        f"Slik behandler {FIRMA} opplysningene du gir oss når du tar kontakt. Ingen informasjonskapsler og ingen sporing.",
        "/personvern/",
        innhold,
        kropp_klasse="undersiden",
    )


def bygg_404():
    innhold = f'''<section class="tom-side">
<div class="ramme">
<p class="stikk">Feil 404</p>
<h1>Her står det<br>ingenting ennå.</h1>
<p>Siden du lette etter finnes ikke. Kanskje er lenken gammel, eller så er det en skrivefeil i adressen.</p>
<div class="knapperad"><a class="knapp" href="/">Til forsiden {PIL_IKON}</a><a class="knapp knapp--tom" href="tel:{TLF_URI}">{TLF_IKON}{TLF_VIS}</a></div>
</div>
</section>'''
    side("404.html", f"Fant ikke siden | {FIRMA}", "Siden finnes ikke.", None, innhold, kropp_klasse="undersiden")


# --- Faste filer ------------------------------------------------------------
SIDER_FOR_SITEMAP = ["/", "/prosjekter/", "/samarbeidspartnere/", "/personvern/"] + [f"/prosjekter/{p['slug']}/" for p in PROSJEKTER]


def sitemap_datoer():
    """Dato per side, oppdatert bare når siden faktisk endrer innhold.
    Lagres i verktoy/sitemap-datoer.json (innholdshash + dato)."""
    fil = ROT / "verktoy" / "sitemap-datoer.json"
    lagret = json.loads(fil.read_text(encoding="utf-8")) if fil.exists() else {}
    modus = "forhandsvisning" if FORHANDSVISNING else "drift"
    gamle = lagret.get(modus, {})
    nye = {}
    idag = date.today().isoformat()
    for s in SIDER_FOR_SITEMAP:
        side = ROT / s.strip("/") / "index.html" if s != "/" else ROT / "index.html"
        h = hashlib.sha256(side.read_bytes()).hexdigest()[:16]
        forrige = gamle.get(s)
        nye[s] = forrige if forrige and forrige["hash"] == h else {"hash": h, "dato": idag}
    lagret[modus] = nye
    fil.write_text(json.dumps(lagret, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return {s: v["dato"] for s, v in nye.items()}


def bygg_sitemap():
    datoer = sitemap_datoer()
    rader = "\n".join(
        f"<url><loc>{DOMENE}{s}</loc><lastmod>{datoer[s]}</lastmod></url>" for s in SIDER_FOR_SITEMAP
    )
    (ROT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{rader}\n</urlset>\n",
        encoding="utf-8",
        newline="\n",
    )


def bygg_llms():
    """Kort faktaside for AI-tjenester (llmstxt.org). Bare i drift – forhåndsvisningen
    skal ikke gi AI-tjenester en adresse som forsvinner."""
    fil = ROT / "llms.txt"
    if FORHANDSVISNING:
        if fil.exists():
            fil.unlink()
        return
    g = SENTRAL_GODKJENNING
    tjenester = "\n".join(f"- **{t[1].replace('&shy;', '')}:** {t[2]}" for t in TJENESTER)
    prosjekter = "\n".join(f"- [{p['tittel']}]({DOMENE}/prosjekter/{p['slug']}/)" for p in PROSJEKTER)
    tekst = f"""# {FIRMA}

> Snekker- og tømrerfirma fra {POSTSTED} i {KOMMUNE} ({FYLKE}). Nybygg, tilbygg, rehabilitering,
> graving, drenering og massetransport for private og bedrifter.

- Organisasjonsnummer: {ORGNR}
- Etablert: {STIFTET} · Ansatte: {ANSATTE}
- Område: {KOMMUNE}, Hamar og {FYLKE}
- Sentralt godkjent av Direktoratet for byggkvalitet som utførende i tiltaksklasse {g["tiltaksklasse"]}: {", ".join(o.lower() for o in g["omraader"])}. Se {g["register"]}
- Gaselle-bedrift {GASELLE_AAR} (Dagens Næringsliv)
- Byggesøknader og tegninger i samarbeid med Ubicu AS ({UBICU_URL})
- Telefon: {TLF_VIS} · E-post: {EPOST}
- Facebook: {FACEBOOK}

## Tjenester

{tjenester}

## Sider

- [Forside]({DOMENE}/)
- [Prosjekter]({DOMENE}/prosjekter/)
- [Samarbeidspartnere]({DOMENE}/samarbeidspartnere/)
- [Personvern]({DOMENE}/personvern/)

## Prosjekter

{prosjekter}
"""
    fil.write_text(tekst, encoding="utf-8", newline="\n")


def bygg_robots():
    if FORHANDSVISNING:
        # Med vilje INGEN Disallow her. Hver side har noindex i <head>, og Google
        # ser bare det merket hvis den får hente siden. En Disallow ville gjort
        # merket usynlig, og en lenke fra et annet sted kunne da fått adressen
        # inn i søkeresultatene likevel (Googles egen dokumentasjon om noindex).
        tekst = (
            "# Forhåndsvisning – ikke en side i drift.\n"
            "# Hver side har <meta name=\"robots\" content=\"noindex\">.\n"
            "User-agent: *\n"
            "Allow: /\n"
        )
    else:
        tekst = f"User-agent: *\nAllow: /\n\nSitemap: {DOMENE}/sitemap.xml\n"
    (ROT / "robots.txt").write_text(tekst, encoding="utf-8", newline="\n")


def bygg_manifest():
    data = {
        "name": FIRMA,
        "short_name": KORTNAVN,
        "lang": "nb-NO",
        "start_url": "/",
        "display": "browser",
        "background_color": "#0d0c0a",
        "theme_color": "#0d0c0a",
        "icons": [{"src": "/merkevare/favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
    }
    (ROT / "site.webmanifest").write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )


def sjekk_godkjenning():
    """Stopper bygget hvis siden ville påstått en utløpt sentral godkjenning."""
    til = SENTRAL_GODKJENNING["gyldig_til"]
    idag = date.today()
    if idag > til:
        raise SystemExit(
            f"STOPP: sentral godkjenning gikk ut {til:%d.%m.%Y}. Sjekk {SENTRAL_GODKJENNING['register']} "
            "og rett datoen i SENTRAL_GODKJENNING – eller fjern godkjenningen fra siden."
        )
    if idag > til - timedelta(days=60):
        print(f"OBS: sentral godkjenning går ut {til:%d.%m.%Y}. Sjekk om den er fornyet.")


def main():
    sjekk_godkjenning()
    bygg_forside()
    bygg_prosjektsider()
    bygg_prosjektoversikt()
    bygg_samarbeidspartnere()
    bygg_personvern()
    bygg_404()
    bygg_sitemap()
    bygg_robots()
    bygg_llms()
    bygg_manifest()
    modus = "FORHÅNDSVISNING (noindex)" if FORHANDSVISNING else "DRIFT (indekseres)"
    print(f"Bygget {FIRMA} – {modus} – {DOMENE}")


if __name__ == "__main__":
    main()
