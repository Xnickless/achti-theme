"""Eksport oferty do platform B2B (Alibaba, Europages, inne) — jeden arkusz po angielsku.

Dane: Admin API (zdjęcia, cena, warianty, tagi, handle) + tłumaczenia EN z tools/translations/en.json
+ podszycie z tools/achti-produkty.json. Wynik: docs/marketplace/achti-products-en.csv i .xlsx.
Kolumny są uniwersalne; szablony Alibaby/Europages pobiera się z ich paneli i mapuje te kolumny.

  python3 tools/export_marketplace.py [--eur=4.25 --usd=3.70]   (kursy PLN; domyślnie z EBC)
"""
import sys, json, re, csv, html, urllib.request, os
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'marketplace')
SITE = 'https://b2b.achti.com/en/products/'

LINING = {
    'Pełne podszycie polarowe 100% poliester': 'Full fleece lining (100% polyester)',
    'Opaska polarowa 100% poliester': 'Fleece-lined band (100% polyester)',
    'Bez podszycia': 'No lining',
    'Podwójna dzianina': 'Double-layer knit',
}

def args():
    a = dict(x[2:].split('=', 1) for x in sys.argv[1:] if x.startswith('--') and '=' in x)
    return a

def rates(a):
    if 'eur' in a and 'usd' in a:
        return float(a['eur']), float(a['usd']), 'manual'
    r = json.load(urllib.request.urlopen('https://api.frankfurter.app/latest?from=PLN&to=EUR,USD', timeout=20))
    return 1 / r['rates']['EUR'], 1 / r['rates']['USD'], r['date']

def text(h):
    h = re.sub(r'<br\s*/?>', '\n', h or '')
    h = re.sub(r'</p>\s*', '\n\n', h)
    return html.unescape(re.sub(r'<[^>]+>', '', h)).strip()

Q = '''query($c:String){ products(first:100, after:$c){ pageInfo{hasNextPage endCursor}
  nodes{ handle tags productType status
    options{ name values }
    variants(first:1){ nodes{ sku price } }
    media(first:6){ nodes{ ... on MediaImage{ image{ url altText } } } } } } }'''

def fetch():
    out, c = [], None
    while True:
        r = si.gql(Q, {'c': c})['products']
        out += r['nodes']
        if not r['pageInfo']['hasNextPage']:
            return out
        c = r['pageInfo']['endCursor']

def main():
    a = args()
    eur, usd, rdate = rates(a)
    en = json.load(open(os.path.join(ROOT, 'tools/translations/en.json')))['products']
    local = {x['code']: x for x in json.load(open(os.path.join(ROOT, 'tools/achti-produkty.json')))}
    rows = []
    for p in fetch():
        if p['status'] != 'ACTIVE':
            continue
        v = p['variants']['nodes'][0]
        sku = v['sku'] or ''
        code = max((k for k in en if sku == k or sku.startswith(k + '-')), key=len, default=sku)
        t = en.get(code) or {}
        loc = local.get(code) or {}
        tags = set(p['tags'])
        headband = p['productType'] == 'Opaska'
        if 'dzieci' in tags: gender = 'Kids'
        elif 'damskie' in tags and 'meskie' in tags: gender = 'Unisex'
        elif 'meskie' in tags: gender = 'Men'
        else: gender = 'Women'
        colours = []
        for o in p['options']:
            if o['name'] == 'Kolor':
                colours = o['values']
        imgs = [m['image']['url'] for m in p['media']['nodes'] if m.get('image')]
        body = text(t.get('body_html', ''))
        short = body.split('\n')[0].strip()
        price = float(v['price'])
        meta = t.get('metafields') or {}
        rows.append({
            'SKU': code,
            'Product name': t.get('title', ''),
            'Brand': 'Achti',
            'Category': 'Knitted headband' if headband else 'Knitted winter hat (beanie)',
            'Gender': gender,
            'Material': meta.get('custom.sklad', ''),
            'Lining': LINING.get(loc.get('podszycie', ''), ''),
            'Pom-pom': '' if headband else ('Yes' if 'pompon' in tags else 'No'),
            'Size': meta.get('custom.rozmiar', 'One Size'),
            'Colours (count)': len(colours) or 1,
            'Colours': ', '.join(colours),
            'Short description': short,
            'Full description': body,
            'Main image URL': imgs[0] if imgs else '',
            'Lifestyle image URL': imgs[1] if len(imgs) > 1 else '',
            'Unit weight (g)': 110,
            'Price PLN net': f'{price:.2f}',
            'Price EUR net (approx.)': f'{price / eur:.2f}',
            'Price USD (approx.)': f'{price / usd:.2f}',
            'MOQ per colour (pcs)': 2,
            'Minimum order value': '2000 PLN / 470 EUR / 550 USD net',
            'Lead time': '7-14 working days',
            'HS code (to confirm)': '6117 80' if headband else '6505 00',
            'Country of origin': 'Poland',
            'Custom logo / private label': 'Yes - embroidery or patch from 100 pcs',
            'Product page': SITE + p['handle'],
        })
    rows.sort(key=lambda r: r['SKU'])
    os.makedirs(OUT, exist_ok=True)
    cols = list(rows[0])
    with open(os.path.join(OUT, 'achti-products-en.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    try:
        import openpyxl
        from openpyxl.styles import Font
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Products'
        ws.append(cols)
        for c in ws[1]: c.font = Font(bold=True)
        for r in rows: ws.append([r[c] for c in cols])
        ws.freeze_panes = 'C2'
        for i, c in enumerate(cols, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = 60 if 'description' in c.lower() or c == 'Colours' else 22
        ws2 = wb.create_sheet('Info')
        for line in [f'Exchange rates (PLN per unit): EUR {eur:.4f}, USD {usd:.4f} ({rdate})',
                     'Prices are net, ex works Poland. Volume discounts from 500 pcs (1-10%).',
                     'HS codes to be confirmed with the customs agent.']:
            ws2.append([line])
        wb.save(os.path.join(OUT, 'achti-products-en.xlsx'))
    except ImportError:
        print('brak openpyxl — tylko CSV')
    print(len(rows), 'produktów; kursy', round(eur, 4), round(usd, 4), rdate)

if __name__ == '__main__':
    main()
