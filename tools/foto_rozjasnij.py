#!/usr/bin/env python3
"""Lekkie rozjaśnienie czapek: krzywa gamma na jasności (HSV V), kolor i białe tło bez zmian.
Siła zależy od jasności czapki: ciemne (śr. ~20) gamma 0.72, średnie ~0.85, jasne (>=170) 0.95.
Użycie: python3 tools/foto_rozjasnij.py <folder_wyj> auto|<gamma> <plik.jpg> [...]"""
import sys, os, numpy as np
from PIL import Image
out_dir, mode, files = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out_dir, exist_ok=True)
def auto_gamma(im):
    L = im.max(axis=2); m = L < 0.94
    mean = float(L[m].mean() * 255) if m.any() else 128
    return float(np.interp(mean, [20, 90, 170], [0.72, 0.85, 0.95])), mean
for path in files:
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float32) / 255
    gamma, mean = (auto_gamma(im) if mode == 'auto' else (float(mode), 0))
    v = im.max(axis=2, keepdims=True)
    scale = np.where(v > 0, np.power(v, gamma) / np.maximum(v, 1e-6), 1)
    res = np.clip(im * scale, 0, 1)
    Image.fromarray((res * 255 + 0.5).astype(np.uint8)).save(os.path.join(out_dir, os.path.basename(path)), quality=92, optimize=True)
    print(f'ok gamma={gamma:.2f} jasność={mean:.0f} {os.path.basename(path)}', flush=True)
