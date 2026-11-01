"""PDF z kółkami „cała próbka” dla Adriana (21.10.2026): karta po karcie, tylko kolory używane w sklepie (manifest.json).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/pdf_kolka.py KÓŁKA PDF [--podtytul="…"]
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
F = '/System/Library/Fonts/Supplemental/Arial.ttf'
FB = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, out = args
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    f1, f2, f3 = ImageFont.truetype(FB, 40), ImageFont.truetype(FB, 26), ImageFont.truetype(F, 18)
    PW, PH, M, COLS = 1240, 1754, 60, 7
    D = (PW - 2 * M) // COLS
    R = D - 20
    mask = Image.new('L', (R, R), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, R - 1, R - 1), fill=255)
    pages = []

    def new():
        p = Image.new('RGB', (PW, PH), 'white')
        pages.append(p)
        return p, ImageDraw.Draw(p), M

    p, d, y = new()
    d.text((M, y), 'Achti – kółka kolorów: cała próbka', font=f1, fill='black')
    y += 56
    d.text((M, y), opts.get('podtytul') or 'Zdjęcia kart bez metek, każda próbka w całości w kółku, bez AI.', font=f3, fill='#555')
    y += 50
    for c in sorted([c for c in os.listdir(src) if os.path.isdir(os.path.join(src, c))], key=natural):
        fs = [f for f in sorted(os.listdir(os.path.join(src, c)), key=natural) if f[:-4] in man.get(c, [])]
        fs = fs or sorted(os.listdir(os.path.join(src, c)), key=natural)
        if y + 44 + D + 28 > PH - M:
            p, d, y = new()
        d.text((M, y), c.replace('COLORCARD ', '').replace('   ', ' / '), font=f2, fill='black')
        y += 44
        for i, f in enumerate(fs):
            if i and i % COLS == 0:
                y += D + 28
                if y + D + 28 > PH - M:
                    p, d, y = new()
            x = M + (i % COLS) * D
            im = Image.open(os.path.join(src, c, f)).convert('RGB').resize((R, R), Image.LANCZOS)
            p.paste(im, (x + 10, y), mask)
            t = f[:-4]
            d.text((x + D / 2 - d.textlength(t, font=f3) / 2, y + R + 3), t, font=f3, fill='#333')
        y += D + 40
    pages[0].save(out, save_all=True, append_images=pages[1:], resolution=150)
    print(len(pages), 'stron', os.path.getsize(out) // 1024, 'KB')


if __name__ == '__main__':
    main()
