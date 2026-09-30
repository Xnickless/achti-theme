#!/usr/bin/env python3
"""Wspólna kolorystyka („grading”) zdjęć na modelce — ciepły, filmowy look jak w kampaniach barts.eu (29.09.2026).
Kroki: lekkie ocieplenie, podniesione czernie (film), delikatna krzywa S, −12 % nasycenia, drobne ziarno.
  ~/Claude/achti-foto/venv/bin/python3 tools/grade_photos.py demo <wyj.jpg> <plik.png> [...]   # przed | po
  ~/Claude/achti-foto/venv/bin/python3 tools/grade_photos.py apply <wejście.png> <wyjście.jpg>
Siła efektu: --strength=1.0 (0 = bez zmian)."""
import sys, random
from PIL import Image, ImageDraw, ImageEnhance

ARGS = {a.split('=', 1)[0]: a.split('=', 1)[1] for a in sys.argv if a.startswith('--') and '=' in a}
STRENGTH = float(ARGS.get('--strength', '1.0'))
POS = [a for a in sys.argv[1:] if not a.startswith('--')]


def curve(v, s):
    x = v / 255.0
    lift, gain = 0.045 * s, 1 - 0.035 * s          # czernie w górę, biele lekko w dół (charakter kliszy)
    x = lift + x * (gain - lift)
    y = x + 0.10 * s * (x - 0.5) * (1 - abs(2 * x - 1))  # łagodna krzywa S w półtonach
    return max(0, min(255, round(y * 255)))


def grade(im, s=STRENGTH):
    im = im.convert('RGB')
    lut_r = [curve(min(255, v * (1 + 0.035 * s)), s) for v in range(256)]
    lut_g = [curve(min(255, v * (1 + 0.012 * s)), s) for v in range(256)]
    lut_b = [curve(v * (1 - 0.04 * s), s) for v in range(256)]
    im = im.point(lut_r + lut_g + lut_b)
    im = ImageEnhance.Color(im).enhance(1 - 0.12 * s)
    if s > 0:  # ziarno: szum monochromatyczny w małej rozdzielczości, przeskalowany (miękkie ziarenka)
        w, h = im.size
        n = Image.effect_noise((max(1, w // 2), max(1, h // 2)), 22 * s).resize((w, h), Image.BILINEAR).convert('L')
        im = Image.blend(im, Image.merge('RGB', (n, n, n)), 0.045 * s)
    return im


if __name__ == '__main__':
    if not POS: sys.exit(__doc__)
    if POS[0] == 'apply':
        grade(Image.open(POS[1])).save(POS[2], quality=88, optimize=True, progressive=True)
    elif POS[0] == 'demo':
        out, files = POS[1], POS[2:]
        H = 560; tiles = []
        for f in files:
            a = Image.open(f).convert('RGB'); a = a.resize((int(a.width * H / a.height), H), Image.LANCZOS)
            tiles.append((a, grade(a)))
        W = tiles[0][0].width
        sheet = Image.new('RGB', (len(tiles) * (W * 2 + 24), H + 34), 'white'); d = ImageDraw.Draw(sheet)
        for i, (a, b) in enumerate(tiles):
            x = i * (W * 2 + 24); sheet.paste(a, (x, 0)); sheet.paste(b, (x + W + 4, 0))
            d.text((x + 4, H + 10), 'przed', fill='black'); d.text((x + W + 8, H + 10), 'po', fill='black')
        sheet.save(out, quality=88); print(out, sheet.size)
