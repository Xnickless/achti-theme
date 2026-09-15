"""Sprzątanie tagów produktów: zostają tylko te, które coś robią w sklepie (kolekcje, filtry, znaczki składu).
Techniczne tagi z importu (nazwy przędzy z nazw plików, stare grupy cenowe) idą precz — Search & Discovery
pokazuje w filtrze WSZYSTKIE tagi, więc każdy śmieć jest widoczny dla klienta.
  python3 tools/clean_tags.py [--dry-run]
Kopia stanu sprzed sprzątania: tools/achti-produkty.json (pole tags) i git."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

DRY = '--dry-run' in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
KEEP = {
    'damskie', 'meskie', 'dzieci', 'premium', 'nowosc', 'opaski',   # kolekcje automatyczne
    'welna', 'merino',                                              # znaczki składu + filtr
    'podszycie', 'bez-podszycia', 'pompon', 'bez-pompona',          # filtr „Cechy”
    'wycofany',                                                     # zarezerwowany do ukrywania modeli
}

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title tags variants(first:1){ nodes{ sku } } }
            pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

prods = fetch()
usuwane = {}
for p in prods:
    for t in p['tags']:
        if t not in KEEP: usuwane[t] = usuwane.get(t, 0) + 1
print(f'produktów: {len(prods)} | tagi do usunięcia ({len(usuwane)}):')
for t, n in sorted(usuwane.items(), key=lambda x: -x[1]): print(f'  {t:20} {n} szt.')
if DRY: sys.exit()

zmienione = 0
for p in prods:
    keep = [t for t in p['tags'] if t in KEEP]
    if len(keep) == len(p['tags']): continue
    r = si.gql('mutation($p:ProductInput!){ productUpdate(input:$p){ userErrors{ message } } }',
               {'p': {'id': p['id'], 'tags': sorted(keep)}})
    if r['productUpdate']['userErrors']: print('BŁĄD', p['title'], r['productUpdate']['userErrors'])
    else: zmienione += 1
print('zaktualizowane produkty:', zmienione)

# spójność lokalnego katalogu
path = os.path.join(HERE, 'achti-produkty.json')
data = json.load(open(path, encoding='utf-8'))
for o in data:
    o['tags'] = sorted(t for t in (o.get('tags') or []) if t in KEEP)
json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('achti-produkty.json zsynchronizowany')
