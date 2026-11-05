"""Ostrzejsze kółka palet przędzy (05.11.2026): ponowne wycięcie z oryginalnych zdjęć zamiast wersji 2000 px.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/ostre_palety.py ORYGINAŁY OUT [--tylko=ACRYLIC 100_|COLORCARD VEZUV] [--size=640]

ORYGINAŁY = colorcards-bez-metek-3 (pełna rozdzielczość). Współrzędne kół z manifest.json (skala 2000 px dłuższego boku).
Obrót dobierany do kółka, które już jest w Shopify (porównanie miniatur), więc kierunek nitek zostaje jak był.
Wynik: OUT/<karta>/<kolor>.jpg + OUT/manifest.json → set_warianty.py OUT --upload-only --replace.
"""
import json
import os
import re
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import shopify_import as si  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
SRC, OUT = args
SIZE = int(opts.get('size', 640))
ONLY = set(opts['tylko'].split('|')) if 'tylko' in opts else None


def handleize(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('%', '')).strip('-')


def slug(card):
    return handleize(re.sub(r'^COLORCARD\s+', '', card))


def live(pref):
    out, cur = {}, None
    while True:
        r = si.gql('''query($q:String,$c:String){ files(first:250, after:$c, query:$q){ nodes{ ... on MediaImage { image{ url } } }
            pageInfo{ hasNextPage endCursor } } }''', {'q': f'filename:{pref}*', 'c': cur})['files']
        for n in r['nodes']:
            u = (n.get('image') or {}).get('url') or ''
            fn = u.split('/')[-1].split('?')[0]
            if fn.startswith(pref):
                out[fn] = u
        if not r['pageInfo']['hasNextPage']:
            return out
        cur = r['pageInfo']['endCursor']


def small(img):
    g = cv2.cvtColor(cv2.resize(img, (48, 48), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2LAB).astype(np.float32)
    return (g - g.mean((0, 1))) / (g.std((0, 1)) + 1e-3), g.mean((0, 1))


man = json.load(open(os.path.join(HERE, 'manifest.json')))
res, skipped = {}, []
for card, cols in man.items():
    if card.startswith('COLORCARD AZ') or (ONLY and card not in ONLY):
        continue
    files = live(f'kolor-{slug(card)}-')
    if not files:
        continue
    os.makedirs(os.path.join(OUT, card), exist_ok=True)
    cache = {}
    for color, v in cols.items():
        fn = f'kolor-{slug(card)}-{handleize(color)}.jpg'
        if fn not in files or len(v) < 4:
            continue
        photo, r = v[0], v[3]
        p = os.path.join(SRC, card, os.path.splitext(photo)[0] + '.jpg')
        if p not in cache:
            im = cv2.imread(p)
            cache[p] = None if im is None else [(k, np.ascontiguousarray(np.rot90(im, k))) for k in range(4)]
        if cache[p] is None:
            skipped.append((card, color, 'brak zdjęcia'))
            continue
        ref = cv2.imdecode(np.frombuffer(subprocess.run(['curl', '-sf', files[fn].split('?')[0]],
                                                        capture_output=True).stdout, np.uint8), cv2.IMREAD_COLOR)
        if ref is None:
            skipped.append((card, color, 'brak kółka w Shopify'))
            continue
        # kółko w Shopify = kwadrat 2*0.92*r z wersji 2000 px; szukamy go na oryginale (4 obroty), skala 2000 px
        side2k = max(int(2 * r * 0.92), 8)
        tpl = cv2.resize(ref, (side2k, side2k), interpolation=cv2.INTER_AREA)
        best = (-1, None)
        for k, im in cache[p]:
            sc = 2000 / max(im.shape[:2])
            small_im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            if small_im.shape[0] < side2k or small_im.shape[1] < side2k:
                continue
            res_ = cv2.matchTemplate(small_im, tpl, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(res_)
            if mv > best[0]:
                best = (mv, (k, im, ml, sc))
        if best[0] < 0.6:
            skipped.append((card, color, f'nie znaleziono {best[0]:.2f}'))
            continue
        k, im, (x2, y2), sc = best[1]
        X, Y, S = int(x2 / sc), int(y2 / sc), int(side2k / sc)
        c = im[Y:Y + S, X:X + S]
        bk = 0
        out = cv2.resize(np.ascontiguousarray(np.rot90(c, bk)), (SIZE, SIZE),
                         interpolation=cv2.INTER_AREA if c.shape[0] > SIZE else cv2.INTER_LANCZOS4)
        cv2.imwrite(os.path.join(OUT, card, color + '.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 90])
        res.setdefault(card, {})[color] = [photo, k, X, Y, S, round(best[0], 3)]
    print(card, len(res.get(card, {})), 'kolorów', flush=True)
json.dump(res, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
for s in skipped:
    print('POMINIĘTE', *s)
