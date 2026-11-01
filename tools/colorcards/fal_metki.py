"""Poprawka miejsc po metkach przez Qwen-Image-Edit-2511 na fal.ai (22.10.2026, Kamil: „trzeba zrobić to przez stronę”).
LaMa (usun_metki.py + druga_runda.py) zostawił na wzorach rozmyte łaty. Lokalny Qwen był dobry, ale 1 MP to ~25 min na
metkę na Macu, a 0,5 MP przesuwał kadr — tu ten sam model w chmurze, 1 MP, ~0,03 $ za metkę.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/fal_metki.py ORYGINAŁY BEZ_METEK WYJŚCIE
        [--tylko=IMG_4450,…] [--limit=N] [--watki=4] [--wszystkie] [--plan]

ORYGINAŁY  rozpakowany zip COLORCARDS (zdjęcia z metkami), BEZ_METEK = wynik LaMa (colorcards-bez-metek-2).
Miejsca do poprawy = różnica ORYGINAŁ (obrócony jak wynik) ↔ BEZ_METEK, więc obie rundy LaMa i ręczne poprawki są ujęte.
Dla każdej łaty: wycinek ORYGINAŁU (z metką, ~2,2× łaty, skalowany do ~1 MP) → Qwen usuwa metkę → wynik dopasowany do
wycinka (ECC, poza łatą; Qwen potrafi lekko przesunąć kadr) → wklejony w BEZ_METEK z miękką krawędzią.
Domyślnie tylko łaty na wzorze (otoczenie niejednolite); --wszystkie = każda łata. --plan = policz łaty i koszt, bez API.
--cofnij=PLIK = lista łat (<karta>__<plik>__<n>, jak w _przeglad) zostawionych w wersji LaMa.
--resztki = dodatkowo szuka na BEZ_METEK metek i sznurków, których LaMa w ogóle nie ruszył (OWLv2 jak druga_runda.py;
ramka liczy się, gdy wokół niej jest dzianina, nie stół). Wklejany jest obszar łaty + to, co Qwen usunął jasnego
(biały sznurek) w kawałkach stykających się z łatą. Wyniki Qwen zapisywane w _cache — ponowne uruchomienie nie płaci drugi raz.
WYJŚCIE = komplet zdjęć (bez łat na wzorze kopiowane), _przeglad/<karta>__<plik>__<n>.jpg = przed | LaMa | Qwen,
_log.json = co zrobione (ponowne uruchomienie pomija zrobione; słabe dopasowanie → „sprawdz”).
Klucz: ~/.config/achti/fal_key (fal.ai → Dashboard → API Keys). Płatność wpisuje Kamil.
"""
import base64
import certifi
import json
import os
import shutil
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from usun_metki import pion  # noqa: E402

KEY = os.path.expanduser('~/.config/achti/fal_key')
ENDPOINT = 'https://queue.fal.run/fal-ai/qwen-image-edit-2511'
PROMPT = ('Remove the paper hang tag, its string and any sticker or label from the knitted fabric. Reconstruct the knit '
          'underneath so it continues the surrounding stitches, pattern, colours and lighting exactly. Change nothing else.')
PRICE_MP = 0.03
_lock = threading.Lock()
# Python z python.org nie ma certyfikatów systemowych — bez tego każde zapytanie kończy się CERTIFICATE_VERIFY_FAILED
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(
    context=__import__('ssl').create_default_context(cafile=certifi.where()))))


def natural_key(s):
    import re
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def patches(orig, clean):
    """Łaty LaMa = piksele, które różnią się od oryginału ponad szum JPEG → ramki (x0,y0,x1,y1)."""
    d = cv2.GaussianBlur(cv2.absdiff(orig, clean).max(2), (0, 0), 3)
    m = (d > 12).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.dilate(m, np.ones((41, 41), np.uint8))  # metka + sznurek obok = jedna łata
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 1500:
            continue
        out.append((x, y, x + w, y + h, (lb == i)))
    return out


