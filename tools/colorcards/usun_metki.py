"""Usuwanie metek z próbek dzianiny (21.10.2026, nowy koncept Kamila): na każdym zdjęciu do dolnej partii dzianiny
przypięta jest biała prostokątna metka z napisem i sznurkiem — wykrywamy ją i zamalowujemy splotem (inpainting).
Wszystko lokalnie, bez kredytów.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/usun_metki.py WEJŚCIE WYJŚCIE [--maski] [--tylko=IMG_4450.JPG,…]
        [--prog=0.25] [--metoda=lama|cv2] [--force]

WEJŚCIE  folder ze zdjęciami (także podfoldery kart, np. rozpakowany zip COLORCARDS) — struktura odtwarzana w WYJŚCIU,
         pliki w pełnej rozdzielczości (JPEG q95), wszystkie w pionie (poziome obrócone o 90° w prawo),
         jedynie akryl (ACRYLIC…) w poziomie.
Kroki:
 1. OWLv2 (google/owlv2-base-patch16-ensemble) szuka po opisie „white paper tag…” — ramki metek; odróżnia papier od
    białej dzianiny, czego progi jasności nie umiały (pierwsza wersja łapała 30–60 % zdjęcia). --prog = próg pewności.
 2. SAM 2.1 (facebook/sam2.1-hiera-large) robi z ramki dokładną maskę metki; maska poszerzona o cień i sznurek.
 3. LaMa (ONNX, ~/Claude/achti-foto/modele/lama_fp32.onnx, wejście 512×512 — model do powtarzalnych faktur): wycinek
    wokół metki skalowany do 512, zamalowany i wklejony tylko w obszarze maski z miękką krawędzią; reszta zdjęcia
    bez zmian. --metoda=cv2 = cv2.inpaint (Telea), rozmazuje splot — tylko do porównania.
--maski  podgląd wykrytej maski obok wyniku (<nazwa>_maska.jpg). Zdjęcia bez metki → WYJŚCIE/_bez_metki.txt.
Modele (~1,5 GB) pobierają się same z Hugging Face przy pierwszym uruchomieniu.
"""
import os
import sys

import cv2
import numpy as np

MASKS = os.path.expanduser('~/Claude/achti-foto/maski-metek')
BIGLAMA = os.path.expanduser('~/Claude/achti-foto/modele/big-lama.pt')
LAMA = os.path.expanduser('~/Claude/achti-foto/modele/lama_fp32.onnx')
OWL = 'google/owlv2-base-patch16-ensemble'
SAM = 'facebook/sam2.1-hiera-large'
QUERIES = ['a white paper price tag label with printed text', 'a rectangular white cardboard hang tag',
           'a brown kraft paper hang tag with a logo']  # 2344, 1820: metka kraft z białą naklejką
EXT = ('.jpg', '.jpeg', '.png')
_m = {}


def models():
    if not _m:
        import onnxruntime as ort
        from transformers import Owlv2ForObjectDetection, Owlv2Processor, Sam2Model, Sam2Processor
        _m['owl'] = (Owlv2Processor.from_pretrained(OWL), Owlv2ForObjectDetection.from_pretrained(OWL).eval())
        _m['sam'] = (Sam2Processor.from_pretrained(SAM), Sam2Model.from_pretrained(SAM).eval())
        _m['lama'] = ort.InferenceSession(LAMA, providers=['CPUExecutionProvider'])
    return _m


