"""Metapole `custom.cechy` (lista tekstów) — źródło filtru „Cechy” w Search & Discovery.
Tagi zostają do kolekcji automatycznych, ale filtr po tagach pokazywał też kategorie (w „Ona” było „Męskie”,
bo modele unisex mają oba tagi). Metapole zawiera wyłącznie cechy fizyczne.
  python3 tools/set_feature_metafield.py [--dry-run] [--limit=N]
Źródło prawdy: tagi na produktach (welna/merino/podszycie/bez-podszycia/pompon/bez-pompona),
czyli set_fibre_tags.py + set_feature_tags.py uruchamiać przed tym skryptem."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

DRY = '--dry-run' in sys.argv
LIMIT = int(next((a[8:] for a in sys.argv if a.startswith('--limit=')), '0'))
NS, KEY = 'custom', 'cechy'
# tag -> etykieta widoczna dla klienta (kolejność listy = kolejność w filtrze)
MAP = [('welna', 'Z wełną'), ('merino', 'Wełna merino'),
       ('podszycie', 'Z podszyciem'), ('bez-podszycia', 'Bez podszycia'),
       ('pompon', 'Z pomponem'), ('bez-pompona', 'Bez pompona')]

def ensure_definition():
    d = si.gql('''query{ metafieldDefinitions(first:50, ownerType:PRODUCT, namespace:"custom"){ nodes{ key name type{ name } } } }''')
    if any(n['key'] == KEY for n in d['metafieldDefinitions']['nodes']):
        print('definicja metapola już istnieje'); return
    r = si.gql('''mutation($d:MetafieldDefinitionInput!){ metafieldDefinitionCreate(definition:$d){
            createdDefinition{ id name } userErrors{ field message } } }''',
        {'d': {'name': 'Cechy', 'namespace': NS, 'key': KEY, 'ownerType': 'PRODUCT',
               'type': 'list.single_line_text_field', 'pin': True,
               'description': 'Cechy do filtrowania na listingu (wełna, podszycie, pompon).',
               'access': {'storefront': 'PUBLIC_READ'}}})
    res = r['metafieldDefinitionCreate']
    print('definicja:', res['createdDefinition'] or res['userErrors'])

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title tags
            cechy: metafield(namespace:"custom", key:"cechy"){ value } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

import json
ensure_definition()
prods = fetch()
if LIMIT: prods = prods[:LIMIT]
zmiana, bez_cech = 0, 0
for p in prods:
    want = [label for tag, label in MAP if tag in p['tags']]
    if not want: bez_cech += 1
    have = json.loads(p['cechy']['value']) if p['cechy'] else []
    if have == want: continue
    zmiana += 1
    if DRY:
        print(f"  {p['title'][:40]:42} {have} -> {want}"); continue
    r = si.gql('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''',
               {'m': [{'ownerId': p['id'], 'namespace': NS, 'key': KEY, 'type': 'list.single_line_text_field',
                       'value': json.dumps(want, ensure_ascii=False)}]})
    if r['metafieldsSet']['userErrors']: print('BŁĄD', p['title'], r['metafieldsSet']['userErrors'])
print(f'{"do zmiany" if DRY else "zaktualizowane"}: {zmiana} | produktów bez żadnej cechy: {bez_cech}')
