"""Wycina okrągłe próbki kolorów ze zdjęć kolorników Adriana (COLORCARDS ACHTI).

Wejście: zdjęcia pomniejszone do 2000 px (<src>/<folder>/<plik>.JPG) + wynik OCR macOS Vision
(<ocr>/<folder>/<plik>.JPG.json z tools/colorcards/ocr.swift).

Dwa rodzaje kart:
- karta modelu: próbki dzianiny z metką „SET 7” — kolor = „SET 7”,
- paleta przędzy (LEGS, merino…): motki/próbki z numerem koloru — kolor = numer.

Dla każdej etykiety: próbka = obszar odróżniający się od tła (kolor lub faktura), do którego
etykieta jest najbliżej; wycinamy największe koło w próbce, omijając metki i napisy.
Wynik: <out>/<folder>/<kolor>.jpg (240 px, kwadrat; koło robi CSS) + <out>/manifest.json.
Ręczne poprawki: tools/colorcards/poprawki.json ({"folder": {"kolor": [plik, cx, cy, r] | null}}),
współrzędne w pikselach obrazu 2000 px.

Uruchamiać pythonem z OpenCV: [KADR=probka] [SIZE=480] ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/wytnij.py SRC OCR OUT [GEMINI] [ZAPAS]
Gdy jest katalog GEMINI (wynik wskaz.py), ramki z Gemini mają pierwszeństwo przed maską.
"""
import json
import os
import re
import sys

import cv2
import numpy as np

SIZE = int(os.environ.get('SIZE', 240))
# KADR=probka: cała szerokość próbki (wzór Adriana 13.10.2026); domyślnie ~60 % w miejscu najbogatszego wzoru (08.10)
KADR = os.environ.get('KADR', '')
SET_RE = re.compile(r'(?:S\s*E\s*T|ZESTAW)\s*[.:,]?\s*(\d{1,2})', re.I)  # Gemini czasem pisze „ZESTAW 9”
CODE_RE = re.compile(r'^(?:[A-Z]{1,3}[- ]?)?\d{2,6}(?:-\d{1,4})?$|^\d[A-Z0-9]{2}$|^[A-Z]\d[A-Z0-9]$')
NOISE = {'LEGS', 'LEGS®', 'SET'}


def labels(ocr):
    """Etykiety kolorów z OCR: (kolor, typ, box) — typ 'set' albo 'code'."""
    out = []
    for it in ocr['items']:
        t = it['text'].strip()
        box = (it['x'], it['y'], it['w'], it['h'])
        m = SET_RE.search(t)
        if m:
            out.append(('SET ' + str(int(m.group(1))), 'set', box))
            continue
        u = t.upper().replace('O', '0') if re.fullmatch(r'[0-9O]+', t.upper()) else t.upper()
        if u in NOISE or len(u) > 9:
            continue
        if CODE_RE.match(u):
            out.append((u, 'code', box))
    return out


