"""Jedna waga dla wszystkich wariantów (decyzja Adriana 14.09.2026: 110 g na każdą czapkę, bez rozróżniania).
  python3 tools/set_weight.py [--grams=110] [--dry-run]
apply_catalog_v2.py nadpisze wagę tylko tam, gdzie w arkuszu jest wypełniona kolumna waga_g."""
import sys
import shopify_import as si

DRY = '--dry-run' in sys.argv
GRAMS = float(next((a[8:] for a in sys.argv if a.startswith('--grams=')), '110'))

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title
            variants(first:20){ nodes{ id sku inventoryItem{ measurement{ weight{ value unit } } } } } }
            pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

def grams(v):
    w = (v['inventoryItem']['measurement'] or {}).get('weight') or {}
    val, unit = w.get('value') or 0, w.get('unit')
    return val * {'GRAMS': 1, 'KILOGRAMS': 1000, 'OUNCES': 28.3495, 'POUNDS': 453.592}.get(unit, 1)

n_prod = n_var = 0
for p in fetch():
    todo = [v for v in p['variants']['nodes'] if round(grams(v)) != round(GRAMS)]
    if not todo: continue
    n_prod += 1; n_var += len(todo)
    if DRY: print('[dry]', p['title'], [f"{v['sku']}: {grams(v):g} g" for v in todo]); continue
    r = si.gql('''mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ field message } } }''',
               {'pid': p['id'], 'v': [{'id': v['id'], 'inventoryItem': {'measurement': {'weight': {'value': GRAMS, 'unit': 'GRAMS'}}}} for v in todo]})
    err = r['productVariantsBulkUpdate']['userErrors']
    if err: print('BŁĄD', p['title'], err)
print(f'{"do zmiany" if DRY else "ustawiono"} {GRAMS:g} g: produktów {n_prod}, wariantów {n_var}')
