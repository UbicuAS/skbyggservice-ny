#!/usr/bin/env python3
"""
Sporer kundens logo fra en bildefil til vektor (SVG).

    python verktoy/spor_logo.py <logobilde>

Kundens eget logobilde er fasit. Den oransje flata finnes og fargen måles i
bildet, og alt som er svart på flata (SK, hammeren, BYGGSERVICE A/S) spores
som baner. Skruene i hjørnene gjøres om til perfekte sirkler. Ingenting er
tegnet på nytt for hånd, så formene blir de samme som i originalen.

Skriver:
  merkevare/logo-skilt.svg  hele skiltet (ramme og skruer hvis originalen har det)
  merkevare/logo.svg        oransje flate uten ramme og skruer, tett utsnitt
  merkevare/favicon.svg     øvre del (SK og hammer) på kvadratisk flate
  merkevare/logo-farger.txt fargene som ble målt

Bildet leses som utrygg inndata: størrelsen har et tak, og fila kontrolleres
før den brukes. Originalen ligger utenfor repoet.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROT = Path(__file__).resolve().parent.parent
FORSTORR = 4            # sporer på et 4x forstørret bilde – glattere kanter
MAKS_PIKSLER = 40_000_000
TOLERANSE = 0.9         # forenkling av banene, i forstørrede piksler (≈0,2 px i originalen)


def les(sti: Path) -> np.ndarray:
    if not sti.is_file():
        sys.exit(f"Finner ikke bildet: {sti}")
    Image.MAX_IMAGE_PIXELS = MAKS_PIKSLER
    with Image.open(sti) as im:
        im.verify()
    with Image.open(sti) as im:
        if im.width < 200 or im.height < 80:
            sys.exit(f"Bildet er for lite til å spore ({im.width}x{im.height}). Bruk største versjon.")
        return np.array(im.convert("RGB"))


def hex_(rgb) -> str:
    return "#" + "".join(f"{int(round(c)):02x}" for c in rgb)


def finn_plate(rgb):
    """Den største oransje flata: (x, y, b, h) og målt farge."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)
    oransje = ((h >= 3) & (h <= 24) & (s >= 110) & (v >= 120)).astype(np.uint8)
    n, merker, stats, _ = cv2.connectedComponentsWithStats(oransje, connectivity=8)
    if n < 2:
        sys.exit("Fant ingen oransje flate i bildet.")
    storst = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, b, hh = (int(t) for t in stats[storst][:4])
    farge = np.median(rgb[merker == storst], axis=0)
    return (x, y, b, hh), farge


def spor(rgb, plate):
    """Konturene av alt mørkt på flata, i flatas koordinater (originalpiksler)."""
    x, y, b, h = plate
    utsnitt = rgb[y:y + h, x:x + b]
    lys = cv2.cvtColor(utsnitt, cv2.COLOR_RGB2HSV)[:, :, 2].astype(np.float32)
    stor = cv2.resize(lys, (b * FORSTORR, h * FORSTORR), interpolation=cv2.INTER_CUBIC)
    # terskel midt mellom flata og blekket, målt i bildet
    flate_v = float(np.median(lys))
    blekk_v = float(np.percentile(lys, 2))
    terskel = (flate_v + blekk_v) / 2
    maske = (stor < terskel).astype(np.uint8) * 255
    # kantene av flata (rester av rammen) er ikke en del av merket
    k = 3 * FORSTORR
    maske[:k, :] = 0
    maske[-k:, :] = 0
    maske[:, :k] = 0
    maske[:, -k:] = 0
    blekk = np.median(utsnitt[lys < terskel], axis=0) if np.any(lys < terskel) else (30, 28, 26)
    konturer, hierarki = cv2.findContours(maske, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    return konturer, hierarki, blekk


def klassifiser(konturer, hierarki, plate):
    """Skiller skruene (runde, små, i hjørnene) fra resten av merket."""
    _, _, b, h = plate
    skruer, merke = [], []
    for i, c in enumerate(konturer):
        forelder = hierarki[0][i][3]
        areal = cv2.contourArea(c) / FORSTORR ** 2
        if areal < 4:
            continue  # støy fra jpeg
        if forelder == -1:
            omkrets = cv2.arcLength(c, True) / FORSTORR
            rundhet = 4 * np.pi * areal / (omkrets ** 2) if omkrets else 0
            (cx, cy), r = cv2.minEnclosingCircle(c)
            cx, cy, r = cx / FORSTORR, cy / FORSTORR, r / FORSTORR
            i_hjorne = min(cx, b - cx) < 0.1 * b and min(cy, h - cy) < 0.2 * h
            if rundhet > 0.7 and r < 0.06 * h and i_hjorne:
                skruer.append((cx, cy, np.sqrt(areal / np.pi)))
                continue
        merke.append((i, c))
    # hull i en skrue skal heller ikke med
    skrue_idx = set()
    return skruer, [(i, c) for i, c in merke if i not in skrue_idx]


def bane(merke) -> str:
    deler = []
    for _, c in merke:
        p = cv2.approxPolyDP(c, TOLERANSE, True).reshape(-1, 2) / FORSTORR
        if len(p) < 3:
            continue
        deler.append("M" + " ".join(f"{px:.1f} {py:.1f}" for px, py in p) + "Z")
    return "".join(deler)


def ramme_for(merke):
    pkt = np.vstack([c.reshape(-1, 2) for _, c in merke]) / FORSTORR
    return pkt[:, 0].min(), pkt[:, 1].min(), pkt[:, 0].max(), pkt[:, 1].max()


def ovre_del(merke):
    """Konturene over det største vannrette mellomrommet (SK og hammer)."""
    x0, y0, x1, y1 = ramme_for(merke)
    hoyde = int(np.ceil(y1)) + 2
    dekket = np.zeros(hoyde, dtype=bool)
    for _, c in merke:
        _, cy, _, ch = cv2.boundingRect(c)
        dekket[int(cy / FORSTORR):int((cy + ch) / FORSTORR) + 1] = True
    beste, start, lop = (0, 0), None, 0
    for yy in range(int(y0), int(y1)):
        if not dekket[yy]:
            start = yy if start is None else start
            lop = yy - start + 1
            if lop > beste[1]:
                beste = (start, lop)
        else:
            start = None
    skille = beste[0] + beste[1] / 2
    return [(i, c) for i, c in merke if cv2.boundingRect(c)[1] / FORSTORR < skille]


def svg(viewbox, innhold, tittel=True):
    vx, vy, vb, vh = viewbox
    t = "<title>SK Byggservice AS</title>" if tittel else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.1f} {vy:.1f} {vb:.1f} {vh:.1f}" '
        f'width="{vb:.0f}" height="{vh:.0f}" role="img">{t}{innhold}</svg>\n'
    )


