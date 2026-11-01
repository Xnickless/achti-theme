"""Cała próbka wycięta z tła kartki (23.10.2026, wariant 2 Kamila): SAM 2.1 z ramki próbki (box_2d z wskaz.py --tryb=probka)
→ maska bez kartki, ramek i napisów → próbka na białym kwadracie z miękką krawędzią.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/wytnij_probki.py ZDJĘCIA RAMKI WYJŚCIE --oryginaly=ZIP --kierunki=kierunki-ai.json
      [--tylko=AZ-2349PC,…] [--size=1000] [--zapas=0.08]

ZDJĘCIA = zdjęcia bez metek (colorcards-bez-metek-3), RAMKI = katalog z <karta>/<IMG>.JPG.json (gemmix),
--oryginaly=KATALOG — zdjęcia z zipa: ramki liczone na nich, a bez-metek są obrócone do pionu (pion()), więc
ramki poziomych zdjęć obracamy o 90° w prawo.
--kierunki=kierunki-ai.json — obrót próbki ściągaczem w dół (stopnie w prawo od surowego zdjęcia, jak w kolka_ai.py).
Kolory i zdjęcia bierze z manifest.json (karty modeli AZ, bez palet przędzy); wynik: WYJŚCIE/<karta>/<kolor>.jpg
+ WYJŚCIE/manifest.json (do set_warianty.py --upload-only --replace) + _podglad/<karta>.jpg.
"""
import json
import os
import re
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from usun_metki import models  # noqa: E402


def sam_mask(rgb, box, pt=None, neg=()):
    """Maska próbki: ramka + punkt na próbce (z OCR albo środek ramki) + punkty sąsiednich próbek jako „nie to”
    (stykające się próbki inaczej zlewają się w jedną). Z trzech masek SAM: najlepsza, chyba że jest drobna
    (fragment wzoru) — wtedy największa."""
    import torch
    from PIL import Image
    proc, model = models()['sam']
    x0, y0, x1, y1 = box
    pts = [pt or [(x0 + x1) / 2, (y0 + y1) / 2]] + [list(q) for q in neg]
    inp = proc(images=Image.fromarray(rgb), input_boxes=[[box]], input_points=[[pts]],
               input_labels=[[[1] + [0] * len(neg)]], return_tensors='pt')
    with torch.no_grad():
        out = model(**inp, multimask_output=True)
    ms = proc.post_process_masks(out.pred_masks, inp['original_sizes'])[0][0].numpy().astype(np.uint8)
    sc = out.iou_scores[0, 0].numpy()
    area = (x1 - x0) * (y1 - y0)
    i = int(np.argmax(sc))
    if ms[i].sum() < 0.3 * area:
        i = int(np.argmax([m.sum() if m.sum() < 1.05 * area else 0 for m in ms]))
    return ms[i]


def clean(m):
    """Największy kawałek, bez dziur (przerwy w dzianinie), wygładzony brzeg."""
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return m
    m = (lb == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    inv = 1 - m
    n, lb = cv2.connectedComponents(inv)
    border = set(np.unique(np.r_[lb[0], lb[-1], lb[:, 0], lb[:, -1]]))
    m = np.where(np.isin(lb, list(border)), 0, 1).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, k)


