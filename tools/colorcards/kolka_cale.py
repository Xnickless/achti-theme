"""Kółka = cała próbka (21.10.2026, koncept Kamila po usunięciu metek): z każdego zdjęcia karty modelu wycinamy każdą
próbkę (SET n) osobno i mieścimy CAŁĄ dzianinę w kółku, tak jak leży na zdjęciu (zdjęcia w pionie, bez dodatkowego
obracania; próbka leżąca poziomo obrócona o 90° w prawo, żeby każda stała pionowo). Bez AI — prawdziwe zdjęcie, kolory i splot 1:1.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/kolka_cale.py BEZ_METEK ORYGINAŁY GEM WYJŚCIE [KARTA|"*"]
        [--tlo=f2f1ef] [--size=900] [--tylko-sklep] [--latanie] [--force]

BEZ_METEK  wynik usun_metki.py (<karta>/<zdjęcie>.jpg, obrócone do pionu)
ORYGINAŁY  zdjęcia źródłowe (do sprawdzenia, czy zdjęcie było obrócone — ramki Gemini są w układzie oryginału)
GEM        ramki próbek (gemmix: <karta>/<zdjęcie>.json, box_2d 0–1000 + label „SET n”)
Kroki: ramka próbki (zakładki sąsiednich przycięte w połowie, pelna_probka.trim_overlaps) → SAM 2 robi maskę samej
próbki (bez sąsiednich próbek i tła) → próbka na jednolitym tle (--tlo, kolor kafelków sklepu) → kwadrat wokół
najmniejszego okręgu opisanego na masce, więc po przycięciu do kółka widać całą dzianinę z rogami.
--latanie  na JEDNOLITEJ dzianinie (wokół metki rozrzut jasności ≤ 32, barwy ≤ 10 w LAB) miejsce po metce łatane
           prawdziwą dzianiną z tej samej próbki (latanie.py, image quilting) zamiast wyniku LaMa — bez ciemnych plam;
           na wzorach zostaje LaMa (łatanie przestawiało motywy). Dziura = różnica oryginał/BEZ_METEK.
--tylko-sklep  tylko kolory z manifest.json (te, które są wariantami w sklepie).
Wynik: WYJŚCIE/<karta>/SET n.jpg + manifest.json → set_warianty.py WYJŚCIE --upload-only --replace.
"""
import json
import os
import re
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from latanie import quilt  # noqa: E402
import usun_metki as um  # noqa: E402
from pelna_probka import trim_overlaps  # noqa: E402

SAM = 'facebook/sam2.1-hiera-large'
_sam = None


def natural(t):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', t)]


def sam():
    global _sam
    if _sam is None:
        from transformers import Sam2Model, Sam2Processor
        _sam = (Sam2Processor.from_pretrained(SAM), Sam2Model.from_pretrained(SAM).eval())
    return _sam


def masks_for(rgb, boxes):
    import torch
    from PIL import Image
    proc, model = sam()
    inp = proc(images=Image.fromarray(rgb), input_boxes=[boxes], return_tensors='pt')
    with torch.no_grad():
        out = model(**inp, multimask_output=False)
    return proc.post_process_masks(out.pred_masks, inp['original_sizes'])[0][:, 0].numpy()


def rotated_box(b, cw):
    """box_2d [y0,x0,y1,x1] (0–1000) po obrocie zdjęcia o 90° w prawo (cw) lub w lewo."""
    y0, x0, y1, x1 = b
    return [x0, 1000 - y1, x1, 1000 - y0] if cw else [1000 - x1, y0, 1000 - x0, y1]