def skriv(navn, tekst):
    fil = ROT / "merkevare" / navn
    fil.parent.mkdir(exist_ok=True)
    fil.write_text(tekst, encoding="utf-8", newline="\n")
    print(f"  {fil.relative_to(ROT)}  {fil.stat().st_size // 1024 + 1} kB")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    rgb = les(Path(sys.argv[1]))
    plate, oransje = finn_plate(rgb)
    konturer, hierarki, blekk = spor(rgb, plate)
    if hierarki is None:
        sys.exit("Fant ingenting mørkt på flata.")
    skruer, merke = klassifiser(konturer, hierarki, plate)
    _, _, b, h = plate
    o, s = hex_(oransje), hex_(blekk)
    d = bane(merke)
    print(f"Flate {b}x{h} px, oransje {o}, svart {s}, {len(merke)} konturer, {len(skruer)} skruer")

    g = f'<path fill="{s}" fill-rule="evenodd" d="{d}"/>'

    # 1) Hele skiltet. Rammen tegnes bare hvis originalen har skruer (skiltversjonen).
    if skruer:
        r = round(h * 0.038)
        sk = "".join(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="{s}"/>' for cx, cy, rr in skruer)
        skriv("logo-skilt.svg", svg((-r, -r, b + 2 * r, h + 2 * r),
              f'<rect x="{-r}" y="{-r}" width="{b + 2 * r}" height="{h + 2 * r}" fill="{s}"/>'
              f'<rect width="{b}" height="{h}" fill="{o}"/>{sk}{g}'))

    # 2) Flata alene, tett utsnitt rundt merket
    x0, y0, x1, y1 = ramme_for(merke)
    mb, mh = x1 - x0, y1 - y0
    luft_x, luft_y = 0.055 * mb, 0.1 * mh
    vb = (x0 - luft_x, y0 - luft_y, mb + 2 * luft_x, mh + 2 * luft_y)
    skriv("logo.svg", svg(vb, f'<rect x="{vb[0]:.1f}" y="{vb[1]:.1f}" width="{vb[2]:.1f}" '
                              f'height="{vb[3]:.1f}" fill="{o}"/>{g}'))

    # 3) Favicon: SK og hammer på kvadrat
    topp = ovre_del(merke)
    fx0, fy0, fx1, fy1 = ramme_for(topp)
    side = max(fx1 - fx0, fy1 - fy0) * 1.18
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    fv = (cx - side / 2, cy - side / 2, side, side)
    skriv("favicon.svg", svg(fv, f'<rect x="{fv[0]:.1f}" y="{fv[1]:.1f}" width="{side:.1f}" height="{side:.1f}" '
                                 f'rx="{side * 0.08:.1f}" fill="{o}"/>'
                                 f'<path fill="{s}" fill-rule="evenodd" d="{bane(topp)}"/>', tittel=False))

    (ROT / "merkevare" / "logo-farger.txt").write_text(
        f"Målt i {Path(sys.argv[1]).name}\noransje {o}\nsvart {s}\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
