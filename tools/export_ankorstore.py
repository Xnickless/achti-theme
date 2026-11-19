"""Arkusz produktów na Ankorstore / Faire — wiersz na każdy kolor (wariant), po angielsku.

Decyzja Adriana 16.11.2026: cena hurtowa = cena B2B +10%, sugerowana detaliczna = hurtowa x 2,2.
Kreator importu Ankorstore dopasowuje kolumny sam (Products → Import a spreadsheet).

  python3 tools/export_ankorstore.py [--codes=AZ-3102PC,AZ-2344PC] [--markup=1.10] [--retail=2.2] [--eur=4.25]
Wynik: docs/marketplace/ankorstore-<n>.csv i .xlsx
"""
import sys, os, json, csv, re
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
from export_marketplace import text, LINING, ROOT, OUT, SITE
from colorcards.set_warianty import handleize

TEST15 = ['AZ-3102PC', 'AZ-3101PC', 'AZ-2344PC', 'AZ-1748PC', 'AZ-2656PC', 'AZ-2836PC', 'AZ-2911PC',
          'AZ-2910PC', 'AZ-2934', 'AZ-2928', 'AZ-2937', 'AZ-2541PK', 'AZ-2555PK', 'AZ-2349PC', 'AZ-2712PC']

Q = '''query($q:String){ products(first:10, query:$q){ nodes{ handle tags productType status
  metafield(namespace:"custom", key:"kolornik"){ value }
  variants(first:250){ nodes{ sku price selectedOptions{ name value } } }
  media(first:2){ nodes{ ... on MediaImage{ image{ url } } } } } } }'''


def opts():
    return dict(x[2:].split('=', 1) for x in sys.argv[1:] if x.startswith('--') and '=' in x)


def swatch_urls():
    out, c = {}, None
    while True:
        r = si.gql('''query($c:String){ files(first:250, after:$c, query:"filename:kolor-"){ nodes{
            ... on MediaImage { image{ url } } } pageInfo{ hasNextPage endCursor } } }''', {'c': c})['files']
        for n in r['nodes']:
            u = (n.get('image') or {}).get('url') or ''
            if u: out[u.split('/')[-1].split('?')[0]] = u.split('?')[0]
        if not r['pageInfo']['hasNextPage']:
            return out
        c = r['pageInfo']['endCursor']


def main():
    o = opts()
    codes = o['codes'].split(',') if 'codes' in o else TEST15
    markup, retail = float(o.get('markup', 1.10)), float(o.get('retail', 2.2))
    if 'eur' in o:
        eur = float(o['eur'])
    else:
        import urllib.request
        eur = 1 / json.load(urllib.request.urlopen('https://api.frankfurter.app/latest?from=PLN&to=EUR', timeout=20))['rates']['EUR']
    en = json.load(open(os.path.join(ROOT, 'tools/translations/en.json')))['products']
    local = {x['code']: x for x in json.load(open(os.path.join(ROOT, 'tools/achti-produkty.json')))}
    have = swatch_urls()
    rows, missing_img = [], 0
    for code in codes:
        cand = si.gql(Q, {'q': f'sku:{code}*'})['products']['nodes']
        own = lambda c: max((k for k in en if any(v['sku'] == k or v['sku'].startswith(k + '-')
                                                  for v in c['variants']['nodes'][:1])), key=len, default='')
        p = next((c for c in cand if own(c) == code), None)
        if not p:  # wyszukiwarka Admin API bywa chwilowo niepełna — druga próba
            cand = si.gql(Q, {'q': f'sku:{code}*'})['products']['nodes']
            p = next((c for c in cand if own(c) == code), None)
        if not p:
            print('brak produktu', code); continue
        t, loc = en.get(code) or {}, local.get(code) or {}
        meta = t.get('metafields') or {}
        body = text(t.get('body_html', ''))
        imgs = [m['image']['url'] for m in p['media']['nodes'] if m.get('image')]
        card = (p['metafield'] or {}).get('value')
        headband = p['productType'] == 'Opaska'
        for v in p['variants']['nodes']:
            colour = next((s['value'] for s in v['selectedOptions'] if s['name'] == 'Kolor'), '')
            sw = f'kolor-{card}-{handleize(colour)}.jpg' if card and colour else ''
            if sw and sw not in have:
                missing_img += 1; sw = ''
            whole = round(float(v['price']) * markup / eur, 2)
            rows.append({
                'Product name': t.get('title', ''),
                'Product reference': code,
                'Variant SKU': v['sku'],
                'Colour': colour or 'One colour',
                'Wholesale price EUR': f'{whole:.2f}',
                'Retail price EUR': f'{whole * retail:.2f}',
                'Description': body,
                'Category': 'Headbands' if headband else 'Beanies',
                'Composition': meta.get('custom.sklad', ''),
                'Lining': LINING.get(loc.get('podszycie', ''), ''),
                'Size': meta.get('custom.rozmiar', 'One Size'),
                'VAT rate %': 23,
                'Made in': 'PL',  # Ankorstore: kod kraju ISO (2 znaki)
                'HS code': '61178080' if headband else '65050090',  # CN, same cyfry (spacja = błąd formatu)
                'Unit weight (g)': 110,
                'Minimum per colour (pcs)': 2,
                'Lead time': '7-14 working days (made to order)',
                'Main image URL': imgs[0] if imgs else '',
                'Lifestyle image URL': imgs[1] if len(imgs) > 1 else '',
                'Colour swatch image URL': have.get(sw, ''),
                'Product page': SITE + p['handle'],
            })
    os.makedirs(OUT, exist_ok=True)
    name = os.path.join(OUT, 'ankorstore-cala-oferta' if len(codes) > 100 else f'ankorstore-{len(codes)}')
    cols = list(rows[0])
    with open(name + '.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Products'
    ws.append(cols)
    for r in rows: ws.append([r[c] for c in cols])
    ws.freeze_panes = 'D2'
    wb.save(name + '.xlsx')
    print(len(codes), 'modeli,', len(rows), 'wariantów, kurs EUR', round(eur, 4), '| bez zdjęcia koloru:', missing_img)


if __name__ == '__main__':
    main()