def detect(rgb, thr):
    """Ramki metek [x0,y0,x1,y1] w pikselach oryginału."""
    import torch
    from PIL import Image
    proc, model = models()['owl']
    H, W = rgb.shape[:2]
    s = 1600 / max(H, W)  # OWLv2 i tak skaluje do 960 — mniejszy obraz = szybciej, ta sama dokładność
    im = Image.fromarray(cv2.resize(rgb, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    inp = proc(text=[QUERIES], images=im, return_tensors='pt')
    with torch.no_grad():
        out = model(**inp)
    side = max(im.size)  # OWLv2 dopełnia obraz do kwadratu
    r = proc.post_process_grounded_object_detection(out, threshold=thr, target_sizes=torch.tensor([[side, side]]))[0]
    boxes, scores = r['boxes'].numpy() / s, r['scores'].numpy()
    keep = []
    for i in np.argsort(-scores):  # NMS między obiema frazami
        b = boxes[i]
        bw, bh = b[2] - b[0], b[3] - b[1]
        if bw * bh > 0.06 * H * W or bw * bh < 0.0015 * H * W:  # cała próbka albo drobiazg
            continue
        hit = next((k for k, kb in enumerate(keep) if iou(b, kb) > 0.1 or inside(b, kb) or inside(kb, b)), None)
        if hit is None:
            keep.append(b.copy())
        else:  # naklejka na metce kraft = jedna metka → suma ramek
            kb = keep[hit]
            keep[hit] = np.array([min(kb[0], b[0]), min(kb[1], b[1]), max(kb[2], b[2]), max(kb[3], b[3])])
    return [b.tolist() for b in keep]


def inside(a, b, tol=0.8):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0) > tol * (a[2] - a[0]) * (a[3] - a[1])


def iou(a, b):
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x1 - x0) * max(0, y1 - y0)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-6)


def segment(rgb, boxes):
    """Maski SAM 2 dla ramek → jedna maska uint8 0/255 (z cieniem i sznurkiem)."""
    import torch
    from PIL import Image
    proc, model = models()['sam']
    inp = proc(images=Image.fromarray(rgb), input_boxes=[boxes], return_tensors='pt')
    with torch.no_grad():
        out = model(**inp, multimask_output=False)
    masks = proc.post_process_masks(out.pred_masks, inp['original_sizes'])[0][:, 0].numpy()
    H, W = rgb.shape[:2]
    mask = np.zeros((H, W), np.uint8)
    for b, m in zip(boxes, masks):
        m = m.astype(np.uint8)
        x0, y0, x1, y1 = [int(v) for v in b]
        if m[y0:y1, x0:x1].sum() < 0.3 * (x1 - x0) * (y1 - y0):  # SAM nie objął metki — bierzemy ramkę
            m[max(y0, 0):y1, max(x0, 0):x1] = 1
        k = max(7, int(0.12 * min(x1 - x0, y1 - y0)))  # cień, postrzępiony brzeg i nasada sznurka
        mask |= cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return mask * 255


