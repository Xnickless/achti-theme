"""Nanosi nowe nazwy modeli z tools/nazwy-propozycja.json: tytuł, opis i pole name w katalogu lokalnym.
Handle produktów zostają stare (jak przy poprzedniej zmianie nazw) — nie psujemy linków i SEO adresów.
  python3 tools/apply_nazwy.py [--dry-run] [--limit=N]
Po nim: set_seo.py → translate_catalog.py → set_translations.py en fr de --only=products → katalog PDF."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
import catalog_text as ct

HERE = os.path.dirname(os.path.abspath(__file__))
DRY = '--dry-run' in sys.argv
LIMIT = int(next((a[8:] for a in sys.argv if a.startswith('--limit=')), '0'))

prop = {w['code'].upper(): w for w in json.load(open(os.path.join(HERE, 'nazwy-propozycja.json'), encoding='utf-8'))}
katalog = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
by_code = {p['code'].upper(): p for p in katalog}

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title
            variants(first:1){ nodes{ sku } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

prods = fetch()
if LIMIT: prods = prods[:LIMIT]
zmiana, brak = 0, []
for p in prods:
    code = (p['variants']['nodes'][0]['sku'] or '').upper()
    w, src = prop.get(code), by_code.get(code)
    if not w or not src: brak.append(code); continue
    name = w['nowa']
    segment = src.get('segment') or 'Damska'
    kind = src.get('product_type') or 'Czapka'
    flags = set(src.get('flags') or [])
    title = ct.title_for(name, segment, kind)
    body = ct.body_for(name, segment, kind, src.get('materials') or [], src.get('size') or 'One Size', flags,
                       code, sklad=src.get('sklad'), podszycie=src.get('podszycie'), opis=src.get('opis'))
    if title == p['title'] and not DRY and src.get('name') == name: continue
    zmiana += 1
    if DRY:
        if zmiana <= 5: print(f'  {code}: „{p["title"]}” -> „{title}”')
        continue
    r = si.gql('mutation($p:ProductInput!){ productUpdate(input:$p){ userErrors{ field message } } }',
               {'p': {'id': p['id'], 'title': title, 'descriptionHtml': body}})
    if r['productUpdate']['userErrors']: print('BŁĄD', code, r['productUpdate']['userErrors'])
    else: src['name'] = name; src['title'] = title; src['body_html'] = body
if not DRY:
    json.dump(katalog, open(os.path.join(HERE, 'achti-produkty.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(('do zmiany: ' if DRY else 'zmienione: ') + str(zmiana), '| bez propozycji:', brak or 'brak')
