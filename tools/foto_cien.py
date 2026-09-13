#!/usr/bin/env python3
"""Wariant „premium”: miękki cień kontaktowy pod czapką + delikatne wyostrzenie splotu, tło zostaje białe.
Użycie: python3 tools/foto_cien.py <folder_wyj> [--gradient] <plik.jpg> [...]   (--gradient = ciepłe jasne tło zamiast bieli)"""
import sys, os, numpy as np
from PIL import Image, ImageFilter, ImageDraw
out_dir = sys.argv[1]; GRAD = '--gradient' in sys.argv; files = [a for a in sys.argv[2:] if a != '--gradient']
os.makedirs(out_dir, exist_ok=True)
def gradient(w, h):
    top = np.array([250, 249, 247], float); bot = np.array([238, 234, 229], float)
    t = np.linspace(0, 1, h)[:, None, None]
    return Image.fromarray(np.repeat(top * (1 - t) + bot * t, w, axis=1).astype(np.uint8))
def process(im):
    w, h = im.size
    a = np.asarray(im.convert('L'))
    m = Image.fromarray(((a < 245) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
    x0, y0, x1, y1 = m.getbbox()
    sh = Image.new('L', (w, h), 0); d = ImageDraw.Draw(sh); cw = (x1 - x0) * 0.42
    d.ellipse([(x0 + x1) / 2 - cw, y1 - 28, (x0 + x1) / 2 + cw, y1 + 26], fill=110)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    drop = m.point(lambda v: int(v * 0.22)).filter(ImageFilter.GaussianBlur(30))
    drop = Image.fromarray(np.roll(np.asarray(drop), 18, axis=0))
    shadow = Image.fromarray(np.maximum(np.asarray(sh), np.asarray(drop)))
    canvas = Image.composite(Image.new('RGB', (w, h), (60, 52, 46)), gradient(w, h) if GRAD else Image.new('RGB', (w, h), (255, 255, 255)), shadow)
    obj = im.filter(ImageFilter.UnsharpMask(radius=3, percent=35, threshold=2))
    if GRAD:
        # zdjęcie na białym „mnożymy” przez tło: biel staje się tłem, włoski futra wtapiają się bez obwódki;
        # cień tylko poza czapką (wewnątrz maski mnożymy przez czyste tło)
        o = np.asarray(obj).astype(np.float32) / 255
        inside = o * (np.asarray(gradient(w, h)).astype(np.float32) / 255)
        outside = o * (np.asarray(canvas).astype(np.float32) / 255)
        mm = (np.asarray(m).astype(np.float32) / 255)[:, :, None]
        return Image.fromarray(np.clip((inside * mm + outside * (1 - mm)) * 255 + 0.5, 0, 255).astype(np.uint8))
    return Image.composite(obj, canvas, m)
for p in files:
    process(Image.open(p).convert('RGB')).save(os.path.join(out_dir, os.path.basename(p)), quality=92, optimize=True)
    print('ok', os.path.basename(p), flush=True)