def inpaint_biglama(img, mask, max_side=1600):
    """big-lama (TorchScript z IOPaint, ~/Claude/achti-foto/modele/big-lama.pt) w rozdzielczości bliskiej pełnej —
    wersja ONNX liczy w 512 px, więc przy zdjęciach 4–6 tys. px łata wychodziła 3–4× rozmyta (smugi zamiast oczek)."""
    import torch
    if 'big' not in _m:
        _m['big'] = torch.jit.load(BIGLAMA, map_location='cpu').eval()
    net = _m['big']
    out = img.copy()
    H, W = img.shape[:2]
    n, lb, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8))
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        side = min(int(max(bw, bh) * 2.0), H, W)
        cx, cy = x + bw // 2, y + bh // 2
        x0, y0 = max(0, min(cx - side // 2, W - side)), max(0, min(cy - side // 2, H - side))
        crop, m = out[y0:y0 + side, x0:x0 + side], (lb[y0:y0 + side, x0:x0 + side] == i).astype(np.uint8)
        f = min(1.0, max_side / side)
        s8 = int(round(side * f / 8)) * 8
        ci = cv2.resize(crop, (s8, s8), interpolation=cv2.INTER_AREA)
        mi = cv2.dilate(cv2.resize(m, (s8, s8), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        t = torch.from_numpy(cv2.cvtColor(ci, cv2.COLOR_BGR2RGB)).permute(2, 0, 1)[None].float() / 255
        tm = torch.from_numpy(mi)[None, None].float()
        with torch.no_grad():
            r = net(t, tm)[0].permute(1, 2, 0).numpy()
        r = cv2.cvtColor(np.clip(r * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        r = cv2.resize(r, (side, side), interpolation=cv2.INTER_CUBIC) if s8 != side else r
        a = cv2.GaussianBlur(cv2.dilate(m, np.ones((9, 9), np.uint8)).astype(np.float32), (15, 15), 0)[..., None]
        out[y0:y0 + side, x0:x0 + side] = (crop * (1 - a) + r * a).astype(np.uint8)
    return out


def inpaint_lama(img, mask):
    sess = models()['lama']
    out = img.copy()
    H, W = img.shape[:2]
    n, lb, st, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8))
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        side = min(int(max(bw, bh) * 2.2), H, W)  # kontekst splotu wokół metki
        cx, cy = x + bw // 2, y + bh // 2
        x0, y0 = max(0, min(cx - side // 2, W - side)), max(0, min(cy - side // 2, H - side))
        x1, y1 = x0 + side, y0 + side
        crop, m = out[y0:y1, x0:x1], (lb[y0:y1, x0:x1] == i).astype(np.uint8)
        ci = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_AREA)
        mi = cv2.dilate(cv2.resize(m, (512, 512), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        x_in = cv2.cvtColor(ci, cv2.COLOR_BGR2RGB).transpose(2, 0, 1)[None].astype(np.float32) / 255
        res = sess.run(None, {'image': x_in, 'mask': mi[None, None].astype(np.float32)})[0][0].transpose(1, 2, 0)
        res = np.clip(res * 255 if res.max() <= 1.5 else res, 0, 255).astype(np.uint8)
        res = cv2.resize(cv2.cvtColor(res, cv2.COLOR_RGB2BGR), (side, side), interpolation=cv2.INTER_CUBIC)
        a = cv2.GaussianBlur(cv2.dilate(m, np.ones((9, 9), np.uint8)).astype(np.float32), (15, 15), 0)[..., None]
        out[y0:y1, x0:x1] = (crop * (1 - a) + res * a).astype(np.uint8)
    return out


def inpaint_shift(img, mask, verbose=False):
    """Dzianina = wzór powtarzany wzdłuż pasa, więc miejsce po metce wypełniamy PRAWDZIWYM kawałkiem tej samej próbki
    przesuniętym wzdłuż pasa (poziomo albo pionowo) o tyle, ile najlepiej pasuje na pierścieniu wokół metki, i wtapiamy
    go Poissonem (cv2.seamlessClone — wyrównuje też ton/cień). Gdy nic nie pasuje (koniec próbki, unikalny motyw),
    zostaje LaMa. Zwraca (obraz, lista metod na łatę)."""
    out = img.copy()
    H, W = img.shape[:2]
    allm = (mask > 0).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(allm)
    lama_mask = np.zeros_like(allm)
    used = []
    g = cv2.GaussianBlur(img, (0, 0), 1.2).astype(np.float32)
    # tło (jasny, gładki papier/stół) nie bierze udziału w dopasowaniu — liczy się tylko dzianina wokół metki
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    std = np.sqrt(np.maximum(cv2.blur(gray * gray, (15, 15)) - cv2.blur(gray, (15, 15)) ** 2, 0))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bgc = np.median(np.concatenate([img[:20].reshape(-1, 3), img[-20:].reshape(-1, 3)]), 0)
    bg = (np.abs(img.astype(np.int16) - bgc).max(2) < 28) & (std < 6) & (hsv[..., 1] < 40)
    bg = cv2.morphologyEx(bg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) > 0
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        pad = max(8, int(0.3 * max(bw, bh)))
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + bw + pad), min(H, y + bh + pad)
        m = (lb[y0:y1, x0:x1] == i).astype(np.uint8)
        ring = (cv2.dilate(m, np.ones((2 * pad + 1,) * 2, np.uint8)) > 0) & (allm[y0:y1, x0:x1] == 0) & ~bg[y0:y1, x0:x1]
        if ring.sum() < 100:
            lama_mask[lb == i] = 1
            used.append('lama')
            continue
        tgt = g[y0:y1, x0:x1]
        ringvar = tgt[ring].var(0).sum() + 1.0
        best = None
        rw, rh = x1 - x0, y1 - y0
        for axis in ('x', 'y'):
            span, need = (W, rw) if axis == 'x' else (H, rh)
            start = (x0 if axis == 'x' else y0)
            step = max(2, need // 60)
            for d in range(-3 * need, 3 * need + 1, step):
                if abs(d) < (bw if axis == 'x' else bh) + 4:  # źródło nie może nachodzić na metkę
                    continue
                s0 = start + d
                if s0 < 0 or s0 + need > span:
                    continue
                sx0, sy0 = (s0, y0) if axis == 'x' else (x0, s0)
                if allm[sy0:sy0 + rh, sx0:sx0 + rw][m > 0].any():  # źródło z innej metki
                    continue
                if bg[sy0:sy0 + rh, sx0:sx0 + rw][m > 0].mean() > 0.02:  # źródło wychodzi poza próbkę
                    continue
                src = g[sy0:sy0 + rh, sx0:sx0 + rw]
                cost = ((src[ring] - tgt[ring]) ** 2).sum(1).mean()
                if best is None or cost < best[0]:
                    best = (cost, sx0, sy0, axis, d)
        if best is not None:  # dokładne dopasowanie co 1 px wokół najlepszego
            cost, sx0, sy0, axis, d = best
            for dd in range(-step, step + 1):
                a0 = (sx0 + dd, sy0) if axis == 'x' else (sx0, sy0 + dd)
                if a0[0] < 0 or a0[1] < 0 or a0[0] + rw > W or a0[1] + rh > H:
                    continue
                if allm[a0[1]:a0[1] + rh, a0[0]:a0[0] + rw][m > 0].any():
                    continue
                if bg[a0[1]:a0[1] + rh, a0[0]:a0[0] + rw][m > 0].mean() > 0.02:
                    continue
                c = ((g[a0[1]:a0[1] + rh, a0[0]:a0[0] + rw][ring] - tgt[ring]) ** 2).sum(1).mean()
                if c < best[0]:
                    best = (c, a0[0], a0[1], axis, d + dd)
        rel = best[0] / ringvar if best else 9
        if verbose:
            print(f'  łata {i}: {bw}x{bh}', 'przesunięcie' if best else '-', best and (best[3], best[4]), f'dopasowanie {rel:.2f}')
        if best is None or rel > 0.9:  # pierścień nie pasuje — wzór się nie powtarza albo źródło poza próbką
            lama_mask[lb == i] = 1
            used.append('lama')
            continue
        _, sx0, sy0, _, _ = best
        src = out.copy()
        src[y0:y1, x0:x1] = img[sy0:sy0 + rh, sx0:sx0 + rw]
        mm = np.zeros((H, W), np.uint8)
        mm[y0:y1, x0:x1] = cv2.dilate(m, np.ones((7, 7), np.uint8)) * 255
        mm[0, :] = mm[-1, :] = mm[:, 0] = mm[:, -1] = 0  # seamlessClone nie lubi maski przy krawędzi
        yy, xx = np.where(mm > 0)
        if len(xx) == 0:
            continue
        bx0, by0, bx1, by1 = xx.min(), yy.min(), xx.max() + 1, yy.max() + 1
        center = ((bx0 + bx1) // 2, (by0 + by1) // 2)
        out = cv2.seamlessClone(src[by0:by1, bx0:bx1], out, mm[by0:by1, bx0:bx1], center, cv2.NORMAL_CLONE)
        used.append('przesunięcie')
    if lama_mask.any():
        out = inpaint_lama(out, lama_mask * 255)
    return out, used


def inpaint_strips(img, mask, verbose=False):
    """Metka zwykle zachodzi na kilka pasów wzoru i leży przy brzegu próbki, więc jedno przesunięcie całości rzadko
    pasuje. Tu łatę dzielimy na paski wzdłuż pasów dzianiny (poziome albo pionowe — wybór po koszcie) i każdy pasek
    wypełniamy tym samym rzędem dzianiny przesuniętym wzdłuż pasa; kolejne paski wolą to samo przesunięcie (spójny
    motyw). Złożoną łatę wtapia Poisson (cv2.seamlessClone). Słabe dopasowanie → LaMa."""
    out = img.copy()
    H, W = img.shape[:2]
    allm = (mask > 0).astype(np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    std = np.sqrt(np.maximum(cv2.blur(gray * gray, (15, 15)) - cv2.blur(gray, (15, 15)) ** 2, 0))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bgc = np.median(np.concatenate([img[:20].reshape(-1, 3), img[-20:].reshape(-1, 3)]), 0)
    bg = (np.abs(img.astype(np.int16) - bgc).max(2) < 28) & (std < 6) & (hsv[..., 1] < 40)
    bg = cv2.morphologyEx(bg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8)) > 0
    g = cv2.GaussianBlur(img, (0, 0), 1.2).astype(np.float32)
    n, lb, st, _ = cv2.connectedComponentsWithStats(allm)
    lama_mask = np.zeros_like(allm)
    used = []
    for i in range(1, n):
        x, y, bw, bh, _ = st[i]
        best_axis = None
        for axis in ('x', 'y'):
            # układ „wzdłuż osi x”: dla osi y transponujemy wszystko i używamy tego samego kodu
            T = (lambda a: a) if axis == 'x' else (lambda a: np.swapaxes(a, 0, 1))
            G, M, A, B = T(g), T((lb == i).astype(np.uint8)), T(allm), T(bg)
            px, py, pw, ph = (x, y, bw, bh) if axis == 'x' else (y, x, bh, bw)
            HH, WW = M.shape
            strip = max(12, ph // 6)
            ov = max(6, strip // 3)
            fill = np.zeros((ph, pw, 3), np.float32)
            total, cnt, prev = 0.0, 0, None
            ok = True
            for r0 in range(py, py + ph, strip):
                r1 = min(py + ph, r0 + strip)
                a0, a1 = max(0, r0 - ov), min(HH, r1 + ov)
                cols = np.where(M[r0:r1].any(0))[0]
                if not len(cols):
                    continue
                c0, c1 = cols.min(), cols.max() + 1
                e0, e1 = max(0, c0 - 3 * ov), min(WW, c1 + 3 * ov)  # pierścień: boki paska + zakładki góra/dół
                tg = G[a0:a1, e0:e1]
                ring = (A[a0:a1, e0:e1] == 0) & ~B[a0:a1, e0:e1]
                if ring.sum() < 30:
                    ok = False
                    break
                var = tg[ring].var(0).sum() + 25.0
                best = None
                wneed = c1 - c0
                for d in range(-(WW), WW, 2):
                    if abs(d) < wneed + 4 or e0 + d < 0 or e1 + d > WW:
                        continue
                    if A[r0:r1, c0 + d:c1 + d].any() or B[r0:r1, c0 + d:c1 + d].mean() > 0.02:
                        continue
                    src = G[a0:a1, e0 + d:e1 + d]
                    cost = ((src[ring] - tg[ring]) ** 2).sum(1).mean() / var
                    if prev is not None and abs(d - prev) > 2:
                        cost += 0.15  # spójność motywu między paskami
                    if best is None or cost < best[0]:
                        best = (cost, d)
                if best is None:
                    ok = False
                    break
                prev = best[1]
                total += best[0]
                cnt += 1
                fill[r0 - py:r1 - py, c0 - px:c1 - px] = T(img)[r0:r1, c0 + best[1]:c1 + best[1]].astype(np.float32)
            if ok and cnt and (best_axis is None or total / cnt < best_axis[0]):
                best_axis = (total / cnt, axis, fill.copy())
        if verbose:
            print(f'  łata {i}: {bw}x{bh}', best_axis and (best_axis[1], round(best_axis[0], 2)))
        if best_axis is None or best_axis[0] > 1.6:
            lama_mask[lb == i] = 1
            used.append('lama')
            continue
        _, axis, fill = best_axis
        if axis == 'y':
            fill = np.swapaxes(fill, 0, 1)
        src = out.copy()
        mi = (lb[y:y + bh, x:x + bw] == i)
        src[y:y + bh, x:x + bw][mi] = fill.astype(np.uint8)[mi]
        mm = cv2.dilate((lb == i).astype(np.uint8), np.ones((7, 7), np.uint8)) * 255
        mm[0, :] = mm[-1, :] = mm[:, 0] = mm[:, -1] = 0
        # brzeg 7 px poza maską bierzemy z oryginału — Poisson dopasowuje do niego ton łaty
        yy, xx = np.where(mm > 0)
        bx0, by0, bx1, by1 = xx.min(), yy.min(), xx.max() + 1, yy.max() + 1
        out = cv2.seamlessClone(src[by0:by1, bx0:bx1], out, mm[by0:by1, bx0:bx1],
                                ((bx0 + bx1) // 2, (by0 + by1) // 2), cv2.NORMAL_CLONE)
        used.append('paski-' + axis)
    if lama_mask.any():
        out = inpaint_lama(out, lama_mask * 255)
    return out, used


def pion(img, rel=''):
    """Kamil 21.10: wszystkie zdjęcia w pionie (poziome obrócone o 90° w prawo), jedynie akryl w poziomie."""
    if 'ACRYLIC' in rel.upper():
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE) if img.shape[0] > img.shape[1] else img
    return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE) if img.shape[1] > img.shape[0] else img


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, dst = args
    only = set(opts['tylko'].split(',')) if opts.get('tylko') else None
    thr = float(opts.get('prog') or 0.25)
    missing = []
    for root, _, files in os.walk(src, followlinks=True):
        for fn in sorted(files):
            if not fn.lower().endswith(EXT) or (only and fn not in only):
                continue
            rel = os.path.relpath(os.path.join(root, fn), src)
            out = os.path.join(dst, os.path.splitext(rel)[0] + '.jpg')
            if os.path.exists(out) and 'force' not in opts:
                continue
            img = cv2.imread(os.path.join(root, fn), cv2.IMREAD_COLOR)  # stosuje obrót EXIF
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            cache = os.path.join(opts.get('cache') or MASKS, os.path.splitext(rel)[0] + '.png')
            if os.path.exists(cache):  # maska z poprzedniego przebiegu (OWLv2 + SAM to ~5 s na zdjęcie)
                mask = cv2.imread(cache, cv2.IMREAD_GRAYSCALE)
                boxes = [1] if mask.any() else []
            else:
                boxes = detect(rgb, thr)
                mask = segment(rgb, boxes) if boxes else np.zeros(img.shape[:2], np.uint8)
                os.makedirs(os.path.dirname(cache), exist_ok=True)
                cv2.imwrite(cache, mask)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if not boxes:
                missing.append(rel)
                cv2.imwrite(out, pion(img, rel), [cv2.IMWRITE_JPEG_QUALITY, 95])
                print('brak metki', rel, flush=True)
                continue
            how = []
            if opts.get('metoda') == 'cv2':
                res = cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA)
            elif opts.get('metoda') == 'lama':
                res = inpaint_lama(img, mask)
            elif opts.get('metoda') == 'big':
                res = inpaint_biglama(img, mask, int(opts.get('max') or 1600))
            elif opts.get('metoda') == 'przesun':
                res, how = inpaint_shift(img, mask, 'verbose' in opts)
            else:
                res, how = inpaint_strips(img, mask, 'verbose' in opts)
            cv2.imwrite(out, pion(res, rel), [cv2.IMWRITE_JPEG_QUALITY, 95])
            if 'maski' in opts:
                vis = img.copy()
                vis[mask > 0] = (0.4 * vis[mask > 0] + [0, 0, 150]).astype(np.uint8)
                cv2.imwrite(os.path.splitext(out)[0] + '_maska.jpg', cv2.resize(vis, None, fx=0.4, fy=0.4))
            print('ok', rel, f'{(mask > 0).mean() * 100:.1f}% zdjęcia', ' '.join(how), flush=True)
    if missing:
        with open(os.path.join(dst, '_bez_metki.txt'), 'a') as f:
            f.write('\n'.join(missing) + '\n')
    print('bez metki:', len(missing))


if __name__ == '__main__':
    main()
