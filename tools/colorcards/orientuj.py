"""Kierunek każdej próbki osobno (20.10.2026): na jednej karcie zdjęcia bywają obrócone różnie (AZ-1748PC SET 4/5/18),
więc obrót „na kartę” z kierunki-ai.json nie wystarcza.

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/orientuj.py SRC GEM [--karty=…] [--workers=8]

Dla każdej próbki z kolorem w sklepie: gemini-3.5-flash dostaje SUROWY wycinek (bez obrotu) i mówi, po której stronie
jest ściągacz (top/bottom/left/right/none). Wynik → kierunki-probek.json {karta: {"SET n": stopnie_w_prawo | null}},
a niezgodne z kierunkiem karty (kierunki-ai.json) wypisuje do przejrzenia. kolka_ai.py używa kierunku próbki, gdy jest.
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kolka_ai as k  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'kierunki-probek.json')
ROT = {'bottom': 0, 'top': 180, 'left': 270, 'right': 90}  # stopnie w prawo, żeby ściągacz był na dole

PROMPT = """This is a photo of ONE knitted fabric sample of a winter hat (a piece cut from the hat, from the cuff up to the
crown). A paper tag may lie on it. Tell me on which side of THIS image the hat's CUFF (lower edge) is.
How to recognise it (manufacturer's rules):
- the cuff is a band of straight, parallel vertical ribs (rib knit) at one end of the sample, usually ONE solid colour;
- the sample BULGES / is widest at the cuff end; the crown end narrows, is cut in or shows decreases, or is the plain top;
- colour bands and pattern rows run PARALLEL to the cuff;
- if both ends are ribbed, the cuff is the wider, single-colour, more regular rib; the multicolour edge is the crown.
If the sample has no cuff at all (a plain swatch), say where its lower edge most likely is based on the pattern direction,
or "none" if you cannot tell.
Return JSON {"cuff": "top"|"bottom"|"left"|"right"|"none", "confidence": 0-1}."""


def ask(win):
    body = {'contents': [{'parts': [k.part(win), {'text': PROMPT}]}],
            'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.1,
                                 'thinkingConfig': {'thinkingLevel': 'medium'}}}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent',
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': k.KEY})
    r = json.load(urllib.request.urlopen(req, timeout=120, context=k.CTX))
    return json.loads(r['candidates'][0]['content']['parts'][-1]['text'])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, gem = args
    kier = json.load(open(os.path.join(HERE, 'kierunki-ai.json')))
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    only = set(opts['karty'].split('|')) if opts.get('karty') else None
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    jobs = []
    for c in sorted(kier, key=k.natural):
        if kier[c] is None or (only and c not in only) or not os.path.isdir(os.path.join(src, c)):
            continue
        for fn in sorted(os.listdir(os.path.join(src, c))):
            jp = os.path.join(gem, c, fn + '.json')
            if not fn.lower().endswith(('.jpg', '.jpeg')) or not os.path.exists(jp):
                continue
            for s in k.trim_overlaps(json.load(open(jp))):
                m = re.search(r'(?:SET|ZESTAW)\W*(\d+)', str(s.get('label', '')).upper())
                name = f'SET {int(m.group(1))}' if m else None
                if name and name in man.get(c, []) and name not in res.get(c, {}):
                    jobs.append((c, fn, name, s['box_2d']))
    print(len(jobs), 'próbek do sprawdzenia')

    def run(j):
        c, fn, name, box = j
        win = k.window(cv2.imread(os.path.join(src, c, fn)), box, 0)
        for _ in range(3):
            try:
                return j, ask(win)
            except Exception as e:  # noqa: BLE001
                err = e
        return j, {'cuff': 'none', 'confidence': 0, 'error': str(err)[:80]}

    with cf.ThreadPoolExecutor(int(opts.get('workers') or 8)) as ex:
        for (c, fn, name, _), a in ex.map(run, jobs):
            res.setdefault(c, {})[name] = {'foto': fn, 'rot': ROT.get(a.get('cuff')), 'cuff': a.get('cuff'),
                                           'conf': a.get('confidence')}
    json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
    # zgodność z kierunkiem karty
    for c, d in sorted(res.items(), key=lambda kv: k.natural(kv[0])):
        diff = {n: v for n, v in d.items() if v['rot'] != kier.get(c)}
        if diff:
            print(c.replace('COLORCARD ', ''), f'karta={kier.get(c)}',
                  ', '.join(f"{n}({v['foto'][4:8]}):{v['rot']}" for n, v in sorted(diff.items(), key=lambda kv: k.natural(kv[0]))))


if __name__ == '__main__':
    main()
