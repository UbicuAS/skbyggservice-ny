# SK Byggservice AS – ny nettside

Forslag til ny nettside for **SK Byggservice AS** (org.nr. 925 496 774), laget
av Ubicu AS.

- **Forhåndsvisning:** https://skbyggservice.ubicu.cloud/ (GitHub Pages)
- **Kundens domene:** skbyggservice.no – parkert hos Domeneshop, ingen side i
  drift (kontrollert 7. okt 2026). **Ikke rørt.**

Ren statisk HTML, uten rammeverk og uten `node_modules`. Eneste byggesteg er
`bygg.py`, som skriver sidene med felles toppfelt og bunn.

---

## ⚠️ Forhåndsvisning kontra drift – én bryter

`FORHANDSVISNING` øverst i `bygg.py` styrer alt som skiller forhåndsvisningen
fra en side i drift:

| | Forhåndsvisning (`True`) | Drift (`False`) |
|---|---|---|
| `<meta name="robots">` | `noindex, nofollow, noarchive` | `index, follow …` |
| `robots.txt` | ingen sitemap | med sitemap |
| Domene i canonical, OG, sitemap, JSON-LD | skbyggservice.ubicu.cloud | skbyggservice.no |
| Banner over toppfeltet | «Forhåndsvisning – utkast, ikke publisert» | borte |

**robots.txt har med vilje ingen `Disallow` i forhåndsvisningen.** Google ser
bare `noindex`-merket hvis den får hente siden. Med `Disallow` kunne adressen
havnet i søk likevel, uten innhold, hvis noen lenker til den.

GitHub Pages kan ikke sette HTTP-headere. Derfor står både `noindex` og
innholdssikkerheten (CSP) som meta-tagger.

### Lansering

1. Kunden godkjenner tekst, bilder og logo.
2. Kontaktskjemaet kobles til en mottaker (`SKJEMA_AKTIVT`, se under).
3. `FORHANDSVISNING = False` i `bygg.py`, og `python bygg.py`.
4. Legg ut på kundens domene etter Ubicus metode for statiske sider på webhotell.
5. Slett DNS-raden `skbyggservice` i ubicu.cloud, og skru av Pages for repoet,
   så forhåndsvisningen ikke blir liggende igjen.

## Kontaktskjemaet

`SKJEMA_AKTIVT = False`: skjemaet sender ingenting. Knappen er ikke en
send-knapp, og skriptet viser en beskjed om å ringe eller sende e-post.
Ingen opplysninger forlater nettleseren. Før lansering trengs en mottaker på
serveren (PHP på webhotellet, med spamvern), og så settes bryteren til `True`.

## Bygge og se lokalt

```bash
python bygg.py
```

Siden er ren statisk HTML og kan vises med en hvilken som helst statisk
webserver som peker på mappa.

## Filer

```
bygg.py                 all tekst, metadata og strukturerte data
css/stil.css            stilarket, med designtokens øverst
js/side.js              meny, innsig, tellere, skjema og hero-animasjonen
bilder/                 webp i flere bredder (lages med verktoy/lag_bilder.py)
merkevare/              logo, favicon og delebilde
fonter/                 Inter og JetBrains Mono, selvhostet (SIL OFL 1.1)
verktoy/lag_bilder.py   nettversjoner av et bilde, uten metadata (EXIF/GPS)
verktoy/spor_logo.py    sporer kundens logo fra bildefil til SVG
CNAME, .nojekyll        GitHub Pages – lette å slette i vanvare, ikke gjør det
```

## Heroen

Bakgrunnen er et **AI-generert stemningsbilde** (Higgsfield, `gpt_image_2_5`,
7. okt 2026). Det er merket «Illustrasjon» på siden og skal aldri framstilles som
et prosjekt kunden har gjort. Bevegelsen er laget med CSS og `js/side.js`:

- arbeidslyset «slås på» med et lite blaff, og bildet zoomer langsomt inn mot lyset
- lyset flimrer svakt, og sagflis svever i lyskjeglen (canvas, sterkest nær lyset)
- med mus beveger bildet og flisa seg litt ulikt, så det oppleves dybde
- tommestokken nederst tegnes inn fra venstre, og «STÅ.» fylles nedenfra

Animasjonen tegnes ikke når heroen er ute av syne eller fanen er skjult. Med
«redusert bevegelse» i operativsystemet står alt stille.

**Video:** legg en `bilder/hero.mp4` i mappa og kjør `bygg.py`. Da brukes video
automatisk, med bildet som plakat.

## Merkevare

Aksentfargen `--aksent` er logoens oransje. Logoen spores fra kundens egen
bildefil med `verktoy/spor_logo.py`, som også måler fargene
(`merkevare/logo-farger.txt`). Står det en annen verdi der enn i `stil.css`,
er det målingen som gjelder.

Skrifter: **Inter** (900 til overskrifter, 400/500 til brødtekst) og
**JetBrains Mono** (små etiketter). Begge er selvhostet. Siden gjør ingen kall
til Google Fonts eller andre tredjeparter.
