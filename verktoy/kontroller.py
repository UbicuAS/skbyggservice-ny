#!/usr/bin/env python3
"""
Kontroll før publisering. Kjør ETTER bygg.py og FØR git push:

    python verktoy/kontroller.py && git push

Avslutter med feilkode 1 hvis noe er galt, så kommandoen over stopper.
Leser bare filene i repoet. Lanseringstesten kjøres i en midlertidig kopi.

Kontrollerer:
  1. ingen metadata (EXIF/XMP) i bilder
  2. hver side: noindex i forhåndsvisning, ingen style-attributter eller
     inline-skript (blokkeres av CSP), bare kjente eksterne adresser
  3. alle interne lenker og ressurser finnes, og ?v=-hashene stemmer
  4. url() i CSS peker på filer som finnes
  5. CNAME, .nojekyll og robots.txt
  6. lanseringsbryteren: FORHANDSVISNING = False fjerner alle spor
"""

import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROT = Path(__file__).resolve().parent.parent
FORHANDSVISNING_DOMENE = "https://skbyggservice.ubicu.cloud"
PRODUKSJONSDOMENE = "https://skbyggservice.no"
KJENTE = (
    "https://schema.org",
    "https://www.facebook.com/SKbyggserviceas",
    "https://www.datatilsynet.no",
    "http://www.w3.org",
    "https://sgregister.dibk.no/enterprises/925496774",  # sentral godkjenning (DiBKs register)
    "https://dibk.no",                                  # utsteder av godkjenningen (JSON-LD)
    "https://ubicu.no",                                 # samarbeidspartner (søknader og tegninger)
)
feil = []


def f(melding):
    feil.append(melding)
    print("  FEIL:", melding)


def html_sider(rot):
    return sorted(p for p in rot.rglob("*.html") if ".git" not in p.parts)


def main():
    forhandsvisning = "FORHANDSVISNING = True" in (ROT / "bygg.py").read_text(encoding="utf-8")
    domene = FORHANDSVISNING_DOMENE if forhandsvisning else PRODUKSJONSDOMENE

    print("1) Metadata i bilder")
    n = 0
    for fil in sorted(list((ROT / "bilder").glob("*")) + list((ROT / "merkevare").glob("*.jpg"))):
        with Image.open(fil) as im:
            n += 1
            if im.getexif() or any(k in im.info for k in ("exif", "xmp", "XML:com.adobe.xmp", "comment")):
                f(f"metadata i {fil.name}")
    print(f"  {n} rasterfiler")

    print("2-3) Sidene, lenker og versjonshasher")
    for side in html_sider(ROT):
        t = side.read_text(encoding="utf-8")
        rel = side.relative_to(ROT).as_posix()
        if forhandsvisning and '<meta name="robots" content="noindex, nofollow, noarchive">' not in t:
            f(f"mangler noindex: {rel}")
        if re.search(r'\sstyle="', t):
            f(f"style-attributt (blokkeres av CSP): {rel}")
        if re.search(r"<script(?![^>]*(src=|application/ld\+json))", t):
            f(f"inline-skript (blokkeres av CSP): {rel}")
        if "localhost" in t:
            f(f"localhost i {rel}")
        for adr in re.findall(r'https?://[^"\s<>)]+', t):
            if not adr.startswith((domene,) + KJENTE):
                f(f"uventet adresse i {rel}: {adr}")
        refs = re.findall(r'(?:href|src)="(/[^"#]*)"', t)
        for s in re.findall(r'(?:srcset|imagesrcset)="([^"]+)"', t):
            refs += re.findall(r"(/\S+)\s+\d+w", s)
        for ref in refs:
            sti, _, query = ref.partition("?")
            mal = ROT / sti.lstrip("/")
            if sti.endswith("/"):
                mal = mal / "index.html"
            if not mal.exists():
                f(f"død lenke i {rel}: {ref}")
            elif query.startswith("v="):
                riktig = hashlib.sha256(mal.read_bytes()).hexdigest()[:10]
                if query[2:] != riktig:
                    f(f"feil versjonshash i {rel}: {ref} (skal være {riktig})")
    print(f"  {len(html_sider(ROT))} sider")

    print("4) CSS")
    css = (ROT / "css/stil.css").read_text(encoding="utf-8")
    for url in re.findall(r'url\("?(/[^")]+)"?\)', css):
        if not (ROT / url.lstrip("/")).exists():
            f(f"død url() i CSS: {url}")

    print("5) Faste filer")
    if (ROT / "CNAME").read_text(encoding="utf-8").strip() != "skbyggservice.ubicu.cloud":
        f("CNAME er feil")
    if not (ROT / ".nojekyll").exists():
        f(".nojekyll mangler")
    robots = (ROT / "robots.txt").read_text(encoding="utf-8")
    if "Disallow" in robots:
        f("robots.txt har Disallow – da ser ikke Google noindex-merket")

    if forhandsvisning:
        print("6) Lanseringsbryteren (i midlertidig kopi)")
        with tempfile.TemporaryDirectory() as tmp:
            kopi = Path(tmp) / "kopi"
            shutil.copytree(ROT, kopi, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            b = (kopi / "bygg.py").read_text(encoding="utf-8")
            (kopi / "bygg.py").write_text(b.replace("FORHANDSVISNING = True", "FORHANDSVISNING = False"), encoding="utf-8")
            subprocess.run([sys.executable, "-I", str(kopi / "bygg.py")], check=True, cwd=kopi, capture_output=True)
            for side in html_sider(kopi):
                t = side.read_text(encoding="utf-8")
                rel = side.relative_to(kopi).as_posix()
                for rest in ("noindex", "forhandsvisning", "ubicu.cloud", "Utkast"):
                    if rest in t:
                        f(f"etter lansering står «{rest}» igjen i {rel}")
            if f"Sitemap: {PRODUKSJONSDOMENE}/sitemap.xml" not in (kopi / "robots.txt").read_text(encoding="utf-8"):
                f("robots.txt ved lansering mangler sitemap")

    print()
    if feil:
        print(f"RESULTAT: {len(feil)} feil – ikke publiser")
        sys.exit(1)
    print("RESULTAT: ingen feil")


if __name__ == "__main__":
    main()