def no_paper(img, m):
    """Kartka z napisem „ZESTAW n” w poszerzonej ramce: jasne, szare i gładkie piksele precz z maski."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.blur(g, (15, 15))
    sd = np.sqrt(np.maximum(cv2.blur(g * g, (15, 15)) - mu * mu, 0))
    paper = (hsv[..., 2] > 185) & (hsv[..., 1] < 30) & (sd < 7)
    paper = cv2.morphologyEx(paper.astype(np.uint8), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    return clean(m & (1 - paper))


def rib_score(out, a):
    """Ściągacz = pionowe prążki: przewaga gradientu poziomego. Zwraca (góra, dół) ćwiartki próbki."""
    g = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx, gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)), np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    inner = cv2.erode((a > 0.5).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    ys = np.nonzero(inner.any(1))[0]
    if len(ys) < 20:
        return 0.0, 0.0
    q = (ys[-1] - ys[0]) // 4

    def part(y0, y1):
        mm = inner[y0:y1]
        return float(gx[y0:y1][mm].mean() / (gy[y0:y1][mm].mean() + 1e-3)) if mm.any() else 1.0
    return part(ys[0], ys[0] + q), part(ys[-1] - q, ys[-1])


def place(img, m, size, deg=0, pad=0.06):
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop, a = img[y0:y1, x0:x1].astype(np.float32), m[y0:y1, x0:x1].astype(np.float32)
    a = cv2.GaussianBlur(a, (0, 0), 1.2)[..., None]
    k = (deg // 90) % 4  # obrót w prawo: ściągacz na dół
    crop, a = np.ascontiguousarray(np.rot90(crop, -k)), np.ascontiguousarray(np.rot90(a, -k))
    h, w = a.shape[:2]
    s = size * (1 - 2 * pad) / max(h, w)
    crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    a = cv2.resize(a, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_AREA)[..., None]
    out = np.full((size, size, 3), 255, np.float32)
    oy, ox = (size - crop.shape[0]) // 2, (size - crop.shape[1]) // 2
    reg = out[oy:oy + crop.shape[0], ox:ox + crop.shape[1]]
    out[oy:oy + crop.shape[0], ox:ox + crop.shape[1]] = reg * (1 - a) + crop * a
    alpha = np.zeros((size, size), np.float32)
    alpha[oy:oy + crop.shape[0], ox:ox + crop.shape[1]] = a[..., 0]
    return out.astype(np.uint8), alpha


def norm(label):
    """„SET.12”, „ZESTAW 12”, „set 12” → „SET 12” (nazwy kolorów z manifest.json)."""
    m = re.search(r'(\d+\s*[A-Z]?)\s*$', label.upper())
    return 'SET ' + m.group(1).replace(' ', '') if m else label


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, ramki, dst = args
    size = int(opts.get('size') or 1000)
    pad = float(opts.get('zapas') or 0.08)  # ramki Gemini bywają ciasne (ucięty ściągacz) — szukamy szerzej
    only = opts['tylko'].split(',') if opts.get('tylko') else None
    manifest = json.load(open(os.path.join(HERE, 'manifest.json')))
    kier = json.load(open(os.path.join(HERE, opts['kierunki']))) if opts.get('kierunki') else {}
    out_manifest = {}
    # ręczne poprawki po przeglądzie: {karta: {kolor|IMG|'*': stopnie w prawo}} nakładane na gotową próbkę
    fp = os.path.join(HERE, 'obroty-probek.json')
    fix = json.load(open(fp)) if os.path.exists(fp) else {}
    for karta, colors in sorted(manifest.items()):
        if not karta.startswith('COLORCARD AZ') or (only and not any(o in karta for o in only)):
            continue
        by_photo = {}
        for c, (fn, deg) in colors.items():
            by_photo.setdefault(fn, []).append((c, deg))
        thumbs = []
        for fn, cs in sorted(by_photo.items()):
            stem = fn.split('.')[0]
            ip, jp = os.path.join(src, karta, stem + '.jpg'), os.path.join(ramki, karta, fn + '.json')
            if not os.path.exists(ip) or not os.path.exists(jp):
                print('  brak zdjęcia/ramek', karta, fn, flush=True)
                continue
            img = cv2.imread(ip)
            H, W = img.shape[:2]
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            rot = False
            if opts.get('oryginaly'):
                o = cv2.imread(os.path.join(opts['oryginaly'], karta, fn), cv2.IMREAD_REDUCED_GRAYSCALE_8)
                rot = o is not None and o.shape[1] > o.shape[0]
            done = []

            def centre(q):
                if q.get('punkt') and not rot:
                    return q['punkt'][1] * W / 1000, q['punkt'][0] * H / 1000
                a0, b0, a1, b1 = q['box_2d']
                if rot:
                    a0, b0, a1, b1 = b0, 1000 - a1, b1, 1000 - a0
                return (b0 + b1) / 2 * W / 1000, (a0 + a1) / 2 * H / 1000
            frames = {norm(r['label']): r for r in json.load(open(jp)) if len(r.get('box_2d') or []) == 4 and r.get('label')}
            kk = kier.get(karta)
            for c, deg in cs:
                r = frames.get(norm(c))
                if r is None:
                    print('  brak ramki', karta, fn, c, flush=True)
                    continue
                if kk is not None:
                    deg = kk.get(fn, kk.get('*', 0)) if isinstance(kk, dict) else kk
                y0, x0, y1, x1 = r['box_2d']
                if rot:  # 90° w prawo: x' = 1000 - y, y' = x
                    y0, x0, y1, x1 = x0, 1000 - y1, x1, 1000 - y0
                bw, bh = (x1 - x0) * W / 1000, (y1 - y0) * H / 1000
                box = [max(0, x0 * W / 1000 - pad * bw), max(0, y0 * H / 1000 - pad * bh),
                       min(W, x1 * W / 1000 + pad * bw), min(H, y1 * H / 1000 + pad * bh)]
                pt = None
                if r.get('punkt') and not rot:
                    pt = [r['punkt'][1] * W / 1000, r['punkt'][0] * H / 1000]
                neg = [centre(q) for q in frames.values() if q is not r]
                m = no_paper(img, clean(sam_mask(rgb, box, pt, neg)))
                bx = np.zeros_like(m)  # nie wychodzimy poza poszerzoną ramkę (sąsiednia próbka)
                bx[int(box[1]):int(box[3]), int(box[0]):int(box[2])] = 1
                m &= bx
                if m.sum() < 0.3 * bw * bh:
                    print('  słaba maska', karta, fn, c, flush=True)
                    if not m.any():
                        continue
                out, alpha = place(img, m, size, (deg - (90 if rot else 0)) % 360)
                done.append((c, deg, out, rib_score(out, alpha)))
            # próbki na jednym zdjęciu leżą tak samo: jeśli prążki (ściągacz) wychodzą u góry — wszystkie o 180°
            vote = sum(t - b for _, _, _, (t, b) in done)
            flip = vote > 0.15 * max(1, len(done))
            for c, deg, out, _ in done:
                f = (fix.get(karta) or {}).get(c, (fix.get(karta) or {}).get(fn, (fix.get(karta) or {}).get('*')))
                if flip:
                    out = np.ascontiguousarray(out[::-1, ::-1])
                if f is not None:  # obroty-probek.json: dodatkowy obrót po głosowaniu
                    out = np.ascontiguousarray(np.rot90(out, -(f // 90)))
                os.makedirs(os.path.join(dst, karta), exist_ok=True)
                cv2.imwrite(os.path.join(dst, karta, f'{c}.jpg'), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                out_manifest.setdefault(karta, {})[c] = [fn, deg]
                t = cv2.resize(out, (220, 220))
                cv2.putText(t, c, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1)
                thumbs.append((c, t))
        print(karta, len(thumbs), '/', len(colors), flush=True)
        if thumbs:
            ts = [t for _, t in sorted(thumbs, key=lambda x: natural(x[0]))]
            while len(ts) % 8:
                ts.append(np.full_like(ts[0], 255))
            os.makedirs(os.path.join(dst, '_podglad'), exist_ok=True)
            cv2.imwrite(os.path.join(dst, '_podglad', karta + '.jpg'), np.vstack([np.hstack(ts[i:i + 8]) for i in range(0, len(ts), 8)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    json.dump(out_manifest, open(os.path.join(dst, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


if __name__ == '__main__':
    main()
