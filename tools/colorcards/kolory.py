"""Płaskie kółka z kolorów próbki (życzenie Adriana 08.10.2026: „same kolory”, bez zdjęcia dzianiny).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/kolory.py CROPS OUT [--styl=wycinki|pasy] [--only=folder|folder]

CROPS = wycinki z wytnij.py (<CROPS>/<karta>/<kolor>.jpg, próbki już obrócone jak na czapce),
OUT = <OUT>/<karta>/<kolor>.jpg (240 px) + <OUT>/kolory.json {karta: {kolor: [[hex, udział], …]}}.

Kolory: k-means w Lab (do 5 skupień), sklejanie podobnych (ΔE < 14 — cienie dzianiny to ten sam kolor),
odrzucenie drobnych (< 7 %), kolor skupienia = mediana pikseli bez najciemniejszych/najjaśniejszych (cień/połysk).
Styl „wycinki”: kółko podzielone jak tort wg udziału; „pasy”: poziome pasy w kolejności z góry na dół jak na próbce.
"""
import json
import os
import re
import sys

import cv2
import numpy as np

SIZE = 240


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def palette(img):
    small = cv2.resize(img, (96, 96), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    k = 5
    _, lbl, cent = cv2.kmeans(lab, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 4,
                              cv2.KMEANS_PP_CENTERS)
    lbl = lbl.ravel()
    groups = [[i] for i in range(k)]

    def de(a, b):  # odległość z mniejszą wagą jasności (cienie splotu)
        d = cent[a] - cent[b]
        return float(np.sqrt((0.5 * d[0]) ** 2 + d[1] ** 2 + d[2] ** 2))
    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if min(de(a, b) for a in groups[i] for b in groups[j]) < 14:
                    groups[i] += groups.pop(j)
                    merged = True
                    break
            if merged:
                break
    out = []
    rows = np.arange(len(lbl)) // 96
    for g in groups:
        m = np.isin(lbl, g)
        share = m.mean()
        if share < 0.07:
            continue
        px = lab[m]
        L = px[:, 0]
        lo, hi = np.percentile(L, 20), np.percentile(L, 85)
        core = px[(L >= lo) & (L <= hi)] if ((L >= lo) & (L <= hi)).sum() > 10 else px
        c = np.median(core, axis=0).astype(np.uint8).reshape(1, 1, 3)
        bgr = cv2.cvtColor(c, cv2.COLOR_LAB2BGR)[0, 0]
        out.append(('#%02x%02x%02x' % (bgr[2], bgr[1], bgr[0]), float(share), float(rows[m].mean())))
    tot = sum(s for _, s, _ in out)
    return [(h, s / tot, y) for h, s, y in out]


def draw(pal, styl):
    img = np.full((SIZE, SIZE, 3), 255, np.uint8)
    def bgr(h):
        return (int(h[5:7], 16), int(h[3:5], 16), int(h[1:3], 16))
    if styl == 'pasy':
        y = 0
        for h, s, _ in sorted(pal, key=lambda p: p[2]):
            y2 = y + s * SIZE
            cv2.rectangle(img, (0, int(round(y))), (SIZE, int(round(y2))), bgr(h), -1)
            y = y2
    else:
        a = -90.0
        for h, s, _ in sorted(pal, key=lambda p: -p[1]):
            cv2.ellipse(img, (SIZE // 2, SIZE // 2), (SIZE, SIZE), 0, a, a + s * 360 + 0.5, bgr(h), -1)
            a += s * 360
    return img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
    crops, out = args
    styl = opts.get('styl', 'wycinki')
    only = set(opts['only'].split('|')) if 'only' in opts else None
    data = {}
    for folder in sorted(os.listdir(crops)):
        d = os.path.join(crops, folder)
        if not os.path.isdir(d) or folder.startswith('_') or (only and folder not in only):
            continue
        os.makedirs(os.path.join(out, folder), exist_ok=True)
        data[folder] = {}
        for fn in sorted(os.listdir(d), key=natural):
            if not fn.endswith('.jpg'):
                continue
            pal = palette(cv2.imread(os.path.join(d, fn)))
            cv2.imwrite(os.path.join(out, folder, fn), draw(pal, styl), [cv2.IMWRITE_JPEG_QUALITY, 92])
            data[folder][fn[:-4]] = [[h, round(s, 3)] for h, s, _ in pal]
    json.dump(data, open(os.path.join(out, 'kolory.json'), 'w'), ensure_ascii=False, indent=1)
    print(sum(len(v) for v in data.values()), 'kółek')


if __name__ == '__main__':
    main()