def sample_mask(img):
    """Maska próbek: różnica od tła (mediana brzegu) albo wyraźna faktura."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = img.shape[:2]
    b = 20
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3),
                             lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    # tło bywa nierówno oświetlone: porównujemy z rozmytym obrazem tła tylko kolor (a, b) i jasność z tolerancją
    dist = np.sqrt(((lab - bg) ** 2 * np.array([0.35, 1.0, 1.0])).sum(axis=2))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (15, 15))
    sq = cv2.blur(gray * gray, (15, 15))
    tex = np.sqrt(np.maximum(sq - mean * mean, 0))
    m = ((dist > 14) | (tex > 9)).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    return m


def tag_mask(img, ocr, shape):
    """Obszary do ominięcia: napisy z OCR (powiększone) + jasne, gładkie metki."""
    h, w = shape
    ex = np.zeros((h, w), np.uint8)
    for it in ocr['items']:
        x, y, bw, bh = it['x'], it['y'], it['w'], it['h']
        pad = int(max(bw, bh) * 0.9) + 25
        cv2.rectangle(ex, (x - pad, y - pad), (x + bw + pad, y + bh + pad), 1, -1)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mean = cv2.blur(gray, (9, 9))
    tex = np.sqrt(np.maximum(cv2.blur(gray * gray, (9, 9)) - mean * mean, 0))
    white_flat = ((hsv[..., 2] > 225) & (hsv[..., 1] < 25) & (tex < 4)).astype(np.uint8)
    white_flat = cv2.morphologyEx(white_flat, cv2.MORPH_OPEN, np.ones((25, 25), np.uint8))
    return ex | white_flat


def best_circle(mask, ex, near, max_r):
    """Największe koło w masce poza wykluczeniami, możliwie blisko punktu `near`."""
    ok = (mask > 0) & (ex == 0)
    dt = cv2.distanceTransform(ok.astype(np.uint8), cv2.DIST_L2, 5)
    dt = np.minimum(dt, max_r)
    yy, xx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    d_near = np.sqrt((xx - near[0]) ** 2 + (yy - near[1]) ** 2)
    score = dt - 0.08 * d_near
    i = int(np.argmax(score))
    cy, cx = divmod(i, mask.shape[1])
    return int(cx), int(cy), float(dt[cy, cx])


def crop(img, cx, cy, r):
    r = int(r * 0.92)
    x0, y0 = max(cx - r, 0), max(cy - r, 0)
    c = img[y0:cy + r, x0:cx + r]
    return cv2.resize(c, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def motif_square(img, b):
    """Tryb „motyw”: dokładnie wskazany kwadrat (jeden cały motyw, np. serce, z marginesem tła), obrót jak na czapce."""
    h, w = img.shape[:2]
    y0, x0, y1, x1 = [float(v) for v in b['box_2d']]
    c = img[int(y0 * h / 1000):int(y1 * h / 1000), int(x0 * w / 1000):int(x1 * w / 1000)]
    k = int(b.get('rotation', 0)) % 360
    if k:
        c = np.ascontiguousarray(np.rot90(c, -k // 90))
    ch, cw = c.shape[:2]
    if min(ch, cw) < 30:
        return None
    s = min(ch, cw)
    c = c[(ch - s) // 2:(ch - s) // 2 + s, (cw - s) // 2:(cw - s) // 2 + s]
    return cv2.resize(c, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def probka_square(img, b, ocr):
    """Kadr Adriana (13.10.2026): kwadrat o boku całej szerokości próbki w poprzek pasów, pasy pionowo
    (Kamil: „wszystkie próbki mają być w pionie”), w miejscu bez metki.
    Ramki z `wskaz.py --tryb=probka`: box_2d = cała próbka, tag_2d = jej metka; dodatkowo metki z OCR."""
    h, w = img.shape[:2]
    y0, x0, y1, x1 = [float(v) * s / 1000 for v, s in zip(b['box_2d'], (h, w, h, w))]
    iy, ix = (y1 - y0) * 0.04, (x1 - x0) * 0.04  # bez obrębienia i tła na brzegach
    y0, y1, x0, x1 = int(y0 + iy), int(y1 - iy), int(x0 + ix), int(x1 - ix)
    tag = np.zeros((h, w), np.uint8)
    tags = [b[k] for k in ('tag_2d', 'label_2d') if b.get(k)]  # model czasem pisze label_2d
    for t in tags:
        ty0, tx0, ty1, tx1 = [float(v) * s / 1000 for v, s in zip(t, (h, w, h, w))]
        if (ty1 - ty0) * (tx1 - tx0) > 0.4 * (y1 - y0) * (x1 - x0):
            continue  # „metka” na pół próbki to błąd modelu — zostają OCR i biały papier
        py, px = (ty1 - ty0) * 0.08, (tx1 - tx0) * 0.08
        cv2.rectangle(tag, (int(tx0 - px), int(ty0 - py)), (int(tx1 + px), int(ty1 + py)), 1, -1)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    for it in ocr['items']:  # napisy na jasnym kartoniku (wrobione w dzianinę napisy zostają)
        x, y, bw, bh = it['x'], it['y'], it['w'], it['h']
        if max(bw, bh) > 0.2 * max(h, w):
            continue
        pad = int(max(bw, bh) * 0.5) + 10
        ys, xs = slice(max(y - pad, 0), y + bh + pad), slice(max(x - pad, 0), x + bw + pad)
        if ((hsv[ys, xs, 2] > 190) & (hsv[ys, xs, 1] < 60)).mean() >= 0.45:
            cv2.rectangle(tag, (x - pad, y - pad), (x + bw + pad, y + bh + pad), 1, -1)
    # papier metki i tło: jasne, mało nasycone i gładkie (biała włóczka ma fakturę ściegu)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.blur(g, (9, 9))
    tex = np.sqrt(np.maximum(cv2.blur(g * g, (9, 9)) - mu * mu, 0))
    flat = ((hsv[..., 2] > 200) & (hsv[..., 1] < 30) & (tex < 4)).astype(np.uint8)
    tag |= cv2.dilate(cv2.morphologyEx(flat, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8)), np.ones((9, 9), np.uint8))
    vertical = int(b.get('rotation', 0)) % 180 == 90  # pasy pionowo na zdjęciu (ściągacz z boku)
    # szukanie na obrazie /4; zasłonięcie liczone tylko w kole (rogi kwadratu i tak obcina CSS)
    q = 4
    tq = cv2.resize(tag.astype(np.float32), (w // q, h // q), interpolation=cv2.INTER_AREA)
    gq = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (w // q, h // q), interpolation=cv2.INTER_AREA).astype(np.float32)
    full = min(x1 - x0, y1 - y0) // q
    best = None
    for f in (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.45, 0.4, 0.35, 0.3):
        sd = int(full * f)
        if sd < 15:
            break
        yy_, xx_ = np.mgrid[0:sd, 0:sd]
        circ = ((yy_ - sd / 2 + 0.5) ** 2 + (xx_ - sd / 2 + 0.5) ** 2 <= (sd / 2) ** 2).astype(np.float32)
        cn = circ.sum()
        cand = None
        for yy in range(y0 // q, y1 // q - sd + 1, max(2, sd // 25)):
            for xx in range(x0 // q, x1 // q - sd + 1, max(2, sd // 25)):
                ov = float((tq[yy:yy + sd, xx:xx + sd] * circ).sum() / cn)
                score = ov * 4 - gq[yy:yy + sd, xx:xx + sd].std() / 400
                if cand is None or score < cand[0]:
                    cand = (score, xx * q, yy * q, ov, sd * q)
        if cand and (best is None or cand[3] < best[3]):
            best = cand
        if best and best[3] <= 0.01:
            break
    if not best or best[3] > 0.06:
        return None  # metka wszędzie — inne zdjęcie tej próbki
    side = best[4]
    _, X, Y, _, _ = best
    win = img[Y:Y + side, X:X + side]
    # Kamil 14.10.2026: „kolory od góry do dołu, a nie od lewej do prawej” — próbka jak na czapce: pasy poziomo,
    # ściągacz na dole (13.10 były pasy pionowo). Kierunek mierzony na samym wycinku (obrót od Gemini bywa błędny).
    vx, vy = band_profile(win)
    gx, gy = grad_xy(win)
    if max(vx, vy) > 4.0:
        rotate = vx > 1.3 * vy
    else:
        # jeden kolor: prążki (ściągacz, warkocze) pionowo, jak na czapce
        rotate = gy > 1.1 * gx if max(gx, gy) > 1.1 * min(gx, gy) else vertical
    if rotate:
        win = np.ascontiguousarray(np.rot90(win, 1))
    sq = cv2.resize(win, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    # ściągacz na dół rozstrzyga main() głosowaniem wszystkich próbek ze zdjęcia (leżą tak samo), bo pojedynczy
    # ciemny ściągacz nie pokazuje prążków; obrót z Gemini bywał błędny
    CUFF[id(sq)] = (rotate, rib_score(sq[-SIZE // 4:]) - rib_score(sq[:SIZE // 4]))
    return sq


CUFF = {}


def rib_score(strip):
    """Jak bardzo pasek wygląda na ściągacz: proste pionowe prążki — średnie kolumn mocno zmienne względem całej faktury."""
    g = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g -= cv2.GaussianBlur(g, (0, 0), 12)
    w = g.shape[1] // 4
    return float(np.median([g[:, k * w:(k + 1) * w].mean(axis=0).std() / (g[:, k * w:(k + 1) * w].std() + 1e-3)
                            for k in range(4)]))


def grad_xy(win):
    """Średni gradient w poziomie i w pionie (faktura dzianiny) na szarym wycinku 192 px."""
    g = cv2.cvtColor(cv2.resize(win, (192, 192), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    return (float(np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)).mean()),
            float(np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)).mean()))


def band_profile(win):
    """Zmienność koloru w poziomie (vx: pasy pionowe) i w pionie (vy: pasy poziome), Lab po rozmyciu."""
    lab = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(win, (96, 96), interpolation=cv2.INTER_AREA),
                                        cv2.COLOR_BGR2LAB).astype(np.float32), (21, 21), 0)
    return (float(np.linalg.norm(lab.mean(axis=0).std(axis=0))),
            float(np.linalg.norm(lab.mean(axis=1).std(axis=0))))


def band_square(img, b, ocr=None):
    """Kwadrat z ramki Gemini w trybie set: obrót jak na czapce, pełna wysokość (wszystkie pasy),
    za wąska ramka → rozciągnięcie w poziomie (do 3×), dalej przycięcie góry i dołu."""
    h, w = img.shape[:2]
    y0, x0, y1, x1 = [float(v) for v in b['box_2d']]
    # 6 % od brzegów ramki (3 % w kadrze „probka”, żeby został brzeg ściągacza): bez obrębienia, tła i krawędzi metki
    m = 0.03 if KADR == 'probka' else 0.06
    dy, dx = (y1 - y0) * m, (x1 - x0) * m
    y0, y1, x0, x1 = y0 + dy, y1 - dy, x0 + dx, x1 - dx
    Y0, Y1, X0, X1 = int(y0 * h / 1000), int(y1 * h / 1000), int(x0 * w / 1000), int(x1 * w / 1000)
    c = img[Y0:Y1, X0:X1]
    # metki w kadrze: napis z OCR leżący na jasnym, gładkim kartoniku (wrobione w dzianinę napisy mają fakturę)
    tag = np.zeros(c.shape[:2], np.uint8)
    if ocr is not None and c.size:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
        for it in ocr['items']:
            x, y, bw, bh = it['x'], it['y'], it['w'], it['h']
            if x > X1 or x + bw < X0 or y > Y1 or y + bh < Y0:
                continue
            pad = int(max(bw, bh) * 0.5) + 10
            ys, xs = slice(max(y - pad, 0), y + bh + pad), slice(max(x - pad, 0), x + bw + pad)
            bright = (hsv[ys, xs, 2] > 190) & (hsv[ys, xs, 1] < 60)
            if bright.mean() < 0.45:
                continue
            p2 = int(max(bw, bh) * 1.1) + 20  # cały kartonik, nie tylko napis
            cv2.rectangle(tag, (x - p2 - X0, y - p2 - Y0), (x + bw + p2 - X0, y + bh + p2 - Y0), 1, -1)
    k = int(b.get('rotation', 0)) % 360
    if k:
        c = np.ascontiguousarray(np.rot90(c, -k // 90))
        tag = np.ascontiguousarray(np.rot90(tag, -k // 90))
    if tag.any():
        free = tag.max(axis=0) == 0
        best, cur, start = (0, 0), 0, 0
        for i, f in enumerate(list(free) + [False]):
            if f:
                start, cur = (i, 1) if cur == 0 else (start, cur + 1)
            else:
                if cur > best[1] - best[0]:
                    best = (start, start + cur)
                cur = 0
        if best[1] - best[0] < 0.25 * c.shape[0]:
            return None  # metka zabiera prawie całą szerokość — zapas z pierwszego przebiegu
        c = c[:, best[0]:best[1]]
    ch, cw = c.shape[:2]
    if ch < 40 or cw < 20:
        return None
    # motyw (życzenie Adriana 10.10.2026, AZ-3102PC): jeden cały kształt (serce, gwiazdka) z marginesem tła
    sq = find_motif(c)
    if sq is not None:
        return cv2.resize(sq, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    if KADR == 'probka':
        # wzór Adriana 13.10.2026 (AZ-1748PC SET 7, „elegancko wycina”): kwadrat o boku całej szerokości próbki —
        # wszystkie pasy od brzegu do ściągacza — w miejscu bez metki, ułożony tak jak leży na karcie (bez obrotu;
        # na jego przykładach ściągacz raz z prawej — 1748 — raz z lewej — 2349)
        side = min(ch, cw)
        y, x = rich_window(c, side) if cw > ch else ((ch - side) // 2, 0)
        win = np.ascontiguousarray(np.rot90(c[y:y + side, x:x + side], k // 90))
        return cv2.resize(win, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    # kadr jak zaznaczył Adrian (08.10.2026): kwadrat ~60 % wysokości próbki w miejscu najbogatszego wzoru;
    # gdy w kadrze brakuje któregoś koloru próbki (czapki z pasami, np. AZ-2349PC), kadr rośnie do 80 % i 100 %
    from kolory import palette
    want = len(palette(c))
    for frac in (0.6, 0.8):
        side = int(min(cw, frac * ch))
        if side < 40 or side >= min(cw, ch):
            break
        y, x = rich_window(c, side)
        win = c[y:y + side, x:x + side]
        if len(palette(win)) >= want:
            return cv2.resize(win, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    if cw >= ch:
        m = (cw - ch) // 2
        return cv2.resize(c[:, m:m + ch], (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    return cv2.resize(c, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def find_motif(c):
    """Największy zamknięty kształt w innym kolorze niż tło dzianiny, nie dotykający brzegu → kwadrat z marginesem."""
    ch, cw = c.shape[:2]
    if min(ch, cw) < 80:
        return None
    lab = cv2.cvtColor(cv2.GaussianBlur(c, (7, 7), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    px = lab.reshape(-1, 3)
    _, lbl, cent = cv2.kmeans(px, 3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                              cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(lbl.ravel(), minlength=3)
    bg = cent[int(np.argmax(counts))]
    if counts.max() < 0.45 * len(px):  # brak dominującego tła → wzór na całej powierzchni
        return None
    d = np.sqrt((((lab - bg) * np.array([0.6, 1, 1])) ** 2).sum(axis=2))
    m = (d > 22).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if x <= 2 or y <= 2 or x + bw >= cw - 2 or y + bh >= ch - 2:
            continue  # ucięty brzegiem
        if area < 0.03 * ch * cw or bw * bh > 0.5 * ch * cw or area < 0.35 * bw * bh:
            continue
        if bw > 2.5 * bh or bh > 2.5 * bw:
            continue  # pas, nie motyw
        if best is None or area > best[4]:
            best = (x, y, bw, bh, area)
    if best is None:
        return None
    x, y, bw, bh, _ = best
    side = int(max(bw, bh) * 1.4)
    side = min(side, ch, cw)
    if side < max(bw, bh):
        return None
    cx, cy = x + bw // 2, y + bh // 2
    x0 = int(np.clip(cx - side // 2, 0, cw - side))
    y0 = int(np.clip(cy - side // 2, 0, ch - side))
    return c[y0:y0 + side, x0:x0 + side]


def rich_window(c, side):
    """Kwadrat o boku side z największą ilością wzoru (krawędzie + rozrzut barw), lekko ku środkowi."""
    ch, cw = c.shape[:2]
    gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY).astype(np.float32)
    edge = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB).astype(np.float32)
    best, pos = -1.0, (0, 0)
    for y in range(0, ch - side + 1, max(1, (ch - side) // 12 or 1)):
        for x in range(0, cw - side + 1, max(1, (cw - side) // 8 or 1)):
            win = lab[y:y + side, x:x + side].reshape(-1, 3)
            score = float(edge[y:y + side, x:x + side].mean()) + 2.0 * float(win[:, 1:].std(axis=0).sum() + 0.5 * win[:, 0].std())
            score *= 1 - 0.15 * abs((y + side / 2) / ch - 0.5) - 0.1 * abs((x + side / 2) / cw - 0.5)
            if score > best:
                best, pos = score, (y, x)
    return pos


def set_name(label):
    m = SET_RE.search(str(label))
    return 'SET ' + str(int(m.group(1))) if m else None


def fallback_square(img, path, name, rotation):
    """Kwadrat bez metki z pierwszego przebiegu Gemini (box_2d), obrócony jak na czapce."""
    if not os.path.exists(path):
        return None
    old = [o for o in json.load(open(path)) if set_name(o.get('label', '')) == name]
    if not old:
        return None
    H, W = img.shape[:2]
    y0, x0, y1, x1 = [float(v) for v in old[0]['box_2d']]
    sq = crop(img, int((x0 + x1) / 2 * W / 1000), int((y0 + y1) / 2 * H / 1000),
              min((x1 - x0) * W, (y1 - y0) * H) / 2000)
    k = rotation % 360
    return np.ascontiguousarray(np.rot90(sq, -k // 90)) if k else sq


def from_boxes(img, boxes):
    """Koła z ramek Gemini: środek ramki, promień = połowa krótszego boku."""
    h, w = img.shape[:2]
    res = []
    for b in boxes:
        try:
            y0, x0, y1, x1 = [float(v) for v in b['box_2d']]
            name = str(b['label']).strip().upper()
        except (KeyError, ValueError, TypeError):
            continue
        m = SET_RE.search(name)
        name = 'SET ' + str(int(m.group(1))) if m else name.replace(' ', '').replace('/', '-')
        x0, x1, y0, y1 = x0 * w / 1000, x1 * w / 1000, y0 * h / 1000, y1 * h / 1000
        r = min(x1 - x0, y1 - y0) / 2
        if r >= 25:
            res.append((name, int((x0 + x1) / 2), int((y0 + y1) / 2), r))
    return res


def main(src, ocr_dir, out, boxes_dir=None, fallback_dir=None):
    fixes = {}
    fp = os.path.join(os.path.dirname(__file__), 'poprawki.json')
    if os.path.exists(fp):
        fixes = json.load(open(fp))
    tp = os.path.join(os.path.dirname(__file__), 'obroty.json')
    turns = json.load(open(tp)) if os.path.exists(tp) else {}
    # obroty-po.json: przegląd kółek 14.10.2026 (Gemini + ręcznie) — obrót gotowego kółka, nakładany po obroty.json
    tp2 = os.path.join(os.path.dirname(__file__), 'obroty-po.json')
    turns2 = json.load(open(tp2)) if os.path.exists(tp2) else {}
    manifest = {}
    uwagi, flagged = set(), set()
    for folder in sorted(os.listdir(src)):
        fdir = os.path.join(src, folder)
        if not os.path.isdir(fdir):
            continue
        best = {}
        for fn in sorted(os.listdir(fdir)):
            if not fn.lower().endswith(('.jpg', '.jpeg')):
                continue
            img = cv2.imread(os.path.join(fdir, fn))
            bp = boxes_dir and os.path.join(boxes_dir, folder, fn + '.json')
            if bp and os.path.exists(bp):
                data = json.load(open(bp))
                if KADR == 'probka' and data and any(SET_RE.search(str(d.get('label', ''))) for d in data):
                    # Gemini czasem pomija obrót — najczęstszy na tym zdjęciu, a gdy brak wszędzie: na całej karcie
                    rots = [int(d['rotation']) for d in data if 'rotation' in d]
                    if not rots:
                        for f2 in os.listdir(os.path.dirname(bp)):
                            rots += [int(d['rotation']) for d in json.load(open(os.path.join(os.path.dirname(bp), f2)))
                                     if isinstance(d, dict) and 'rotation' in d]
                    r0 = max(set(rots), key=rots.count) if rots else 0
                    data = [d if 'rotation' in d else dict(d, rotation=r0) for d in data]
                if data and 'rotation' in data[0]:
                    for b in data:
                        m = SET_RE.search(str(b.get('label', '')))
                        if not m:
                            continue
                        name = 'SET ' + str(int(m.group(1)))
                        try:
                            o = json.load(open(os.path.join(ocr_dir, folder, fn + '.json')))
                            sq = motif_square(img, b) if b.get('motyw') else \
                                probka_square(img, b, o) if KADR == 'probka' else band_square(img, b, o)
                        except (KeyError, ValueError, TypeError):
                            sq = None
                        if sq is None and fallback_dir:
                            sq = fallback_square(img, os.path.join(fallback_dir, folder, fn + '.json'), name,
                                                 int(b.get('rotation', 0)))
                            b = dict(b, box_2d=[0, 0, 1, 1])  # mała waga: pełne ujęcie z innego zdjęcia wygrywa
                        if sq is None:
                            continue
                        y0, x0, y1, x1 = [float(v) for v in b['box_2d']]
                        score = (y1 - y0) * (x1 - x0)
                        H, W = img.shape[:2]
                        ocr = json.load(open(os.path.join(ocr_dir, folder, fn + '.json')))
                        if KADR != 'probka' and any(it['x'] < x1 * W / 1000 and it['x'] + it['w'] > x0 * W / 1000 and
                               it['y'] < y1 * H / 1000 and it['y'] + it['h'] > y0 * H / 1000 for it in ocr['items']):
                            score *= 0.2  # napis w kadrze: weź inne zdjęcie tej próbki, jeśli jest
                            flagged.add((folder, name, fn))
                        if name not in best or score > best[name][3]:
                            best[name] = (fn, sq, int(b.get('rotation', 0)), score)
                    continue
                for name, cx, cy, r in from_boxes(img, data):
                    if name not in best or r > best[name][3]:
                        best[name] = (fn, cx, cy, r)
                continue
            ocr = json.load(open(os.path.join(ocr_dir, folder, fn + '.json')))
            labs = labels(ocr)
            if not labs:
                continue
            h, w = img.shape[:2]
            mask = sample_mask(img)
            ex = tag_mask(img, ocr, (h, w))
            n, comp = cv2.connectedComponents(mask)
            for name, kind, (x, y, bw, bh) in labs:
                c = (x + bw / 2, y + bh / 2)
                # próbka: komponent maski najbliżej etykiety (metka wisi na próbce / numer obok motka)
                ys, xs = np.nonzero(mask[max(0, y - 400):y + bh + 400, max(0, x - 400):x + bw + 400])
                if len(xs) == 0:
                    continue
                ox, oy = max(0, x - 400), max(0, y - 400)
                d = (xs + ox - c[0]) ** 2 + (ys + oy - c[1]) ** 2
                j = int(np.argmin(d))
                lab_id = comp[ys[j] + oy, xs[j] + ox]
                cm = (comp == lab_id).astype(np.uint8)
                bx, by, bw2, bh2 = cv2.boundingRect(cm)
                max_r = 0.32 * min(bw2, bh2) if kind == 'set' else 0.5 * min(bw2, bh2)
                cx, cy, r = best_circle(cm, ex, c, max_r)
                if r < 30:
                    continue
                if name not in best or r > best[name][3]:
                    best[name] = (fn, cx, cy, r)
        for name, v in (fixes.get(folder) or {}).items():
            if v is None:
                best.pop(name, None)
            else:
                best[name] = tuple(v)
        # karta modelu: zostają tylko etykiety „SET <nr>” (OCR/Gemini czasem czyta „SETX”, „257A”)
        if sum(n.startswith('SET ') for n in best) > len(best) / 2:
            best = {n: v for n, v in best.items() if re.fullmatch(r'SET \d+', n)}
        if KADR == 'probka':
            orient_cuffs(best)
            # ręczne poprawki kierunku (obroty.json: {karta: {"SET n" | "*": stopnie w prawo}}) — tam, gdzie
            # automat się myli: jednokolorowe prążki z cieniem, karta z ściągaczem odwróconym na całym zdjęciu
            fix, fix2 = turns.get(folder, {}), turns2.get(folder, {})
            for name, (fn, sq, r, score) in list(best.items()):
                k = (fix.get(name, fix.get('*', 0)) + fix2.get(name, 0)) // 90 % 4
                if k and isinstance(sq, np.ndarray):
                    best[name] = (fn, np.ascontiguousarray(np.rot90(sq, -k)), r, score)
        os.makedirs(os.path.join(out, folder), exist_ok=True)
        manifest[folder] = {}
        for name, (fn, a, b2, r) in sorted(best.items(), key=lambda kv: natural(kv[0])):
            if isinstance(a, np.ndarray):  # tryb set: gotowy kwadrat
                sq, meta = a, [fn, b2]
            else:
                sq, meta = crop(cv2.imread(os.path.join(fdir, fn)), a, b2, r), [fn, a, b2, round(r)]
            cv2.imwrite(os.path.join(out, folder, name + '.jpg'), sq, [cv2.IMWRITE_JPEG_QUALITY, 88])
            if (folder, name, fn) in flagged:
                uwagi.add(f'{folder} | {name} | napis w kadrze ({fn})')
            manifest[folder][name] = meta
        print(f'{len(best):3d}  {folder}')
    json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
    if uwagi:
        open(os.path.join(out, 'uwagi.txt'), 'w').write('\n'.join(sorted(uwagi)) + '\n')
        print(len(uwagi), 'kółek z napisem w kadrze → uwagi.txt')


def orient_cuffs(best, debug=False):
    """Ściągacz na dół: głos wszystkich próbek z karty (a przy słabym głosie — z tego samego zdjęcia)
    o tym, po której stronie zdjęcia leżą ściągacze; kółka z pasami pionowo na zdjęciu głosują osobno (oś lewo–prawo)."""
    votes = {}
    for name, (fn, sq, _, _) in best.items():
        if isinstance(sq, np.ndarray) and id(sq) in CUFF:
            rot, ev = CUFF[id(sq)]
            for key in ((fn, rot), ('*', rot)):
                votes[key] = votes.get(key, 0) + float(np.clip(ev, -0.3, 0.3))
    for name, (fn, sq, r, score) in list(best.items()):
        if isinstance(sq, np.ndarray) and id(sq) in CUFF:
            rot, _ = CUFF[id(sq)]
            v = votes[('*', rot)]
            if abs(v) < 0.1:
                v = votes[(fn, rot)]
            if v < 0:
                best[name] = (fn, np.ascontiguousarray(np.rot90(sq, 2)), r, score)


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


if __name__ == '__main__':
    main(*sys.argv[1:6])