def circle(img, mask, bg, size):
    m = (mask > 0).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 2:  # tylko największy kawałek (SAM czasem łapie okruch sąsiedniej próbki)
        m = (lb == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    (cx, cy), r = cv2.minEnclosingCircle(np.vstack(cnts))
    r *= 1.03
    a = cv2.GaussianBlur(m.astype(np.float32), (5, 5), 0)[..., None]  # miękka krawędź próbki
    comp = (img * a + np.array(bg, np.float32) * (1 - a)).astype(np.uint8)
    H, W = img.shape[:2]
    x0, y0, side = int(cx - r), int(cy - r), int(2 * r)
    canvas = np.full((side, side, 3), bg, np.uint8)
    sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(W, x0 + side), min(H, y0 + side)
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = comp[sy0:sy1, sx0:sx1]
    _, _, bw, bh = cv2.boundingRect(m)
    if bw > bh:  # Kamil 21.10: każda próbka w kółku stoi pionowo
        canvas = cv2.rotate(canvas, cv2.ROTATE_90_CLOCKWISE)
    return cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    clean, orig, gem, out = args[:4]
    want = args[4] if len(args) > 4 else '*'
    hx = opts.get('tlo') or 'f2f1ef'
    bg = [int(hx[i:i + 2], 16) for i in (4, 2, 0)]  # BGR
    size = int(opts.get('size') or 900)
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    res = json.load(open(os.path.join(out, 'manifest.json'))) if os.path.exists(os.path.join(out, 'manifest.json')) else {}
    cards = [c for c in sorted(os.listdir(gem), key=natural) if want in ('*', c) or want in c]
    for card in cards:
        if not os.path.isdir(os.path.join(clean, card)):
            print('brak zdjęć bez metek:', card)
            continue
        made = set(res.get(card, []))
        for jf in sorted(os.listdir(os.path.join(gem, card)), key=natural):
            fn = jf[:-5]
            cp = os.path.join(clean, card, os.path.splitext(fn)[0] + '.jpg')
            op = os.path.join(orig, card, fn)
            if not os.path.exists(cp) or not os.path.exists(op):
                continue
            samples = []
            for s in trim_overlaps(json.load(open(os.path.join(gem, card, jf)))):
                m = re.search(r'(?:SET|ZESTAW)\W*(\d+)', str(s.get('label', '')).upper())
                if not m:
                    continue
                name = f'SET {int(m.group(1))}'
                if 'tylko-sklep' in opts and name not in man.get(card, []):
                    continue
                if (name in made or os.path.exists(os.path.join(out, card, name + '.jpg'))) and 'force' not in opts:
                    made.add(name)
                    continue
                samples.append((name, s['box_2d']))
            if not samples:
                continue
            img = cv2.imread(cp)
            H, W = img.shape[:2]
            org = cv2.imread(op)  # IMREAD_COLOR stosuje EXIF, jak przy ramkach Gemini
            oh, ow = org.shape[:2]
            turned = (oh > ow) != (H > W)
            px = []
            for name, b in samples:
                if turned:
                    b = rotated_box(b, cw=not ('ACRYLIC' in card.upper()))
                px.append([b[1] * W / 1000, b[0] * H / 1000, b[3] * W / 1000, b[2] * H / 1000])
            if 'latanie' in opts:  # miejsce po metce = prawdziwa dzianina z tej samej próbki zamiast LaMa
                if turned:
                    org = cv2.rotate(org, cv2.ROTATE_90_COUNTERCLOCKWISE if 'ACRYLIC' in card.upper() else cv2.ROTATE_90_CLOCKWISE)
                # maska metki = ta sama, której użył usun_metki (OWLv2 + SAM, zapisana w maski-metek); różnica obrazów
                # gubiła białe metki na białej dzianinie i oryginał z metką wracał do kółka
                mpath = os.path.join(um.MASKS, card, os.path.splitext(fn)[0] + '.png')
                if os.path.exists(mpath):
                    hole = cv2.imread(mpath, cv2.IMREAD_GRAYSCALE) > 0
                else:
                    o0 = cv2.imread(op)
                    rgb0 = cv2.cvtColor(o0, cv2.COLOR_BGR2RGB)
                    bx = um.detect(rgb0, 0.25)
                    hole = (um.segment(rgb0, bx) > 0) if bx else np.zeros(o0.shape[:2], bool)
                    os.makedirs(os.path.dirname(mpath), exist_ok=True)
                    cv2.imwrite(mpath, hole.astype(np.uint8) * 255)
                if turned:
                    hole = cv2.rotate(hole.astype(np.uint8), cv2.ROTATE_90_COUNTERCLOCKWISE if 'ACRYLIC' in card.upper()
                                      else cv2.ROTATE_90_CLOCKWISE) > 0
                patched = org.copy()
                smasks = masks_for(cv2.cvtColor(org, cv2.COLOR_BGR2RGB), px)  # obrys każdej próbki (źródło łat)
                labb = cv2.cvtColor(cv2.GaussianBlur(org, (0, 0), 6), cv2.COLOR_BGR2LAB).astype(np.float32)
                for b, sm_ in zip(px, smasks):
                    hb = np.zeros_like(hole)
                    hb[int(b[1]):int(b[3]), int(b[0]):int(b[2])] = hole[int(b[1]):int(b[3]), int(b[0]):int(b[2])]
                    if not hb.any():
                        continue
                    # łatanie tylko na jednolitej dzianinie (prążek, melanż); na wzorze przestawiało motywy → LaMa
                    k = int(np.sqrt(hb.sum()) // 2) * 2 + 1
                    ring = (cv2.dilate(hb.astype(np.uint8), np.ones((k, k), np.uint8)) > 0) & ~hole & (sm_ > 0)
                    v = labb[ring]
                    if len(v) < 100 or v[:, 0].std() > 32 or v[:, 1:].std(0).sum() > 10:
                        continue
                    before = patched.copy()
                    patched = quilt(patched, hole, b, allowed=sm_ > 0)
                    # do wyniku idzie łata tylko tam, gdzie była metka i quilt ją faktycznie wypełnił; wszędzie
                    # indziej zostaje obraz bez metek (LaMa + ton) — nigdy oryginał z metką
                    done = hb & (np.abs(patched.astype(np.int16) - before.astype(np.int16)).max(2) > 0)
                    img = np.where(done[..., None], patched, img)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            masks = masks_for(rgb, px)
            os.makedirs(os.path.join(out, card), exist_ok=True)
            for (name, _), mk in zip(samples, masks):
                cv2.imwrite(os.path.join(out, card, name + '.jpg'), circle(img, mk, bg, size), [cv2.IMWRITE_JPEG_QUALITY, 92])
                made.add(name)
            print(card.replace('COLORCARD ', ''), fn, ', '.join(n for n, _ in samples), flush=True)
        res[card] = sorted(made, key=natural)
        json.dump(res, open(os.path.join(out, 'manifest.json'), 'w'), ensure_ascii=False, indent=1)
        brak = [c for c in man.get(card, []) if c not in made]
        if brak:
            print('  brak w sklepie:', card, ', '.join(brak))


if __name__ == '__main__':
    main()
