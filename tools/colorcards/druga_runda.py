"""Druga runda usuwania metek (21.10.2026): po pierwszym przebiegu usun_metki.py część metek została — całe białe metki,
których OWLv2 nie złapał, sznurki, metki kraft, plastikowe szpilki. Tu szukamy ich ponownie NA WYNIKU pierwszej
rundy, z dodatkowymi opisami i niższym progiem, i zamalowujemy LaMa.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/druga_runda.py BEZ_METEK WYJŚCIE [--prog=0.18] [--tylko=…] [--maski]

Odrzucane wykrycia: ramka w większości na tle (luźne nitki na stole, kartoniki „ZESTAW” na podkładce — to nie metki).
Sznurek: SAM na cienkim obiekcie bywa dziurawy, więc dla wąskich ramek (proporcje > 3:1) maska = cała ramka.
Pliki bez resztek kopiowane bez zmian, więc WYJŚCIE to komplet.
"""
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usun_metki as um  # noqa: E402
from latanie import background  # noqa: E402

um.QUERIES = um.QUERIES + ['a white string or thread loop attached to a tag', 'a paper sticker label with text',
                           'a clear plastic tag fastener pin', 'a black fabric brand label']


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, dst = args
    thr = float(opts.get('prog') or 0.18)
    only = set(opts['tylko'].split(',')) if opts.get('tylko') else None
    n_fix = 0
    for root, _, files in os.walk(src):
        for fn in sorted(files):
            if not fn.lower().endswith('.jpg'):
                continue
            rel = os.path.relpath(os.path.join(root, fn), src)
            out = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if only and not any(o in rel for o in only):
                if not os.path.exists(out):
                    shutil.copy2(os.path.join(root, fn), out)
                continue
            img = cv2.imread(os.path.join(root, fn))
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            bg = background(img)
            boxes = []
            for b in um.detect(rgb, thr):
                x0, y0, x1, y1 = [int(v) for v in b]
                if bg[max(0, y0):y1, max(0, x0):x1].mean() > 0.6:  # na tle: nitki na stole, kartoniki ZESTAW
                    continue
                boxes.append(b)
            if not boxes:
                shutil.copy2(os.path.join(root, fn), out)
                continue
            mask = um.segment(rgb, boxes)
            for b in boxes:
                x0, y0, x1, y1 = [int(v) for v in b]
                w, h = x1 - x0, y1 - y0
                if max(w, h) > 3 * max(1, min(w, h)):  # sznurek — cała ramka z zapasem
                    p = max(6, int(0.15 * min(w, h)))
                    mask[max(0, y0 - p):y1 + p, max(0, x0 - p):x1 + p] = 255
            res = um.inpaint_lama(img, mask)
            cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if 'maski' in opts:
                vis = img.copy()
                vis[mask > 0] = (0.4 * vis[mask > 0] + [0, 0, 150]).astype(np.uint8)
                cv2.imwrite(os.path.splitext(out)[0] + '_maska.jpg', cv2.resize(vis, None, fx=0.3, fy=0.3))
            n_fix += 1
            print('poprawione', rel, len(boxes), flush=True)
    print('razem poprawionych:', n_fix)


if __name__ == '__main__':
    main()
