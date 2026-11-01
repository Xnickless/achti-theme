"""Łatanie miejsca po metce prawdziwą dzianiną z tej samej próbki (21.10.2026, Kamil: „ciemniejsze pole od metki —
podmień materiał w to miejsce”). Image quilting (Efros–Freeman): dziurę wypełniamy w kolejności rastrowej blokami
wyciętymi z innych miejsc TEJ SAMEJ próbki; każdy blok to miejsce, którego zakładka najlepiej pasuje do tego, co już
wokół jest (prawdziwa dzianina albo wcześniej wstawione bloki). Wynik = oryginalne oczka, bez rozmycia i bez cienia.

Używane przez kolka_cale.py (--latanie). Funkcja: quilt(img, hole, region) → img z wypełnioną dziurą.
Dopasowanie liczone szybko przez splot (filter2D/DFT): SSD z maską = Σm·I² − 2·Σ(m·T)·I + Σm·T².
"""
import cv2
import numpy as np


def background(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    std = np.sqrt(np.maximum(cv2.blur(gray * gray, (15, 15)) - cv2.blur(gray, (15, 15)) ** 2, 0))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bgc = np.median(np.concatenate([img[:20].reshape(-1, 3), img[-20:].reshape(-1, 3)]), 0)
    bg = (np.abs(img.astype(np.int16) - bgc).max(2) < 28) & (std < 6) & (hsv[..., 1] < 40)
    return cv2.morphologyEx(bg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) > 0


def _corr(a, k):
    """Korelacja (nie splot) obrazu a z jądrem k, wynik w lewym-górnym rogu okna (jak matchTemplate)."""
    r = cv2.filter2D(a, -1, k, anchor=(0, 0), borderType=cv2.BORDER_CONSTANT)
    return r[:a.shape[0] - k.shape[0] + 1, :a.shape[1] - k.shape[1] + 1]


def quilt(img, hole, region, scale=0.5, seed=0, allowed=None):
    """img BGR uint8, hole bool (gdzie była metka), region (x0,y0,x1,y1) = ramka próbki, allowed = maska samej próbki
    (SAM) — ramka zahacza o sąsiednie próbki, a stamtąd brać nie wolno."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = [int(v) for v in region]
    H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    sub = img[y0:y1, x0:x1]
    hs = hole[y0:y1, x0:x1]
    if not hs.any():
        return img
    k = max(15, int(0.35 * min(np.ptp(np.where(hs)[0]), np.ptp(np.where(hs)[1]))))
    bad = cv2.dilate(hs.astype(np.uint8), np.ones((k, k), np.uint8)) > 0  # metka + sznurek i cień obok niej
    bad |= background(sub)  # źródło nie może zawierać metki, sznurka ani tła
    # ani brzegu próbki (lamówka, nitka obszycia) — tylko środek próbki
    e = int(0.08 * min(sub.shape[:2]))
    knit = ~background(sub) if allowed is None else allowed[y0:y1, x0:x1].astype(bool)
    knit = cv2.erode(knit.astype(np.uint8), np.ones((2 * e + 1, 2 * e + 1), np.uint8)) > 0
    bad |= ~knit
    sm = cv2.resize(sub, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA).astype(np.float32)
    hsm = cv2.resize(hs.astype(np.uint8), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    hsm = cv2.dilate(hsm.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0  # zapas na zaokrąglenia skali
    badm = cv2.resize(bad.astype(np.uint8), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    badm |= hsm
    ys, xs = np.where(hsm)
    hy0, hy1, hx0, hx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    B = int(np.clip(min(hy1 - hy0, hx1 - hx0) / 3, 16, 60))  # blok ~1/3 dziury, w skali roboczej
    ov = max(4, B // 5)
    out = sm.copy()
    known = ~hsm
    I2 = (sm ** 2).sum(2)
    # okna źródłowe, które w całości leżą na dzianinie (bez metki i tła)
    badc = cv2.integral(badm.astype(np.uint8))
    valid = (badc[B:, B:] - badc[:-B, B:] - badc[B:, :-B] + badc[:-B, :-B]) == 0
    if not valid.any():
        return img
    blocks = []
    for by in range(max(0, hy0 - ov), hy1, B - ov):
        for bx in range(max(0, hx0 - ov), hx1, B - ov):
            by_, bx_ = min(by, sm.shape[0] - B), min(bx, sm.shape[1] - B)
            win = (slice(by_, by_ + B), slice(bx_, bx_ + B))
            need = ~known[win]
            if not need.any():
                continue
            m = known[win].astype(np.float32)
            T = out[win]
            if m.sum() < 1:  # brak zakładki — losowe ważne okno
                vy, vx = np.where(valid)
                k = rng.integers(len(vy))
                sy, sx = vy[k], vx[k]
            else:
                cost = _corr(I2, m) - 2 * sum(_corr(sm[..., c], m * T[..., c]) for c in range(3)) + (m[..., None] * T ** 2).sum()
                cost = np.where(valid, cost, np.inf)
                flat = np.argsort(cost, axis=None)[:3]  # trochę losowości między 3 najlepszymi — bez powtarzania wzoru
                sy, sx = np.unravel_index(flat[rng.integers(len(flat))], cost.shape)
            out[win][need] = sm[sy:sy + B, sx:sx + B][need]
            known[win] |= need
            blocks.append((by_, bx_, sy, sx))
    # pełna rozdzielczość: te same bloki kopiowane z oryginału (ostre oczka), w tej samej kolejności, tylko na dziurę
    res = img.copy()
    full = res[y0:y1, x0:x1]
    filled = ~hs
    hole_d = cv2.dilate(hs.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0  # cień tuż przy brzegu metki też podmieniamy
    filled &= ~hole_d
    Bf = int(round(B / scale))
    for by_, bx_, sy, sx in blocks:
        ty, tx, fy, fx = int(by_ / scale), int(bx_ / scale), int(sy / scale), int(sx / scale)
        h = min(Bf + 4, full.shape[0] - ty, full.shape[0] - fy)  # +4 px: bez szczelin między blokami
        w = min(Bf + 4, full.shape[1] - tx, full.shape[1] - fx)
        if h <= 0 or w <= 0:
            continue
        need = ~filled[ty:ty + h, tx:tx + w] & hole_d[ty:ty + h, tx:tx + w]
        full[ty:ty + h, tx:tx + w][need] = sub[fy:fy + h, fx:fx + w][need]
        filled[ty:ty + h, tx:tx + w] |= need
    # ton łaty do otoczenia (niskie częstotliwości, jak wyrownaj_laty) zamiast Poissona — Poisson ciągnął cień z brzegu
    lab_f = cv2.cvtColor(full, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_o = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2LAB).astype(np.float32)
    ring = (cv2.dilate(hole_d.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0) & ~hole_d & knit
    if ring.sum() > 100:
        # pole korekty zamiast jednej liczby: ton otoczenia i łaty rozmyte na skali ~1/4 łaty (znormalizowane)
        sg = max(10.0, 0.25 * np.sqrt(hole_d.sum()))
        def nb(x, w):
            k = cv2.GaussianBlur(w.astype(np.float32), (0, 0), sg)[..., None]
            return cv2.GaussianBlur(x * w[..., None], (0, 0), sg) / np.maximum(k, 1e-3)
        field = np.clip(nb(lab_o, ring) - nb(lab_f, hole_d), [-25, -8, -8], [25, 8, 8])
        lab_f[hole_d] += field[hole_d]
        full = cv2.cvtColor(np.clip(lab_f, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    a = cv2.GaussianBlur(hole_d.astype(np.float32), (0, 0), 6)[..., None]
    res[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - a) + full * a).astype(np.uint8)
    return res
