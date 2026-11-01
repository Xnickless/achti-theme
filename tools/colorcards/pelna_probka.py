"""Kółko = cała próbka jak czapka: ściągacz na dole, dzianina nad nim, bez metki (wzór Kamila 15.10.2026, AZ-2344PC).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/pelna_probka.py SRC GEM OUT KARTA [--obrot=plik:stopnie,…] [--ramka="SET n:ymin,xmin,ymax,xmax;…"]

SRC/GEM = zdjęcia i ramki z wskaz.py --tryb=probka (box_2d = cała próbka, tag_2d = metka, rotation = stopnie w prawo,
żeby ściągacz był na dole). Próbka jest obracana, metka zamalowana dzianiną z tych samych rzędów obok (pasy kolorów
i prążki ściągacza biegną wzdłuż rzędu, więc przesunięcie w bok ich nie psuje), potem kwadrat przy dolnej krawędzi
(cały ściągacz) na pełną szerokość próbki. --obrot nadpisuje obrót całego zdjęcia, gdy Gemini się pomylił.
"""
import json
import os
import re
import sys

import cv2
import numpy as np

SIZE = 480
INSET = 0.04   # odcięcie postrzępionych krawędzi i tła z ramki próbki
PAD = 0.03     # zapas wokół metki (sznurek, cień)
CUFF = 0.28    # część kółka na ściągacz (wzór: ok. 1/4)


def patch_tag(img, x0, y0, x1, y1):
    """Zamalowuje prostokąt pikselami z tych samych rzędów przesuniętymi w bok o szerokość metki."""
    h, w = img.shape[:2]
    x0, x1, y0, y1 = max(0, x0), min(w, x1), max(0, y0), min(h, y1)
    tw = x1 - x0
    if tw <= 0 or y1 <= y0:
        return img
    out = img.copy()
    src = np.zeros_like(img[y0:y1, x0:x1])
    right = w - x1 >= x0   # bierzemy dzianinę z szerszej strony; gdy za mało miejsca — odbicie lustrzane
    room = (w - x1) if right else x0
    for c in range(tw):
        k = c if right else tw - 1 - c
        k = k % (2 * room) if room else 0
        k = k if k < room else 2 * room - 1 - k
        src[:, c] = img[y0:y1, x1 + k if right else x0 - 1 - k]
    # miękkie przejście 12 px przy krawędziach łaty
    f = 12
    m = np.ones((y1 - y0, tw), np.float32)
    ramp = np.linspace(0, 1, f + 2)[1:-1]
    for i, v in enumerate(ramp):
        if x0 > 0 and i < tw:
            m[:, i] = np.minimum(m[:, i], v)
        if x1 < w and i < tw:
            m[:, tw - 1 - i] = np.minimum(m[:, tw - 1 - i], v)
        if y0 > 0 and i < y1 - y0:
            m[i, :] = np.minimum(m[i, :], v)
        if y1 < h and i < y1 - y0:
            m[y1 - y0 - 1 - i, :] = np.minimum(m[y1 - y0 - 1 - i, :], v)
    # łata zachodzi na metkę o pełne f px, więc przejście leży na dzianinie
    region = out[y0:y1, x0:x1].astype(np.float32)
    out[y0:y1, x0:x1] = (src * m[..., None] + region * (1 - m[..., None])).astype(np.uint8)
    return out


