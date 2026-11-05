"""Większe wycinki motków palet (05.11.2026): kwadrat rośnie od obecnego kółka tak długo, jak mieści się w motku.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/wieksze_palety.py SRC IN OUT [--tylko=karta|karta] [--size=800] [--max=3.0]

IN = wynik ostre_palety.py (manifest: [zdjęcie, obrót k, X, Y, bok S, dopasowanie]). Motek = piksele o kolorze bliskim środka
i z fakturą przędzy (odchylenie jasności w oknie 9×9), kartka i napisy odpadają. Kwadrat rośnie co 5 % boku, środek może się
przesuwać o pół kroku w stronę wnętrza motka; stop, gdy >3 % pikseli kwadratu nie jest motkiem.
"""
import json
import os
import sys

import cv2
import numpy as np

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
SRC, IN, OUT = args
SIZE = int(opts.get('size', 800))
MAXF = float(opts.get('max', 3.0))
ONLY = set(opts['tylko'].split('|')) if 'tylko' in opts else None
BEZ = {'COLORCARD VERONA', 'COLORCARD ROMA', 'COLORCARD VINCI', 'COLORCARD TURBO VINCI'}

man = json.load(open(os.path.join(IN, 'manifest.json')))
res, cache = {}, {}
for card, cols in man.items():
    if ONLY and card not in ONLY:
        continue
    os.makedirs(os.path.join(OUT, card), exist_ok=True)
    for color, (photo, k, X, Y, S, _) in cols.items():
        key = (card, photo, k)
        if key not in cache:
            im = cv2.imread(os.path.join(SRC, card, os.path.splitext(photo)[0] + '.jpg'))
            im = np.ascontiguousarray(np.rot90(im, k))
            lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
            g = lab[..., 0]
            mu = cv2.blur(g, (9, 9))
            sd = np.sqrt(np.maximum(cv2.blur(g * g, (9, 9)) - mu * mu, 0))
            cache.clear()
            cache[key] = (im, lab, sd)
        im, lab, sd = cache[key]
        H, W = im.shape[:2]
        c = lab[Y + S // 4:Y + 3 * S // 4, X + S // 4:X + 3 * S // 4].reshape(-1, 3)
        mean, std = c.mean(0), c.std(0)
        tex = float(np.median(sd[Y:Y + S, X:X + S]))
        T = float(np.linalg.norm(std)) * 3 + 10
        # maska motka liczona lokalnie w oknie MAXF*S wokół kółka
        R = int(S * MAXF)
        cx, cy = X + S // 2, Y + S // 2
        x0, y0, x1, y1 = max(cx - R, 0), max(cy - R, 0), min(cx + R, W), min(cy + R, H)
        dist = np.linalg.norm(lab[y0:y1, x0:x1] - mean, axis=2)
        mask = (dist < T) & (sd[y0:y1, x0:x1] > tex * 0.5)
        ii = cv2.integral(mask.astype(np.uint8))

        def box(xa, ya, w, h):
            xa, ya = xa - x0, ya - y0
            if xa < 0 or ya < 0 or xa + w > mask.shape[1] or ya + h > mask.shape[0] or w <= 0 or h <= 0:
                return 0
            tot = ii[ya + h, xa + w] - ii[ya, xa + w] - ii[ya + h, xa] + ii[ya, xa]
            return tot / (w * h)

        def frac(xa, ya, s):
            # cały kwadrat i każdy z czterech brzegów (pas 4 % boku) musi leżeć na motku
            e = max(int(s * 0.04), 2)
            return min(box(xa, ya, s, s), box(xa, ya, e, s), box(xa + s - e, ya, e, s),
                       box(xa, ya, s, e), box(xa, ya + s - e, s, e))

        best = (X, Y, S)
        base = frac(X, Y, S)
        thr = min(0.96, base - 0.03)
        # przędza puszysta/wielokolorowa albo niejednolity kadr — maska niewiarygodna, zostaje obecny kadr
        s_limit = S if (card in BEZ or base < 0.85) else S * MAXF
        s = S
        bx, by = X, Y
        while s < s_limit:
            ns = int(s * 1.05) + 1
            d = (ns - s)
            cand = []
            for ox in (-d, -d // 2, 0):
                for oy in (-d, -d // 2, 0):
                    f = frac(bx + ox, by + oy, ns)
                    cand.append((f, bx + ox, by + oy))
            f, nx, ny = max(cand)
            if f < thr:
                break
            bx, by, s = nx, ny, ns
            best = (bx, by, s)
        bx, by, s = best
        crop = im[by:by + s, bx:bx + s]
        out = cv2.resize(crop, (SIZE, SIZE), interpolation=cv2.INTER_AREA if s > SIZE else cv2.INTER_LANCZOS4)
        cv2.imwrite(os.path.join(OUT, card, color + '.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 90])
        res.setdefault(card, {})[color] = [photo, k, bx, by, s, round(s / S, 2)]
    v = list(res.get(card, {}).values())
    if v:
        print(card, len(v), 'kolorów, powiększenie mediana', sorted(x[5] for x in v)[len(v) // 2],
              'min', min(x[5] for x in v), 'bok px mediana', sorted(x[4] for x in v)[len(v) // 2], flush=True)
json.dump(res, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
