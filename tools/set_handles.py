#!/usr/bin/env python3
"""Adresy produktów (handle) z aktualnych tytułów: „Czapka zimowa damska Erina” → /products/czapka-zimowa-damska-erina.
Stare adresy z nazwami roboczymi (…-beanie-lodz) dostają automatyczne przekierowanie 301 (redirectNewHandle).
Źródło prawdy = tytuły w sklepie (Admin API), nie achti-produkty.json.
Użycie: python3 tools/set_handles.py [--dry-run] [--only=AZ-1145PC,AZ-910PC]
Po zmianie nazw modeli (apply_nazwy.py) uruchomić ponownie — zmienia tylko produkty, których adres nie pasuje do tytułu."""
import os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

DRY = '--dry-run' in sys.argv
ONLY = {x.strip().upper() for a in sys.argv if a.startswith('--only=') for x in a[7:].split(',')}
PL = str.maketrans('ąćęłńóśźżĄĆĘŁŃÓŚŹŻ', 'acelnoszzACELNOSZZ')

def slug(title):
    s = unicodedata.normalize('NFKD', title.translate(PL)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')

products, cursor = [], None
while True:
    r = si.gql('''query($c:String){ products(first:250, after:$c){ nodes{ id title handle variants(first:1){ nodes{ sku } } }
                  pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
    products += r['products']['nodes']
    if not r['products']['pageInfo']['hasNextPage']: break
    cursor = r['products']['pageInfo']['endCursor']

taken = {p['handle'] for p in products}
seen, todo = set(), []
for p in products:
    sku = (p['variants']['nodes'][0]['sku'] or '') if p['variants']['nodes'] else ''
    if ONLY and sku.upper() not in ONLY: continue
    new = slug(p['title'])
    if new in seen:  # ten sam tytuł dwa razy — dopisz kod, żeby adres był unikalny
        new = f"{new}-{slug(sku)}"
    seen.add(new)
    if new != p['handle']:
        if new in taken:
            print('  ZAJĘTY', sku, new); continue
        todo.append((p, sku, new))

print(f'produktów: {len(products)}, do zmiany: {len(todo)}')
n = 0
for p, sku, new in todo:
    if DRY:
        if n < 15: print(f'  {sku}: /products/{p["handle"]} → /products/{new}')
        n += 1; continue
    r = si.gql('mutation($i:ProductInput!){ productUpdate(input:$i){ product{ handle } userErrors{ field message } } }',
               {'i': {'id': p['id'], 'handle': new, 'redirectNewHandle': True}})
    err = r['productUpdate']['userErrors']
    if err: print('  BŁĄD', sku, err)
    else: n += 1
print('zmienione:' if not DRY else 'do zmiany:', n)
