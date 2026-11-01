"""Wyrównanie tonu łat po metkach (21.10.2026, uwaga Kamila: „w miejscu metki ciemniejszy materiał”): LaMa bierze kolor
z otoczenia metki, a tam jest jej cień, więc łata wychodzi ciemniejsza. Tu poprawiamy tylko NISKIE częstotliwości
(jasność/kolor uśrednione na skali kilku oczek) łaty do otaczającej dzianiny — splot zostaje z LaMa.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/wyrownaj_laty.py BEZ_METEK ORYGINAŁY WYJŚCIE [--tylko=…] [--force]

Maska łaty = piksele, które usun_metki.py zmienił (|oryginał − wynik|, obrót do pionu uwzględniony). W LAB:
docelowy ton = rozmycie znormalizowane (blur(img·w)/blur(w)) z dzianiny WOKÓŁ łaty (pierścień bez łaty i bez jej
cienia) pogrupowanej k-means na 4 kolory; każdy piksel łaty przesuwany o różnicę między „swoim” kolorem pierścienia
a średnią łaty w tym kolorze (jasność ±30, barwa ±10), wygładzone, z miękką krawędzią tylko w łacie.
"""
import os
import sys

import cv2
import numpy as np


def norm_blur(x, w, s):
    k = int(s * 3) | 1
    num = cv2.GaussianBlur(x * w[..., None], (k, k), s)
    den = cv2.GaussianBlur(w, (k, k), s)[..., None]
    return num / np.maximum(den, 1e-3), den[..., 0]


def fix(orig, clean):
    if orig.shape[:2] != clean.shape[:2]:  # usun_metki obrócił zdjęcie do pionu / poziomu
        for r in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE):
            if cv2.rotate(orig, r).shape[:2] == clean.shape[:2]:
                o = cv2.rotate(orig, r)
                if np.abs(o[::8, ::8].astype(int) - clean[::8, ::8]).mean() < 25:
                    orig = o
                    break
    diff = np.abs(orig.astype(np.int16) - clean.astype(np.int16)).max(2)
    m = (diff > 12).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    H, W = m.shape
    lab = cv2.cvtColor(clean, cv2.COLOR_BGR2LAB).astype(np.float32)
    out = lab.copy()
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if area < 0.0005 * H * W:
            continue
        size = max(bw, bh)
        pad = int(size * 0.8)
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + bw + pad), min(H, y + bh + pad)
        patch = (lb[y0:y1, x0:x1] == i).astype(np.uint8)
        big = cv2.dilate(patch, np.ones((int(size * 0.08) | 1,) * 2, np.uint8))  # pomijamy też pas cienia
        ring = cv2.dilate(patch, np.ones((int(size * 0.5) | 1,) * 2, np.uint8)) - big
        # pierścień ma kilka kolorów (pasy wzoru, ściągacz) — k-means na kolorach pierścienia, każdy piksel łaty
        # wyrównujemy do ŚWOJEGO koloru (najbliższy środek), żeby nie rozjaśniać czerni szarym sąsiadem
        L = lab[y0:y1, x0:x1]
        rp = L[ring > 0]
        if len(rp) < 200:
            continue
        k = 4
        _, lab_k, cent = cv2.kmeans(rp[::max(1, len(rp) // 20000)].astype(np.float32), k, None,
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
        e = max(2.0, size * 0.03)
        sm = cv2.GaussianBlur(L, (0, 0), e)  # kolor łaty uśredniony na skali oczka
        pin = patch > 0
        pv = sm[pin]
        w = np.array([1.0, 2.0, 2.0], np.float32)  # barwa waży więcej niż jasność (cień zmienia głównie jasność)
        near = np.argmin((((pv[:, None, :] - cent[None]) * w) ** 2).sum(2), 1)
        shift = np.zeros_like(pv)
        for c in range(k):
            sel = near == c
            if sel.sum() > 20:
                shift[sel] = np.clip(cent[c] - pv[sel].mean(0), [-30, -10, -10], [30, 10, 10])
        smap = np.zeros_like(L)
        smap[pin] = shift
        smap = cv2.GaussianBlur(smap, (0, 0), e * 2)
        a = cv2.GaussianBlur(patch.astype(np.float32), (0, 0), e)[..., None]
        out[y0:y1, x0:x1] = L + smap * a
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    clean_dir, orig_dir, dst = args
    only = set(opts['tylko'].split(',')) if opts.get('tylko') else None
    for root, _, files in os.walk(clean_dir):
        for fn in sorted(files):
            if not fn.lower().endswith('.jpg') or (only and not any(o in os.path.join(root, fn) for o in only)):
                continue
            rel = os.path.relpath(os.path.join(root, fn), clean_dir)
            out = os.path.join(dst, rel)
            if os.path.exists(out) and 'force' not in opts:
                continue
            base = os.path.join(orig_dir, os.path.dirname(rel), os.path.splitext(fn)[0])
            op = next((base + e for e in ('.JPG', '.jpg', '.jpeg', '.JPEG', '.png') if os.path.exists(base + e)), None)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            clean = cv2.imread(os.path.join(root, fn))
            res = fix(cv2.imread(op), clean) if op else clean
            cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 95])
            print('ok', rel, flush=True)


if __name__ == '__main__':
    main()
