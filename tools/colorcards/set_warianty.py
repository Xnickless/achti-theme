"""Kolory z kolorników jako warianty produktów + kółka w Shopify → Pliki.

  python3 tools/colorcards/set_warianty.py CROPS [--dry-run] [--only=AZ-1748PC,…] [--upload-only] [--replace] [--limit=N] [--skip=karta|karta]

CROPS = katalog z wytnij.py (<CROPS>/<karta>/<kolor>.jpg + manifest.json; karta = nazwa folderu z Drive).
Dla każdego produktu z tools/colorcards/mapa.json, którego karta ma wycięte próbki:
1. wgrywa kółka karty jako pliki `kolor-<kolornik>-<kolor>.jpg` (raz na kartę, pomija istniejące),
2. ustawia metapole `custom.kolornik` = slug karty (motyw szuka po nim plików kółek),
3. zakłada opcję „Kolor” z wartościami z karty (wariant domyślny staje się pierwszym kolorem),
   wszystkie warianty: cena produktu, SKU `<kod>-<kolor>` (np. AZ-1748PC-SET7, AZ-3082PC-203),
   bez śledzenia stanów, waga 110 g.
Produkty, które już mają opcję „Kolor”, są pomijane (żeby zmienić listę kolorów — usunąć opcję w panelu).
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import shopify_import as si  # noqa: E402

HERE = os.path.dirname(__file__)
DRY = '--dry-run' in sys.argv
UPLOAD_ONLY = '--upload-only' in sys.argv
REPLACE = '--replace' in sys.argv  # usuwa stare kółka karty i wgrywa nowe (po zmianie kadrowania)
OPTS = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
ONLY = set(OPTS['only'].split(',')) if 'only' in OPTS else None
LIMIT = int(OPTS.get('limit', 0))
SKIP = set(OPTS['skip'].split('|')) if 'skip' in OPTS else set()  # karty do pominięcia, np. --skip=COLORCARD AUSTRALIA|ACRYLIC 100%


def handleize(s):
    s = s.lower().replace('%', '')
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def slug(card):
    return handleize(re.sub(r'^COLORCARD\s+', '', card))


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]


def existing_files():
    names, cursor = set(), None
    while True:
        r = si.gql('''query($c:String){ files(first:250, after:$c, query:"filename:kolor-"){ nodes{
            ... on MediaImage { image{ url } } ... on GenericFile { url } } pageInfo{ hasNextPage endCursor } } }''',
                   {'c': cursor})['files']
        for n in r['nodes']:
            url = (n.get('image') or {}).get('url') or n.get('url') or ''
            names.add(url.split('/')[-1].split('?')[0])
        if not r['pageInfo']['hasNextPage']:
            return names
        cursor = r['pageInfo']['endCursor']


def delete_card_files(card, names=None):
    """names = tylko te pliki (podmiana części kolorów; reszta karty zostaje ze starymi obrazkami)."""
    pref = f'kolor-{slug(card)}-'
    r = si.gql('''query($q:String){ files(first:250, query:$q){ nodes{ id ... on MediaImage { image{ url } } } } }''',
               {'q': f'filename:{pref}*'})['files']['nodes']
    ids = [n['id'] for n in r if pref in ((n.get('image') or {}).get('url') or '')
           and (names is None or ((n.get('image') or {}).get('url') or '').split('/')[-1].split('?')[0] in names)]
    for i in range(0, len(ids), 50):
        si.gql('''mutation($ids:[ID!]!){ fileDelete(fileIds:$ids){ userErrors{ message } } }''', {'ids': ids[i:i + 50]})
    return ids


def upload_card(card, colors, crops, have, folder):
    if REPLACE and not DRY:
        gone = delete_card_files(card, {f'kolor-{slug(card)}-{handleize(c)}.jpg' for c in colors})
        have = set()
        if gone:
            print(f'  {card}: usunięto {len(gone)} starych kółek')
            time.sleep(3)
    todo = []
    for c in colors:
        fn = f'kolor-{slug(card)}-{handleize(c)}.jpg'
        if fn in have:
            continue
        if DRY:
            todo.append(fn)
            continue
        src = os.path.join(crops, folder, c + '.jpg')
        tmp = os.path.join('/tmp' if not os.environ.get('TMPDIR') else os.environ['TMPDIR'], fn)
        with open(src, 'rb') as a, open(tmp, 'wb') as b:
            b.write(a.read())
        todo.append({'originalSource': si.staged_upload(tmp), 'contentType': 'IMAGE', 'filename': fn,
                     'alt': f'Kolor {c}'})
        os.remove(tmp)
    if DRY or not todo:
        return len(todo)
    for i in range(0, len(todo), 25):
        r = si.gql('''mutation($f:[FileCreateInput!]!){ fileCreate(files:$f){ userErrors{ field message } } }''',
                   {'f': todo[i:i + 25]})
        if r['fileCreate']['userErrors']:
            print('  BŁĄD plików', card, r['fileCreate']['userErrors'])
    return len(todo)


def product(code):
    r = si.gql('''query($q:String){ products(first:5, query:$q){ nodes{ id title options{ name }
        variants(first:2){ nodes{ id sku price inventoryItem{ id } } } } } }''', {'q': f'sku:{code}'})
    hits = [p for p in r['products']['nodes'] if any(v['sku'] == code for v in p['variants']['nodes'])]
    return hits[0] if hits else None


def add_variants(code, card, colors):
    p = product(code)
    if not p:
        return 'brak produktu'
    if any(o['name'] == 'Kolor' for o in p['options']):
        return 'ma już Kolor'
    price = p['variants']['nodes'][0]['price']
    if DRY:
        return f'{len(colors)} kolorów (dry-run)'
    r = si.gql('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''',
               {'m': [{'ownerId': p['id'], 'namespace': 'custom', 'key': 'kolornik',
                       'type': 'single_line_text_field', 'value': slug(card)}]})
    if r['metafieldsSet']['userErrors']:
        return f"metapole: {r['metafieldsSet']['userErrors']}"
    r = si.gql('''mutation($pid:ID!, $o:[OptionCreateInput!]!){ productOptionsCreate(productId:$pid, options:$o,
        variantStrategy:CREATE){ product{ variants(first:250){ nodes{ id selectedOptions{ value } } } }
        userErrors{ field message code } } }''',
               {'pid': p['id'], 'o': [{'name': 'Kolor', 'values': [{'name': c} for c in colors]}]})
    res = r['productOptionsCreate']
    if res['userErrors']:
        return f"opcja: {res['userErrors']}"
    upd = []
    for v in res['product']['variants']['nodes']:
        c = v['selectedOptions'][0]['value']
        upd.append({'id': v['id'], 'price': price,
                    'inventoryItem': {'sku': f"{code}-{c.replace(' ', '')}", 'tracked': False,
                                      'measurement': {'weight': {'value': 110, 'unit': 'GRAMS'}}},
                    'inventoryPolicy': 'CONTINUE'})
    for i in range(0, len(upd), 100):
        r = si.gql('''mutation($pid:ID!, $v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid,
            variants:$v){ userErrors{ field message } } }''', {'pid': p['id'], 'v': upd[i:i + 100]})
        if r['productVariantsBulkUpdate']['userErrors']:
            return f"warianty: {r['productVariantsBulkUpdate']['userErrors'][:2]}"
    return f'{len(colors)} kolorów'


def main():
    crops = [a for a in sys.argv[1:] if not a.startswith('--')][0]
    mapa = json.load(open(os.path.join(HERE, 'mapa.json')))
    manifest = json.load(open(os.path.join(crops, 'manifest.json')))
    have = set() if DRY and not os.environ.get('CHECK_FILES') else existing_files()
    uploaded = set()
    done = 0
    for code, card in mapa.items():
        if ONLY and code not in ONLY or not card or card == '?' or card in SKIP:
            continue
        # lokalne foldery (zip z Drive) mają „_” zamiast „%”
        colors = sorted(manifest.get(card) or manifest.get(card.replace('%', '_'), {}), key=natural)
        crops_card = card if card in manifest else card.replace('%', '_')
        if not colors or not os.path.isdir(os.path.join(crops, crops_card)):  # manifest z pełnego przebiegu, folder pominięty
            print(f'{code:14} {card}: brak wyciętych próbek')
            continue
        if card not in uploaded:
            n = upload_card(card, colors, crops, have, crops_card)
            uploaded.add(card)
            if n:
                print(f'  {card}: {n} kółek do Plików')
                if not DRY:
                    time.sleep(2)
        if UPLOAD_ONLY:
            continue
        print(f'{code:14} {card}: {add_variants(code, card, colors)}', flush=True)
        done += 1
        if LIMIT and done >= LIMIT:
            break


if __name__ == '__main__':
    main()
