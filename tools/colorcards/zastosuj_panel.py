"""Obroty z panelu „Kierunek próbek kolorów” (https://claude.ai/artifact/JaYADVHi6BNV93x7ne8cy7, 23.10.2026) → pliki próbek
→ Shopify. Panel pokazuje próbki w stanie z dnia publikacji panelu; obrót w panelu jest względem tego stanu, więc
skrypt pamięta, co już zastosował (panel-zastosowane.json), i obraca tylko o różnicę.

  1. ArtifactData list karty → out_dir=KATALOG (Claude robi to narzędziem; powstaje KATALOG/karty/<id>.json)
  2. ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/zastosuj_panel.py KATALOG/karty [--dry-run]
  3. python3 tools/colorcards/set_warianty.py ~/Claude/achti-foto/probki-panel --upload-only --replace
"""
import json
import os
import shutil
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser('~/Claude/achti-foto/probki-wgraj')  # to, co jest na sklepie
OUT = os.path.expanduser('~/Claude/achti-foto/probki-panel')  # tylko zmienione karty, do wgrania
DONE = os.path.join(HERE, 'panel-zastosowane.json')


def main():
    src_dir = sys.argv[1]
    dry = '--dry-run' in sys.argv
    manifest = json.load(open(os.path.join(SRC, 'manifest.json')))
    done = json.load(open(DONE)) if os.path.exists(DONE) else {}
    shutil.rmtree(OUT, ignore_errors=True)
    sub = {}
    for fn in sorted(os.listdir(src_dir)):
        if not fn.endswith('.json'):
            continue
        d = json.load(open(os.path.join(src_dir, fn)))
        d = d.get('data', d)  # plik z ArtifactData może mieć dane w polu data
        karta, obroty = d.get('karta'), d.get('obroty') or {}
        if karta not in manifest:
            continue
        for kolor in manifest[karta]:
            want = int(obroty.get(kolor, 0)) % 360
            have = int(done.get(karta, {}).get(kolor, 0)) % 360
            delta = (want - have) % 360
            if not delta:
                continue
            print(f'{karta} {kolor}: +{delta}°')
            if dry:
                continue
            p = os.path.join(SRC, karta, kolor + '.jpg')
            im = cv2.imread(p)
            cv2.imwrite(p, np.ascontiguousarray(np.rot90(im, -(delta // 90))), [cv2.IMWRITE_JPEG_QUALITY, 92])
            os.makedirs(os.path.join(OUT, karta), exist_ok=True)
            shutil.copy(p, os.path.join(OUT, karta, kolor + '.jpg'))
            sub.setdefault(karta, {})[kolor] = manifest[karta][kolor]
            done.setdefault(karta, {})[kolor] = want
    if dry or not sub:
        print('nic do wgrania' if not sub else '')
        return
    json.dump(sub, open(os.path.join(OUT, 'manifest.json'), 'w'), ensure_ascii=False)
    json.dump(done, open(DONE, 'w'), ensure_ascii=False, indent=1)
    print(f'{sum(len(v) for v in sub.values())} próbek z {len(sub)} kart w {OUT}')


if __name__ == '__main__':
    main()
