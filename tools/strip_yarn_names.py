#!/usr/bin/env python3
"""Usuwa nazwy przędzy (VEZUV, MADERA, VINCI…) z opisów produktów w sklepie (decyzja Adriana 20.10.2026):
linijkę „Materiał: …” w specyfikacji i „z dzianiny <PRZĘDZA>” we wstępie (→ „z miękkiej dzianiny”).
Użycie: python3 tools/strip_yarn_names.py [--dry-run]. Tłumaczenia: translate_catalog.py + set_translations.py en fr de --only=products."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si

DRY = '--dry-run' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
YARNS = sorted({m for p in json.load(open(os.path.join(HERE, 'achti-produkty.json'))) for m in p.get('materials') or []}
               | {'VEZUV', 'MADERA', 'VINCI', 'T.VINCI', 'TURBO', 'VERONA', 'LAMBSLOOK', 'ROMA', 'ATENA', 'AMICOSOFT',
                  'AUSTRALIA', 'GRASS', 'MOULINE', 'LUREX'}, key=len, reverse=True)
NAME = '|'.join(re.escape(y) for y in YARNS)
RX_LI = re.compile(r'<li>\s*Materiał:[^<]*</li>', re.I)
RX_INTRO = re.compile(rf'z dzianiny (?:(?:{NAME})(?:\s*(?:i|,|\+)\s*)?)+', re.I)
RX_LEFT = re.compile(rf'\b(?:{NAME})\b')

def products():
    cur = None
    while True:
        r = si.gql('query($c:String){ products(first:100, after:$c){ pageInfo{ hasNextPage endCursor } nodes{ id title descriptionHtml } } }', {'c': cur})
        yield from r['products']['nodes']
        if not r['products']['pageInfo']['hasNextPage']: return
        cur = r['products']['pageInfo']['endCursor']

changed = 0
for p in products():
    old = p['descriptionHtml'] or ''
    new = RX_INTRO.sub('z miękkiej dzianiny ', RX_LI.sub('', old)).replace('dzianiny  ', 'dzianiny ').replace('dzianiny ,', 'dzianiny,')
    left = RX_LEFT.findall(re.sub(r'<[^>]+>', ' ', new))
    if left: print('ZOSTAŁO', p['title'], left)
    if new == old: continue
    changed += 1
    if DRY:
        if changed <= 3: print('—', p['title'], '\n  PRZED:', re.sub(r'<[^>]+>', ' ', old)[:220], '\n  PO:   ', re.sub(r'<[^>]+>', ' ', new)[:220])
        continue
    r = si.gql('mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ message } } }', {'p': {'id': p['id'], 'descriptionHtml': new}})
    if r['productUpdate']['userErrors']: print('BŁĄD', p['title'], r['productUpdate']['userErrors'])
print('zmienionych opisów:', changed, '(próba)' if DRY else '')
