"""Ręczne wycięcie próbki, gdy automat jej nie złapał (uwagi Adriana 03.11.2026).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/reczna_probka.py siatka ZDJĘCIE PODGLĄD.jpg
  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/reczna_probka.py wytnij ZDJĘCIE WYJŚCIE.jpg x0,y0,x1,y1 [obrót] [neg=x,y;x,y] [prost]

siatka = miniatura 1000 px z siatką co 10 % (współrzędne w tysięcznych szerokości/wysokości zdjęcia).
wytnij = SAM z ramki (tysięczne), bez kartki, obrót w prawo (ściągacz na dół), biały kwadrat 1000 px jak wytnij_probki.py.
"""
import sys

import cv2
import numpy as np

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from wytnij_probki import clean, no_paper, place, sam_mask  # noqa: E402

cmd, src, out = sys.argv[1:4]
img = cv2.imread(src)
H, W = img.shape[:2]
if cmd == 'siatka':
    s = 1000 / max(H, W)
    sm = cv2.resize(img, None, fx=s, fy=s)
    h, w = sm.shape[:2]
    for i in range(1, 10):
        cv2.line(sm, (w * i // 10, 0), (w * i // 10, h), (0, 0, 255), 1)
        cv2.line(sm, (0, h * i // 10), (w, h * i // 10), (0, 0, 255), 1)
        cv2.putText(sm, str(i * 100), (w * i // 10 + 2, 14), 0, 0.45, (0, 0, 255), 1)
        cv2.putText(sm, str(i * 100), (2, h * i // 10 - 3), 0, 0.45, (0, 0, 255), 1)
    cv2.imwrite(out, sm)
else:
    x0, y0, x1, y1 = [int(v) for v in sys.argv[4].split(',')]
    deg = int(sys.argv[5]) if len(sys.argv) > 5 and '=' not in sys.argv[5] else 0
    neg = []
    for a in sys.argv[5:]:
        if a.startswith('neg='):
            neg = [(int(p.split(',')[0]) * W / 1000, int(p.split(',')[1]) * H / 1000) for p in a[4:].split(';')]
    box = [x0 * W / 1000, y0 * H / 1000, x1 * W / 1000, y1 * H / 1000]
    if 'prost' in sys.argv:  # próbka przykryta sąsiednią: sam prostokąt ramki
        m = np.zeros((H, W), np.uint8)
        m[int(box[1]):int(box[3]), int(box[0]):int(box[2])] = 1
    else:
        m = sam_mask(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), box, neg=neg)
        m = clean(m)
        mp = no_paper(img, m)
        if mp.sum() > 0.7 * m.sum():  # jasna dzianina potrafi wyglądać jak kartka — wtedy bez tego kroku
            m = mp
    res, _ = place(img, m, 1000, deg)
    cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 92])