def fabric_mask(img):
    """Dzianina = różnica od tła (mediana brzegu zdjęcia) albo faktura — jak sample_mask w wytnij.py."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    b = 20
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3),
                             lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    dist = np.sqrt(((lab - np.median(border, axis=0)) ** 2 * np.array([0.35, 1.0, 1.0])).sum(axis=2))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (15, 15))
    tex = np.sqrt(np.maximum(cv2.blur(gray * gray, (15, 15)) - mean * mean, 0))
    m = ((dist > 14) | (tex > 9)).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    return cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)


def runs(ok):
    """Najdłuższy ciąg True: (początek, koniec)."""
    best, start = (0, 0), None
    for i, v in enumerate(list(ok) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            best = max(best, (start, i), key=lambda r: r[1] - r[0])
            start = None
    return best


def cuff_top(win, ok):
    """Górna krawędź ściągacza: od dołu w górę, dopóki rzędy mają słabą fakturę w pionie (prążki biegną pionowo)."""
    g = cv2.GaussianBlur(cv2.cvtColor(win, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
    gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5))
    row = np.array([gy[r][ok[r]].mean() if ok[r].sum() > ok.shape[1] * 0.2 else np.nan for r in range(len(g))])
    row = np.where(np.isnan(row), np.nanmedian(row), row)
    row = np.convolve(row, np.ones(15) / 15, 'same')
    h = len(row)
    body, rib = np.median(row[:int(h * 0.4)]), np.median(row[int(h * 0.85):int(h * 0.97)])
    # granica = największy skok: nad nią faktura dzianiny, pod nią gładsze prążki
    win_ = max(20, h // 15)
    best, r = -1e9, int(h * 0.6)
    for k in range(int(h * 0.35), int(h * 0.9)):
        d = row[max(0, k - win_):k].mean() - row[k:k + win_].mean()
        if d > best:
            best, r = d, k
    return r, body, rib


def cuff_columns(rows, tag):
    """Kolumny ściągacza bez metki, sznurka i tła: prawie wszystkie piksele w kolorze ściągacza (mediana, Lab)."""
    lab = cv2.cvtColor(cv2.GaussianBlur(rows, (0, 0), 1.5), cv2.COLOR_BGR2LAB).astype(np.float32)
    med = np.median(lab[~tag] if (~tag).sum() > 500 else lab.reshape(-1, 3), axis=0)
    d = np.sqrt(((lab - med) ** 2 * np.array([0.5, 1.0, 1.0])).sum(axis=2))
    thr = max(26.0, 3.5 * float(np.median(d)))   # cienie między prążkami mieszczą się w progu, metka i tło nie
    good = ((d > thr).mean(axis=0) < 0.02) & (tag.mean(axis=0) < 0.02)
    return cv2.erode(good.astype(np.uint8)[None], np.ones((1, 11), np.uint8))[0] > 0


def sample(img, fab, b, tag, rot, debug=None):
    H, W = img.shape[:2]
    y0, x0, y1, x1 = b[0] * H / 1000, b[1] * W / 1000, b[2] * H / 1000, b[3] * W / 1000
    dy, dx = (y1 - y0) * INSET, (x1 - x0) * INSET
    y0, x0, y1, x1 = int(y0 + dy), int(x0 + dx), int(y1 - dy), int(x1 - dx)
    win, ok = img[y0:y1, x0:x1].copy(), fab[y0:y1, x0:x1] > 0
    tagm = np.zeros(win.shape[:2], bool)
    if tag:
        ty0, tx0, ty1, tx1 = tag[0] * H / 1000, tag[1] * W / 1000, tag[2] * H / 1000, tag[3] * W / 1000
        py, px = (ty1 - ty0) * PAD + 14, (tx1 - tx0) * PAD + 14
        tagm[max(0, int(ty0 - py - y0)):max(0, int(ty1 + py - y0)), max(0, int(tx0 - px - x0)):max(0, int(tx1 + px - x0))] = True
    k = {0: 0, 90: -1, 180: 2, 270: 1}[rot % 360]   # stopnie w prawo → np.rot90 (w lewo)
    win, ok, tagm = (np.ascontiguousarray(np.rot90(a, k)) for a in (win, ok, tagm))
    h, w = win.shape[:2]
    clean = ok & ~tagm
    ct, body, rib = cuff_top(win, clean)
    # szerokość dzianiny tuż nad ściągaczem
    band = slice(max(0, ct - max(20, (h - ct) // 2)), ct)
    bx0, bx1 = runs(ok[band].mean(axis=0) > 0.9)
    s = bx1 - bx0
    c = min(int(s * CUFF), h - ct)            # widoczna, górna (najszersza) część ściągacza
    if s > ct + c:                            # próbka za niska na pełną szerokość
        s = int((ct) / (1 - CUFF))
        c = min(int(s * CUFF), h - ct)
    bx0 += (bx1 - bx0 - s) // 2
    bot = ct + c
    part = win[bot - s:bot, bx0:bx0 + s].copy()
    pc, pok, ptag = ok[bot - s:bot, bx0:bx0 + s], clean[bot - s:bot, bx0:bx0 + s], tagm[bot - s:bot, bx0:bx0 + s]
    k0 = s - c                                 # pierwszy rząd ściągacza w kwadracie
    # dzianina: metka zamalowana dzianiną z tych samych rzędów
    ys, xs = np.nonzero(ptag[:k0])
    if len(ys):
        part[:k0] = patch_tag(part[:k0], xs.min(), ys.min(), xs.max() + 1, k0)
    # ściągacz: czysty fragment (bez metki i tła) powtarzany w bok co wielokrotność rozstawu prążków
    good = cuff_columns(part[k0:], ptag[k0:])
    strict = good & (pc[k0:].mean(axis=0) > 0.98)   # jasny ściągacz (kremowy) maska tła gubi — wtedy sam kolor
    cx0, cx1 = runs(strict)
    if cx1 - cx0 < 40:
        cx0, cx1 = runs(good)
    if cx1 - cx0 >= 60:                       # brzegi czystego fragmentu to często szew próbki albo cień metki
        m = (cx1 - cx0) // 7
        cx0, cx1 = cx0 + m, cx1 - m
    L = cx1 - cx0
    if L >= 12 and L < s:
        g = cv2.cvtColor(part[k0:], cv2.COLOR_BGR2GRAY).astype(np.float32).mean(axis=0)[cx0:cx1]
        g = g - g.mean()
        ac = np.correlate(g, g, 'full')[L - 1:]
        lo = 6
        per = lo + int(np.argmax(ac[lo:L // 2])) if L // 2 > lo + 1 else L
        L = max(per, L // per * per)
        src = np.array([cx0 + (x - cx0) % L for x in range(s)])
        # cały ściągacz z czystego wycinka — równe prążki bez sznurka, szwów i postrzępionych brzegów
        part[k0:] = part[k0:][:, src]
    # dziury tła w dzianinie (wcięcia między dzianiną a ściągaczem, brzegi) — wypełnienie z otoczenia
    hsv = cv2.cvtColor(part[:k0], cv2.COLOR_BGR2HSV)
    g = cv2.cvtColor(part[:k0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(g, (9, 9))
    flat = np.sqrt(np.maximum(cv2.blur(g * g, (9, 9)) - mean * mean, 0)) < 5
    paper = ((hsv[..., 2] > 205) & (hsv[..., 1] < 30) & flat).astype(np.uint8)
    paper = cv2.morphologyEx(paper, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))   # gładka jasna płaszczyzna, nie biała przędza
    hole = ((~pc[:k0]) | (paper > 0)).astype(np.uint8)
    hole[:, :] = cv2.morphologyEx(hole, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    if hole.any():
        part[:k0] = cv2.inpaint(part[:k0], cv2.dilate(hole, np.ones((7, 7), np.uint8)), 9, cv2.INPAINT_TELEA)
    sq = part
    if debug is not None:
        debug.update(ct=ct, h=h, w=w, s=s, c=c, cuff=(cx0, cx1), L=L, body=round(float(body), 1), rib=round(float(rib), 1))
    return cv2.resize(sq, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def trim_overlaps(samples):
    """Ramki sąsiednich próbek zachodzą na siebie — cięcie w połowie zakładki."""
    for s in samples:
        for o in samples:
            b, c = s['box_2d'], o['box_2d']
            if o is s or b[0] >= c[2] or c[0] >= b[2] or b[1] >= c[3] or c[1] >= b[3]:
                continue
            oy, ox = min(b[2], c[2]) - max(b[0], c[0]), min(b[3], c[3]) - max(b[1], c[1])
            if oy < ox and oy < (b[2] - b[0]) * 0.3:
                if b[0] < c[0]:
                    b[2] = min(b[2], (b[2] + c[0]) / 2)
                else:
                    b[0] = max(b[0], (c[2] + b[0]) / 2)
            elif ox <= oy and ox < (b[3] - b[1]) * 0.3:
                if b[1] < c[1]:
                    b[3] = min(b[3], (b[3] + c[1]) / 2)
                else:
                    b[1] = max(b[1], (c[3] + b[1]) / 2)
    return samples


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:] + '=').split('=')[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, gem, out, card = args
    fix = dict((p.split(':')[0], int(p.split(':')[1])) for p in opts.get('obrot', '').split(',') if p)
    # --ramka="SET 11:339,522,558,988;…" — ręczna ramka próbki (0–1000), gdy Gemini złapał kawałek sąsiedniej
    boxes = {p.split(':')[0]: [float(v) for v in p.split(':')[1].split(',')] for p in opts.get('ramka', '').split(';') if p}
    os.makedirs(os.path.join(out, card), exist_ok=True)
    done = []
    for fn in sorted(os.listdir(os.path.join(src, card))):
        jp = os.path.join(gem, card, fn + '.json')
        if not os.path.exists(jp):
            continue
        img = cv2.imread(os.path.join(src, card, fn))
        fab = fabric_mask(img)
        samples = trim_overlaps(json.load(open(jp)))
        for s in samples:
            m = re.search(r'SET\W*(\d+)', s.get('label', ''))
            if not m:
                print('pomijam', fn, repr(s.get('label')))
                continue
            name = f'SET {int(m.group(1))}'
            rot = fix.get(fn, s.get('rotation', 0))
            s['box_2d'] = boxes.get(name, s['box_2d'])
            dbg = {}
            cv2.imwrite(os.path.join(out, card, name + '.jpg'), sample(img, fab, s['box_2d'], s.get('tag_2d'), rot, dbg),
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            if 'debug' in opts:
                print(name, fn, rot, dbg)
            done.append(name)
    print(len(done), 'kółek:', ', '.join(sorted(done, key=lambda t: int(t[4:]))))


if __name__ == '__main__':
    main()
