"""Która czapka ma którą kartę kolorów: mapa.py → tools/colorcards/mapa.json {SKU: karta | null | "?"}.

Źródło: drive-tree.json (foldery „KOMPRESJA” i „COLORCARDS ACHTI” z Drive Adriana).
Zasada Adriana: folder czapki = karta o tej samej nazwie (VINCI → COLORCARD VINCI), folder „CZAPKI PO NUMERZE
MODELU” = karta z numerem modelu w nazwie, „TYLKO JEDEN KOLOR” = bez wariantów (null). "?" = do wyjaśnienia.
"""
import json, os, re

HERE = os.path.dirname(__file__)
tree = json.load(open(os.path.join(HERE, 'drive-tree.json')))
prods = json.load(open(os.path.join(HERE, '..', 'achti-produkty.json')))
cards = list(tree['colorcards'])
codes = {p['code'] for p in prods}
by_file = {(p.get('plik') or '').upper(): p['code'] for p in prods}

# folder przędzy → karta, gdy nazwy się różnią (None = brak karty, '?' = pytanie do Adriana)
ALIAS = {
    'TURBO VEZUV': 'COLORCARD VEZUV TURBO',
    'COLORCARD 100% AKRYL': 'ACRYLIC 100%',
    'AKRYL MOULINE': 'ACRYLIC MOULINE 100%',
    'ATENA': '?', 'ATENA+VEZUV+GRASS': '?', 'AMICOSOFT': '?', 'LAMBSLOOK 90.10': '?',
    'do wygenerowania w ai': None,  # Adrian 12.10.2026: zostają w jednym kolorze
    'CZAPKI KTÓRE MAJĄ TYLKO JEDEN KOLOR': None,
}


def sku(fn):
    if fn.upper() in by_file:
        return by_file[fn.upper()]
    m = re.match(r'AZ-?\s?(\d{3,4}[A-Z]*)', fn.upper())
    c = 'AZ-' + m.group(1)
    if c in codes:
        return c
    hit = [x for x in codes if x.startswith(c)] or [x for x in codes if x.startswith(re.sub(r'[A-Z]+$', '', c))]
    return hit[0] if len(hit) == 1 else None


def card_for_number(n):
    hit = [c for c in cards if re.search(r'(?<!\d)' + n + r'(?!\d)', c)]
    return hit[0] if hit else '?'


out = {}
for folder, files in tree['kompresja'].items():
    for f in files:
        s = sku(f['name'])
        if not s:
            continue
        if folder in ALIAS:
            out[s] = ALIAS[folder]
        elif folder == 'CZAPKI PO NUMERZE MODELU KOLORYSTYKA' or re.search(r'AZ-\d', folder):
            n = re.match(r'AZ-?\s?(\d{3,4})', (f['name'] if 'PO NUMERZE' in folder else folder.replace('COLORCARD ', '')).upper()).group(1)
            out[s] = card_for_number(n)
        else:
            out[s] = 'COLORCARD ' + folder if 'COLORCARD ' + folder in cards else '?'
json.dump(dict(sorted(out.items())), open(os.path.join(HERE, 'mapa.json'), 'w'), ensure_ascii=False, indent=1)
from collections import Counter
c = Counter('brak' if v is None else v for v in out.values())
print(len(out), 'produktów;', c['?'], 'do wyjaśnienia;', c['brak'], 'jeden kolor')
for k, v in c.most_common():
    print(f'{v:3d}  {k}')