def crop_box(b, H, W):
    x0, y0, x1, y1 = b[:4]
    bw, bh = x1 - x0, y1 - y0
    side = min(int(max(bw, bh) * 2.2), H, W)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    X0, Y0 = max(0, min(cx - side // 2, W - side)), max(0, min(cy - side // 2, H - side))
    return X0, Y0, X0 + side, Y0 + side


def patterned(img, region, hole):
    """Otoczenie łaty niejednolite (wzór, pasy) — tam LaMa rozmywa. Na gładkiej dzianinie LaMa wystarcza."""
    X0, Y0, X1, Y1 = region
    sub = cv2.cvtColor(img[Y0:Y1, X0:X1], cv2.COLOR_BGR2LAB).astype(np.float32)
    ring = (cv2.dilate(hole, np.ones((61, 61), np.uint8)) > 0) & ~(hole > 0)
    if ring.sum() < 200:
        return True
    px = sub[ring]
    return px[:, 0].std() > 18 or np.hypot(px[:, 1] - px[:, 1].mean(), px[:, 2] - px[:, 2].mean()).mean() > 8


def fal_edit(crop, key, seed=7):
    h, w = crop.shape[:2]
    s = np.sqrt(1024 * 1024 / (h * w))
    tw, th = int(round(w * s / 16)) * 16, int(round(h * s / 16)) * 16
    ok, jpg = cv2.imencode('.jpg', cv2.resize(crop, (tw, th), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC),
                           [cv2.IMWRITE_JPEG_QUALITY, 95])
    body = {'prompt': PROMPT, 'image_urls': ['data:image/jpeg;base64,' + base64.b64encode(jpg).decode()],
            'image_size': {'width': tw, 'height': th}, 'seed': seed, 'output_format': 'png', 'num_images': 1}
    hdr = {'Authorization': 'Key ' + key, 'Content-Type': 'application/json'}
    r = json.load(urllib.request.urlopen(urllib.request.Request(ENDPOINT, json.dumps(body).encode(), hdr), timeout=120))
    t0 = time.time()
    while time.time() - t0 < 900:
        st = json.load(urllib.request.urlopen(urllib.request.Request(r['status_url'], headers=hdr), timeout=60))
        if st.get('status') == 'COMPLETED':
            break
        time.sleep(3)
    else:
        raise TimeoutError(r.get('request_id'))
    res = json.load(urllib.request.urlopen(urllib.request.Request(r['response_url'], headers=hdr), timeout=60))
    url = res['images'][0]['url']
    data = urllib.request.urlopen(url, timeout=120).read() if url.startswith('http') else base64.b64decode(url.split(',', 1)[1])
    out = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA if out.shape[1] > w else cv2.INTER_CUBIC), tw * th / 1e6


def align(res, ref, hole):
    """Dopasowanie wyniku Qwen do wycinka oryginału poza łatą (ECC, przesunięcie + skala + obrót). Zwraca (obraz, korelacja)."""
    s = 512 / max(ref.shape[:2])
    a = cv2.cvtColor(cv2.resize(ref, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY).astype(np.float32)
    b = cv2.cvtColor(cv2.resize(res, None, fx=s, fy=s), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = (cv2.resize((hole == 0).astype(np.uint8), (a.shape[1], a.shape[0]), interpolation=cv2.INTER_NEAREST))
    m = cv2.erode(m, np.ones((9, 9), np.uint8))
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        cc, warp = cv2.findTransformECC(a, b, warp, cv2.MOTION_AFFINE,
                                        (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), m, 5)
    except cv2.error:
        return res, 0.0
    warp[:, 2] /= s
    out = cv2.warpAffine(res, warp, (ref.shape[1], ref.shape[0]), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                         borderMode=cv2.BORDER_REFLECT)
    return out, float(cc)


def leftovers(clean, have):
    """Metki/sznurki pominięte przez LaMa: ramki OWLv2 na dzianinie, nie pokrywające się z łatami LaMa."""
    import usun_metki as um
    from latanie import background
    if not getattr(um, '_resztki', False):
        um.QUERIES = um.QUERIES + ['a white string or thread loop attached to a tag', 'a paper sticker label with text',
                                   'a clear plastic tag fastener pin']
        um._resztki = True
    bg = background(clean)
    H, W = clean.shape[:2]
    out = []
    for b in um.detect(cv2.cvtColor(clean, cv2.COLOR_BGR2RGB), 0.2):
        x0, y0, x1, y1 = [int(v) for v in b]
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        p = max(20, (x1 - x0 + y1 - y0) // 6)
        ring = bg[max(0, y0 - p):y1 + p, max(0, x0 - p):x1 + p].copy()
        ring[y0 - max(0, y0 - p):y1 - max(0, y0 - p), x0 - max(0, x0 - p):x1 - max(0, x0 - p)] = False
        if ring.mean() > 0.35:  # wokół stół — nitka na podkładce, kartonik ZESTAW
            continue
        if any(not (x1 < h[0] or x0 > h[2] or y1 < h[1] or y0 > h[3]) for h in have):
            continue
        m = np.zeros((H, W), bool)
        m[y0:y1, x0:x1] = True
        out.append((x0, y0, x1, y1, m))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, clean_dir, dst = args
    only = opts['tylko'].split(',') if opts.get('tylko') else None
    plan = 'plan' in opts
    key = None if plan else open(KEY).read().strip()
    logp = os.path.join(dst, '_log.json')
    log = json.load(open(logp)) if os.path.exists(logp) else {}
    os.makedirs(os.path.join(dst, '_przeglad'), exist_ok=True)
    jobs = []
    for root, _, files in os.walk(src, followlinks=True):
        for fn in sorted(files, key=natural_key):
            if not fn.lower().endswith(('.jpg', '.jpeg')):
                continue
            rel = os.path.relpath(os.path.join(root, fn), src)
            relj = os.path.splitext(rel)[0] + '.jpg'
            cp, out = os.path.join(clean_dir, relj), os.path.join(dst, relj)
            if not os.path.exists(cp):
                continue
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if only and not any(o in rel for o in only):
                if not os.path.exists(out):
                    shutil.copy2(cp, out)
                continue
            jobs.append((rel, os.path.join(root, fn), cp, out))
    total_mp, todo = 0.0, []
    for rel, op, cp, out in jobs:
        orig, clean = pion(cv2.imread(op, cv2.IMREAD_COLOR), rel), cv2.imread(cp)
        if orig.shape != clean.shape:
            print('inny rozmiar, pomijam', rel, flush=True)
            continue
        H, W = clean.shape[:2]
        ps = []
        pp = patches(orig, clean)
        extra = leftovers(clean, [p[:4] for p in pp]) if 'resztki' in opts else []
        if extra:
            print('  resztki', rel, len(extra), flush=True)
        for i, p in enumerate(pp + extra):
            reg = crop_box(p, H, W)
            hole = p[4][reg[1]:reg[3], reg[0]:reg[2]].astype(np.uint8)
            if i >= len(pp) or 'wszystkie' in opts or patterned(orig, reg, hole):
                ps.append((i, p[:4], reg))
        if not ps:
            if not os.path.exists(out):
                shutil.copy2(cp, out)
            continue
        todo.append((rel, op, cp, out, ps))
        total_mp += len(ps) * 1.05
    n = sum(len(t[4]) for t in todo)
    print(f'zdjęć z łatami do poprawy: {len(todo)}, łat: {n}, koszt ≈ {total_mp * PRICE_MP:.2f} $', flush=True)
    if plan:
        return
    if opts.get('limit'):
        todo = todo[:int(opts['limit'])]

    skip = set(open(opts['cofnij']).read().splitlines()) if opts.get('cofnij') else set()
    # --ponow=PLIK: łaty odrzucone w przeglądzie — nowe losowanie (--seed), osobny plik w _cache, reszta zdjęcia z cache
    redo = set(open(opts['ponow']).read().splitlines()) - {''} if opts.get('ponow') else set()
    seed = int(opts.get('seed') or 7)

    def work(t):
        rel, op, cp, out, ps = t
        stem = rel.replace('/', '__')[:-4]
        if log.get(rel, {}).get('ok') and not any(k.startswith(stem + '__') for k in redo):
            return
        orig, img = pion(cv2.imread(op, cv2.IMREAD_COLOR), rel), cv2.imread(cp)
        lama = img.copy()
        info = []
        for i, b, (X0, Y0, X1, Y1) in ps:
            crop = orig[Y0:Y1, X0:X1]
            hole = np.zeros(crop.shape[:2], np.uint8)
            mx, my = int(0.3 * (b[2] - b[0])), int(0.3 * (b[3] - b[1]))  # ramka łaty + 30 % — bez resztek brzegu metki
            hole[max(0, b[1] - my - Y0):b[3] + my - Y0, max(0, b[0] - mx - X0):b[2] + mx - X0] = 1
            if rel.replace('/', '__')[:-4] + f'__{i}' in skip:  # przejrzane: Qwen gorszy niż LaMa
                continue
            key_ = stem + f'__{i}'
            cache = os.path.join(dst, '_cache', key_ + (f'__s{seed}' if key_ in redo else '') + '.png')
            for attempt in range(3):
                if os.path.exists(cache):
                    res, mp = cv2.imread(cache), 0.0
                    break
                try:
                    res, mp = fal_edit(crop, key, seed if key_ in redo else 7)
                    os.makedirs(os.path.dirname(cache), exist_ok=True)
                    cv2.imwrite(cache, res)
                    break
                except Exception as e:  # noqa: BLE001 — sieć/kolejka: ponów
                    msg = e.read()[:300] if hasattr(e, 'read') else e
                    print('  błąd', rel, i, msg, flush=True)
                    time.sleep(10)
            else:
                info.append({'n': i, 'blad': True})
                continue
            res, cc = align(res, crop, hole)
            # biały sznurek poza ramką: to, co Qwen rozjaśnione usunął (oryginał wyraźnie jaśniejszy), w kawałkach stykających się z łatą
            go, gr = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.int16), cv2.cvtColor(res, cv2.COLOR_BGR2GRAY).astype(np.int16)
            gone = cv2.dilate((((go - gr) > 35) & (go > 150)).astype(np.uint8), np.ones((9, 9), np.uint8))
            n_, lb_ = cv2.connectedComponents(gone | hole)
            keep = np.unique(lb_[hole > 0])
            hole = np.isin(lb_, keep[keep > 0]).astype(np.uint8)
            a = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), max(4, 0.03 * crop.shape[0]))[..., None]
            img[Y0:Y1, X0:X1] = (img[Y0:Y1, X0:X1] * (1 - a) + res * a).astype(np.uint8)
            info.append({'n': i, 'cc': round(cc, 3), 'mp': round(mp, 2), 'sprawdz': cc < 0.85})
            row = [cv2.resize(x, (600, 600)) for x in (crop, lama[Y0:Y1, X0:X1], img[Y0:Y1, X0:X1])]
            cv2.imwrite(os.path.join(dst, '_przeglad', rel.replace('/', '__')[:-4] + f'__{i}.jpg'), np.hstack(row),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])
        cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        with _lock:
            log[rel] = {'ok': not any(x.get('blad') for x in info), 'laty': info}
            json.dump(log, open(logp, 'w'), indent=1, ensure_ascii=False)
            done = sum(1 for v in log.values() if v.get('ok'))
        print(f'{done}/{len(todo)}', rel, [x.get('cc') for x in info], flush=True)

    with ThreadPoolExecutor(int(opts.get('watki') or 4)) as ex:
        list(ex.map(work, todo))
    mp = sum(x.get('mp', 0) for v in log.values() for x in v['laty'])
    print(f'gotowe, {mp:.1f} MP ≈ {mp * PRICE_MP:.2f} $', flush=True)


if __name__ == '__main__':
    main()
