"""Ramki próbek bez Gemini (23.10.2026): napis metki z OCR (ocr.swift, macOS Vision, 4 obroty zdjęcia) = punkt na próbce,
SAM 2.1 z tego punktu = maska całej próbki → ramka w formacie wskaz.py --tryb=probka ({box_2d 0–1000, label}).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/ramki_ocr.py ORYGINAŁY BEZ_METEK WYJŚCIE LISTA.json OCRBIN

LISTA.json = [[karta, IMG_x.JPG], …]; OCRBIN = skompilowany ocr.swift (swiftc -O ocr.swift -o ocrbin).
Metka leży na próbce, więc punkt to środek napisu; napisy „ZESTAW n” wydrukowane na kartce nad próbką (1876)
przesuwamy w dół, aż trafimy w dzianinę. Etykiety, których OCR nie odczytał, trzeba dopisać ręcznie (box_2d + label).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from usun_metki import models  # noqa: E402

LABEL = re.compile(r'(?:SET|ZESTAW|5ET)\W*(\d+)\s*([A-Z])?\b', re.I)


def unrotate(k, x, y, H, W):
    """Punkt (x, y) na obrazie obróconym k×90° w prawo → oryginał H×W."""
    if k == 0:
        return x, y
    if k == 1:  # w prawo: x' = H-1-y, y' = x
        return y, H - 1 - x
    if k == 2:
        return W - 1 - x, H - 1 - y
    return W - 1 - y, x  # k == 3: x' = y, y' = W-1-x


def labels(path, ocrbin):
    img = cv2.imread(path)
    H, W = img.shape[:2]
    out = {}
    for k in range(4):
        im = np.ascontiguousarray(np.rot90(img, -k))
        fd, tmp = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        cv2.imwrite(tmp, cv2.resize(im, None, fx=0.5, fy=0.5), [cv2.IMWRITE_JPEG_QUALITY, 92])
        res = subprocess.run([ocrbin, tmp], capture_output=True, text=True).stdout
        os.remove(tmp)
        for it in json.loads(res or '{"items":[]}')['items']:
            m = LABEL.search(it['text'].replace('+', '7').replace('!', '1').replace('&', ''))
            if not m:
                continue
            x, y = (it['x'] + it['w'] / 2) * 2, (it['y'] + it['h'] / 2) * 2
            lab = f'SET {int(m.group(1))}'
            if lab not in out:
                out[lab] = unrotate(k, x, y, H, W)
    return out


def sam_point(rgb, pts, lbl):
    import torch
    from PIL import Image
    proc, model = models()['sam']
    inp = proc(images=Image.fromarray(rgb), input_points=[[pts]], input_labels=[[lbl]], return_tensors='pt')
    with torch.no_grad():
        out = model(**inp, multimask_output=True)
    masks = proc.post_process_masks(out.pred_masks, inp['original_sizes'])[0][0].numpy()
    return masks.astype(np.uint8), out.iou_scores[0, 0].numpy()


def texture(gray):
    g = gray.astype(np.float32)
    mu = cv2.blur(g, (31, 31))
    return np.sqrt(np.maximum(cv2.blur(g * g, (31, 31)) - mu * mu, 0))


def main():
    src, clean_dir, dst, lista, ocrbin = sys.argv[1:6]
    for karta, fn in json.load(open(lista)):
        stem = fn.split('.')[0]
        labs = labels(os.path.join(src, karta, fn), ocrbin)
        img = cv2.imread(os.path.join(clean_dir, karta, stem + '.jpg'))
        H, W = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        tex = texture(cv2.resize(gray, (W // 4, H // 4)))
        frames = []
        for lab, (x, y) in sorted(labs.items()):
            # napis na gładkiej kartce (ZESTAW n nad próbką) → w dół do dzianiny
            xi, yi, y_end = int(x // 4), int(y // 4), int(y // 4 + 0.3 * tex.shape[0])
            while yi < min(y_end, tex.shape[0] - 1) and tex[yi, min(xi, tex.shape[1] - 1)] < 9:
                yi += 4
            px, py = xi * 4, yi * 4 + (60 if yi != int(y // 4) else 0)
            ms, sc = sam_point(rgb, [[px, py]], [1])
            best = None
            for m, s in zip(ms, sc):
                a = m.sum() / (H * W)
                if 0.015 < a < 0.4 and (best is None or a > best[0]):
                    best = (a, m)
            if best is None:
                print('  brak maski', karta, fn, lab, flush=True)
                continue
            m = best[1]
            ys, xs = np.nonzero(m)
            frames.append({'box_2d': [int(ys.min() * 1000 / H), int(xs.min() * 1000 / W),
                                      int(ys.max() * 1000 / H), int(xs.max() * 1000 / W)], 'label': lab,
                           'punkt': [int(py * 1000 / H), int(px * 1000 / W)], 'zrodlo': 'ocr+sam'})
        os.makedirs(os.path.join(dst, karta), exist_ok=True)
        json.dump(frames, open(os.path.join(dst, karta, fn + '.json'), 'w'), ensure_ascii=False)
        print(karta, fn, [f['label'] for f in frames], flush=True)


if __name__ == '__main__':
    main()
