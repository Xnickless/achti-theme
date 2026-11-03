"""Przypisuje produktom kartę kolorów innego modelu albo paletę (uwagi Adriana 03.11.2026).

  python3 tools/colorcards/przypisz_karte.py PLAN.json [--crops=KATALOG] [--dry-run]

PLAN = {"AZ-2837PC": "AZ-2808PC", "AZ-2949PC": "COLORCARD ATENA", ...}
- wartość z kodem produktu = skopiuj kartę i listę kolorów z tego produktu (kółka już są w Plikach),
- wartość z nazwą karty = kolory z <crops>/manifest.json; kółka wgrywane, jeśli ich nie ma.
Produkt nie może mieć jeszcze opcji „Kolor”. mapa.json dostaje nową kartę.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
sys.argv = [sys.argv[0]] + (['--dry-run'] if '--dry-run' in sys.argv else [])
sys.path.insert(0, HERE)
import set_warianty as sw  # noqa: E402

plan = json.load(open(args[0]))
mapa_path = os.path.join(HERE, 'mapa.json')
mapa = json.load(open(mapa_path))
crops = opts.get('crops')
manifest = json.load(open(os.path.join(crops, 'manifest.json'))) if crops else {}
have = sw.existing_files()
uploaded = set()


def source(code):
    r = sw.si.gql('''query($q:String){ products(first:5, query:$q){ nodes{ options{ name values }
        metafield(namespace:"custom", key:"kolornik"){ value } variants(first:1){ nodes{ sku } } } } }''',
                  {'q': f'sku:{code}*'})
    for p in r['products']['nodes']:
        if p['variants']['nodes'][0]['sku'].startswith(code):
            vals = next(o['values'] for o in p['options'] if o['name'] == 'Kolor')
            return vals
    raise SystemExit(f'brak produktu źródłowego {code}')


for code, src in plan.items():
    if src.startswith('COLORCARD') or src not in mapa:
        card = src
        colors = sorted(manifest[card], key=sw.natural)
        if card not in uploaded:
            n = sw.upload_card(card, colors, crops, have, card)
            uploaded.add(card)
            if n:
                print(f'  {card}: {n} kółek do Plików')
    else:
        card = mapa[src]
        colors = source(src)
    print(f'{code:12} ← {card} ({len(colors)}): {sw.add_variants(code, card, colors)}', flush=True)
    if not sw.DRY:
        mapa[code] = card
if not sw.DRY:
    json.dump(mapa, open(mapa_path, 'w'), ensure_ascii=False, indent=1)
