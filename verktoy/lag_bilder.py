#!/usr/bin/env python3
"""
Lager nettversjoner (webp i flere bredder) av ett kildebilde.

    python verktoy/lag_bilder.py <kildebilde> <navn> [--bredder 480,800,1280]
    python verktoy/lag_bilder.py <kildebilde> delebilde --delebilde

Resultatet havner i bilder/<navn>-<bredde>.webp. Med --delebilde lages i stedet
merkevare/delebilde.jpg, beskåret til 1200 x 630 (Open Graph).

Originalene ligger UTENFOR repoet, fordi de kan ha metadata (EXIF/GPS) og
er unødig store. Det som skrives hit har ingen metadata:
Pillow tar bare med EXIF når man ber om det, og det gjør vi ikke.
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROT = Path(__file__).resolve().parent.parent
STANDARD_BREDDER = (480, 800, 1280, 1920)
MAKS_PIKSLER = 60_000_000  # avvis absurde filer i stedet for å spise minnet
GYLDIG_NAVN = set("abcdefghijklmnopqrstuvwxyz0123456789-")


def les(kilde: Path) -> Image.Image:
    if not kilde.is_file():
        sys.exit(f"Finner ikke kildebildet: {kilde}")
    Image.MAX_IMAGE_PIXELS = MAKS_PIKSLER
    with Image.open(kilde) as im:
        im.verify()  # avslører avkuttede og korrupte filer før vi bruker dem
    im = Image.open(kilde)
    im = ImageOps.exif_transpose(im)  # mobilbilder står ofte på siden uten denne
    return im.convert("RGB")


def lag_varianter(im: Image.Image, navn: str, bredder) -> None:
    ut = ROT / "bilder"
    ut.mkdir(exist_ok=True)
    for b in bredder:
        if b > im.width:
            continue  # aldri skaler opp – det gir bare en større, uskarpere fil
        h = round(im.height * b / im.width)
        liten = im.resize((b, h), Image.LANCZOS)
        fil = ut / f"{navn}-{b}.webp"
        liten.save(fil, "WEBP", quality=80, method=6)
        print(f"  {fil.relative_to(ROT)}  {b}x{h}  {fil.stat().st_size // 1024} kB")


def lag_delebilde(im: Image.Image) -> None:
    maal_b, maal_h = 1200, 630
    skala = max(maal_b / im.width, maal_h / im.height)
    stor = im.resize((round(im.width * skala), round(im.height * skala)), Image.LANCZOS)
    # beskjær mot høyre, der arbeidslyset og sagen er
    venstre = stor.width - maal_b
    topp = (stor.height - maal_h) // 2
    utsnitt = stor.crop((venstre, topp, venstre + maal_b, topp + maal_h))
    fil = ROT / "merkevare" / "delebilde.jpg"
    fil.parent.mkdir(exist_ok=True)
    utsnitt.save(fil, "JPEG", quality=84, optimize=True, progressive=True)
    print(f"  {fil.relative_to(ROT)}  {maal_b}x{maal_h}  {fil.stat().st_size // 1024} kB")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("kilde", type=Path)
    p.add_argument("navn")
    p.add_argument("--bredder", default=",".join(map(str, STANDARD_BREDDER)))
    p.add_argument("--delebilde", action="store_true")
    a = p.parse_args()

    # navnet blir en del av en filsti – bare små bokstaver, tall og bindestrek
    if not a.navn or not set(a.navn) <= GYLDIG_NAVN:
        sys.exit("Navnet kan bare inneholde a-z, 0-9 og bindestrek")
    try:
        bredder = sorted({int(x) for x in a.bredder.split(",")})
    except ValueError:
        sys.exit("--bredder må være tall skilt med komma")
    if not bredder or bredder[0] < 100 or bredder[-1] > 4000:
        sys.exit("--bredder må ligge mellom 100 og 4000")

    im = les(a.kilde)
    print(f"{a.kilde.name}: {im.width}x{im.height}")
    if a.delebilde:
        lag_delebilde(im)
    else:
        lag_varianter(im, a.navn, bredder)


if __name__ == "__main__":
    main()
