"""Tagi cech do filtrów na listingu (życzenie Adriana 14.09.2026): `podszycie` / `bez-podszycia` (z kolumny podszycie
w achti-produkty.json) i `pompon` / `bez-pompona` (z tools/pompon.json — detekcja ze zdjęć, detect_pompon.py; opaski bez tagu).
Wełna = tagi `welna`/`merino` z set_fibre_tags.py. Filtry w aplikacji Search & Discovery: „Tagi produktu” → grupy z etykietami.
  python3 tools/set_feature_tags.py [--dry-run]"""
import json, os, sys
import shopify_import as si

HERE = os.path.dirname(os.path.abspath(__file__)); DRY = '--dry-run' in sys.argv
LINED = {'Pełne podszycie polarowe 100% poliester': True, 'Opaska polarowa 100% poliester': True, 'Bez podszycia': False, 'Podwójna dzianina': False}
OURS = {'podszycie', 'bez-podszycia', 'pompon', 'bez-pompona'}
prods = {p['code'].upper(): p for p in json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))}
pompon = {k.upper(): v for k, v in json.load(open(os.path.join(HERE, 'pompon.json'), encoding='utf-8')).items()} if os.path.exists(os.path.join(HERE, 'pompon.json')) else {}

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title tags variants(first:1){ nodes{ sku } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

stats = dict(podszycie=0, bez_podszycia=0, pompon=0, bez_pompona=0, zmienione=0, bez_danych=0)
for p in fetch():
    sku = (p['variants']['nodes'][0]['sku'] or '').upper(); src = prods.get(sku)
    tags = set(p['tags']) - OURS
    lin = LINED.get((src or {}).get('podszycie') or '')
    if lin is True: tags.add('podszycie'); stats['podszycie'] += 1
    elif lin is False: tags.add('bez-podszycia'); stats['bez_podszycia'] += 1
    else: stats['bez_danych'] += 1
    if sku in pompon and 'opaski' not in tags:
        tags.add('pompon' if pompon[sku] else 'bez-pompona'); stats['pompon' if pompon[sku] else 'bez_pompona'] += 1
    if sorted(tags) != sorted(p['tags']):
        stats['zmienione'] += 1
        if DRY: print('[dry]', sku, sorted(tags & OURS))
        else:
            r = si.gql('mutation($p:ProductInput!){ productUpdate(input:$p){ userErrors{ message } } }', {'p': {'id': p['id'], 'tags': sorted(tags)}})
            if r['productUpdate']['userErrors']: print('BŁĄD', sku, r['productUpdate']['userErrors'])
print(stats)
