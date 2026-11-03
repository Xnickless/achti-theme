"""Usuwa kolory albo zmienia nazwę koloru we wszystkich produktach danej karty (uwagi Adriana 03.11.2026).

  python3 tools/colorcards/zmien_kolory.py usun AZ-2910PC,AZ-2688PC 10,15,16 [--dry-run]
  python3 tools/colorcards/zmien_kolory.py nazwa madera FJ229 FJ247 [--dry-run]   # wszystkie produkty z kolornikiem
Przy zmianie nazwy kopiuje kółko kolor-<karta>-<stara>.jpg na kolor-<karta>-<nowa>.jpg i poprawia SKU wariantu.
"""
import os
import sys
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import shopify_import as si  # noqa: E402

DRY = '--dry-run' in sys.argv
a = [x for x in sys.argv[1:] if not x.startswith('--')]

Q = '''query($q:String,$c:String){ products(first:50, after:$c, query:$q){ nodes{ id title
    metafield(namespace:"custom", key:"kolornik"){ value }
    options{ id name optionValues{ id name } }
    variants(first:250){ nodes{ id sku selectedOptions{ name value } } } } pageInfo{ hasNextPage endCursor } } }'''


def products(q):
    cur = None
    while True:
        r = si.gql(Q, {'q': q, 'c': cur})['products']
        yield from r['nodes']
        if not r['pageInfo']['hasNextPage']:
            return
        cur = r['pageInfo']['endCursor']


def handleize(s):
    import re
    return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('%', '')).strip('-')


if a[0] == 'usun':
    drop = set(a[2].split(','))
    for code in a[1].split(','):
        p = next(p for p in products(f'sku:{code}*') if p['variants']['nodes'][0]['sku'].startswith(code))
        ids = [v['id'] for v in p['variants']['nodes']
               if any(o['name'] == 'Kolor' and o['value'] in drop for o in v['selectedOptions'])]
        print(code, p['title'], 'usuwam', len(ids))
        if ids and not DRY:
            r = si.gql('''mutation($p:ID!,$v:[ID!]!){ productVariantsBulkDelete(productId:$p, variantsIds:$v){
                userErrors{ message } } }''', {'p': p['id'], 'v': ids})
            print('  ', r['productVariantsBulkDelete']['userErrors'] or 'OK')
elif a[0] == 'nazwa':
    card, old, new = a[1], a[2], a[3]
    oldf, newf = f'kolor-{card}-{handleize(old)}.jpg', f'kolor-{card}-{handleize(new)}.jpg'
    files = si.gql('''query($q:String){ files(first:5, query:$q){ nodes{ ... on MediaImage { image{ url } } } } }''',
                   {'q': f'filename:{oldf}'})['files']['nodes']
    url = next((n['image']['url'] for n in files if n.get('image') and oldf in n['image']['url']), None)
    print('kółko', oldf, '→', newf, url and 'OK')
    if url and not DRY:
        tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), newf)
        subprocess.run(['curl', '-sf', '-o', tmp, url], check=True)
        r = si.gql('''mutation($f:[FileCreateInput!]!){ fileCreate(files:$f){ userErrors{ message } } }''',
                   {'f': [{'originalSource': si.staged_upload(tmp), 'contentType': 'IMAGE', 'filename': newf,
                           'alt': f'Kolor {new}'}]})
        print('  ', r['fileCreate']['userErrors'] or 'wgrane')
    for p in products(f'metafields.custom.kolornik:{card}'):
        if (p['metafield'] or {}).get('value') != card:
            continue
        opt = next((o for o in p['options'] if o['name'] == 'Kolor'), None)
        ov = opt and next((v for v in opt['optionValues'] if v['name'] == old), None)
        if not ov:
            continue
        print(p['title'])
        if DRY:
            continue
        r = si.gql('''mutation($p:ID!,$o:OptionUpdateInput!,$v:[OptionValueUpdateInput!]){ productOptionUpdate(productId:$p,
            option:$o, optionValuesToUpdate:$v){ userErrors{ message } } }''',
                   {'p': p['id'], 'o': {'id': opt['id']}, 'v': [{'id': ov['id'], 'name': new}]})
        print('  ', r['productOptionUpdate']['userErrors'] or 'OK')
        upd = [{'id': v['id'], 'inventoryItem': {'sku': v['sku'].replace('-' + old, '-' + new)}}
               for v in p['variants']['nodes'] if v['sku'].endswith('-' + old)]
        if upd:
            si.gql('''mutation($p:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$p, variants:$v){
                userErrors{ message } } }''', {'p': p['id'], 'v': upd})
