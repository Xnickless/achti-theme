"""Plik importu Europages (cała oferta) z eksportu docs/marketplace/achti-products-en.csv.

Szablon: europages.pl → Moja firma → Produkty i usługi → Import → „Szablon Excel”
(/product-editor-frontend/bulk-import/excel-template-en.xlsx). Maks. 500 pozycji w jednym imporcie.
Cena = minimalna cena („od”) w EUR, bez narzutu (Europages nie bierze prowizji).

  python3 tools/export_europages.py SZABLON.xlsx [--eur=4.403]
Wynik: docs/marketplace/europages-import.xlsx
"""
import sys, os, csv, re
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'docs/marketplace/achti-products-en.csv')
OUT = os.path.join(ROOT, 'docs/marketplace/europages-import.xlsx')


def keywords(r):
    head = r['Category'].startswith('Knitted headband')
    g = {'Women': "women's", 'Men': "men's", 'Kids': "kids'", 'Unisex': 'unisex'}[r['Gender']]
    k = (['knitted headband', 'winter headband', f'{g} headband', 'ear warmer'] if head else
         ['winter hat', 'beanie', 'knitted hat', f'{g} beanie'])
    if r['Pom-pom'] == 'Yes': k.append('pom-pom hat')
    if 'merino' in r['Material'].lower(): k += ['merino wool hat', 'merino beanie']
    elif 'wool' in r['Material'].lower(): k.append('wool hat')
    if 'fleece' in r['Lining'].lower(): k.append('fleece lined headband' if head else 'fleece lined hat')
    k += ['wholesale hats', 'hat manufacturer', 'made in Poland', 'private label hats']
    return ', '.join(dict.fromkeys(k[:15]))


def description(r):
    body = re.sub(r'(?<=\S)(Code|Composition|Lining|Size|Season|Material|Pom-pom):', r'\n\1:', r['Full description'].strip())
    body = re.sub(r'Specification:\n+', 'Specification:\n', body)
    parts = [body,
             f"Colours: {r['Colours (count)']} variants" + (f" ({r['Colours']})" if r['Colours'] and len(r['Colours']) < 400 else ''), '',
             'Wholesale only (B2B). Prices net, ex works Poland. Minimum order 2 pcs per colour, '
             'minimum order value 470 EUR. Volume discounts from 500 pcs. Lead time 7-14 working days.',
             'Custom logo (embroidery or patch) and private label from 100 pcs.',
             'Manufacturer: Achti, Poland - over 30 years of knitwear production.']
    return '\n'.join(p for p in parts if p is not None).replace('\n\n\n', '\n\n')


def main():
    tpl = sys.argv[1]
    eur = float(next((a.split('=')[1] for a in sys.argv if a.startswith('--eur=')), 4.403))
    rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))
    wb = openpyxl.load_workbook(tpl)
    ws = wb['Template']
    head = [c.value for c in ws[2]]
    col = {h: i + 1 for i, h in enumerate(head)}
    for i, r in enumerate(rows):
        n = 3 + i
        vals = {
            'Product Title': f"{r['Product name']} - knitted winter {'headband' if 'headband' in r['Category'] else 'hat'}, made in Poland ({r['SKU']})",
            'Description': description(r),
            'Keyword(s)': keywords(r),
            'Image URL 1': r['Main image URL'], 'Image Caption 1': r['Product name'],
            'Image URL 2': r['Lifestyle image URL'], 'Image Caption 2': r['Product name'] + ' - lifestyle' if r['Lifestyle image URL'] else None,
            'Image URL 3': None, 'Image Caption 3': None,
            'Website link': r['Product page'],
            'Fixed Price': None,
            'Minimum Price': round(float(r['Price PLN net']) / eur, 2),
            'Maximum Price': None,
            'Currency': 'EUR',
            'Minimum Order Quantity': 2,
            'Unit': 'Piece',
            'Help column': True,
        }
        for h, v in vals.items():
            ws.cell(n, col[h]).value = v
    for n in range(3 + len(rows), ws.max_row + 1):  # puste wiersze szablonu z formułami
        for c in range(1, ws.max_column + 1):
            ws.cell(n, c).value = None
    wb.save(OUT)
    print(len(rows), 'produktów →', OUT, '| najdłuższy opis', max(len(description(r)) for r in rows),
          '| najdłuższy tytuł', max(len(ws.cell(3 + i, 1).value) for i in range(len(rows))))


if __name__ == '__main__':
    main()
