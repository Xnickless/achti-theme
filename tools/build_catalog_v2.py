#!/usr/bin/env python3
"""Buduje nowy arkusz katalogu (v2) w układzie kolumn z arkusza klienta (achti-katalog-do-uzupelnienia (1).xlsx)
na podstawie zdjęć z folderu „WYBRANE NA PLATFORME B2B Full Size”. Przenosi wartości, które klient już wpisał
(po kodzie), i dokłada kolumnę waga_g. Wynik: ~/Downloads/achti-katalog-v2.csv (+ .xlsx) i raport różnic."""
import os, re, csv, json, collections
import openpyxl

HOME = os.path.expanduser('~')
PHOTOS = os.path.join(HOME, 'Downloads/achti-fullsize/WYBRANE NA PLATFORME B2B Full Size')
XLSX = os.path.join(HOME, 'Downloads/achti-katalog-do-uzupelnienia (1).xlsx')
OLD_CSV = os.path.join(HOME, 'Downloads/achti-katalog-do-uzupelnienia.csv')
OUT_CSV = os.path.join(HOME, 'Downloads/achti-katalog-v2.csv')
OUT_XLSX = os.path.join(HOME, 'Downloads/achti-katalog-v2.xlsx')
OUT_JSON = os.path.join(os.path.dirname(__file__), 'katalog-v2.json')

COLUMNS = ['kod', 'typ', 'material', 'rozmiar', 'Cena netto', 'Płeć', 'plik', 'nazwa_produktu',
           'kolory (po przecinku)', 'cena promocyjna', 'opis', 'tagi (damskie/meskie/dzieci/premium/nowosc)', 'waga_g']
FLAGS = {'BOY', 'GIRL', 'CEKIN', 'CEKINY', 'MULTI', 'KOMIN', 'BEZ', 'POM'}
NOISE = {'SIZE', 'ROZ', 'ROZ.'}
MAT_FIX = {'AMIOSOFT': 'AMICOSOFT', 'TURBI': 'TURBO'}

def parse_name(fname):
    base = re.sub(r'\.jpe?g$', '', fname, flags=re.I)
    m = re.match(r'^(AZ-\d+[A-Z0-9]*)\s*(.*)$', base, re.I)
    code, rest = m.group(1).upper(), m.group(2)
    size = None
    ms = re.search(r'(ONE SIZE|ROZ\.?\s*(\d+\s*-\s*\d+)|\b(\d{2})\s*-\s*(\d{2})\b|(\d+X\d+))', rest, re.I)
    if ms:
        if ms.group(1).upper() == 'ONE SIZE': size = 'One Size'
        elif ms.group(2): size = re.sub(r'\s', '', ms.group(2))
        elif ms.group(3): size = f'{ms.group(3)}-{ms.group(4)}'
        else: size = ms.group(5).upper()
        rest = rest[:ms.start()] + ' ' + rest[ms.end():]
    mg = re.search(r'\bG(\d+)\b', rest)
    group = f'G{mg.group(1)}' if mg else None
    if mg: rest = rest[:mg.start()] + ' ' + rest[mg.end():]
    toks = [t for t in re.split(r'[\s+]+', rest) if t and t not in '()' and not re.fullmatch(r'\(\d+\)', t) and t.upper() not in NOISE]
    flags = [t.upper() for t in toks if t.upper() in FLAGS]
    mats = []
    for t in toks:
        u = MAT_FIX.get(t.upper(), t.upper())
        if u in FLAGS: continue
        if u == '90.10' and mats: mats[-1] += ' 90/10'; continue
        if u not in mats: mats.append(u)
    if 'BEZ' in flags and 'POM' in flags:
        flags = [f for f in flags if f not in ('BEZ', 'POM')] + ['BEZ POMPONA']
    return dict(code=code, size=size, group=group, flags=flags, materials=mats)

def main():
    wb = openpyxl.load_workbook(XLSX, data_only=True); ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True)); hdr = [str(h).strip() for h in rows[0]]
    client = {}
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        if d.get('kod'): client[str(d['kod']).strip().upper()] = d
    old_codes = {r['kod'].strip().upper() for r in csv.DictReader(open(OLD_CSV, encoding='utf-8-sig'), delimiter=';')}

    files = sorted(f for f in os.listdir(PHOTOS) if f.lower().endswith('.jpg'))
    out, report = [], collections.defaultdict(list)
    seen = collections.Counter()
    for f in files:
        p = parse_name(f)
        seen[p['code']] += 1
        c = client.get(p['code']) or client.get(p['code'].rstrip('1')) or {}
        if c and c.get('kod') and str(c['kod']).strip().upper() != p['code']:
            report['kod zmieniony (dopasowano do starego)'].append(f"{c['kod']} -> {p['code']}")
        is_snood = 'KOMIN' in p['flags'] or (p['size'] and 'X' in p['size'])
        kids = any(x in p['flags'] for x in ('BOY', 'GIRL')) or (p['size'] and re.fullmatch(r'\d{2}-\d{2}', p['size']) and int(p['size'][:2]) < 56)
        mat_client = c.get('material')
        material = str(mat_client).strip() if mat_client and '%' in str(mat_client) else ' + '.join(p['materials'])
        cena = c.get('Cena netto')
        if isinstance(cena, (int, float)): cena_v = cena
        else: cena_v = p['group'] or ''
        plec = str(c.get('Płeć') or '').strip()  # uzupełnia klient
        if not p['size']: report['brak rozmiaru w nazwie pliku'].append(f)
        if not p['group'] and not isinstance(cena, (int, float)): report['brak grupy cenowej w nazwie pliku'].append(f)
        row = {
            'kod': p['code'], 'typ': 'Komin' if is_snood else 'Czapka', 'material': material,
            'rozmiar': p['size'] or (str(c.get('rozmiar') or '').strip()), 'Cena netto': cena_v, 'Płeć': plec, 'plik': f,
            'nazwa_produktu': c.get('nazwa_produktu') or '', 'kolory (po przecinku)': c.get('kolory (po przecinku)') or '',
            'cena promocyjna': c.get('cena promocyjna') or '', 'opis': c.get('opis') or '',
            'tagi (damskie/meskie/dzieci/premium/nowosc)': c.get('tagi (damskie/meskie/dzieci/premium/nowosc)') or '',
            'waga_g': '', '_flags': p['flags'], '_group': p['group'], '_materials': p['materials'],
        }
        out.append(row)
    SUFFIX = {'TURBO': 'TURBO', 'BOY': 'BOY', 'GIRL': 'GIRL', 'BEZ POMPONA': 'BP'}
    for code, n in seen.items():
        if n > 1:
            dup = [r for r in out if r['kod'] == code]
            report['ten sam kod na kilku zdjęciach → osobne produkty'].append(f"{code} ({n}): " + ', '.join(r['plik'] for r in dup))
            # wariant „bazowy” (bez flagi różnicującej) zachowuje kod, pozostałe dostają sufiks
            common = set.intersection(*[set(r['_materials']) for r in dup])
            for r in dup:
                extra = [f for f in r['_flags'] if f in SUFFIX] + [m for m in r['_materials'] if m not in common and m in SUFFIX]
                if extra:
                    r['kod'] = code + '-' + '-'.join(SUFFIX[f] for f in extra)
                    r['_base_code'] = code
            if all(r['kod'] == code for r in dup):  # np. BOY vs GIRL: obie mają flagę
                pass
            report['nowe kody wariantów'] += [r['kod'] for r in dup if r['kod'] != code]
    new_codes = set(seen)
    report['usuwane ze sklepu (brak w Full Size)'] = sorted(old_codes - new_codes)
    report['nowe kody (nie było w sklepie)'] = sorted(new_codes - old_codes)

    with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, delimiter=';', extrasaction='ignore')
        w.writeheader(); [w.writerow(r) for r in out]
    wb2 = openpyxl.Workbook(); ws2 = wb2.active; ws2.title = 'katalog v2'
    ws2.append(COLUMNS)
    for r in out: ws2.append([r[c] for c in COLUMNS])
    for col, width in zip('ABCDEFGHIJKLM', (13, 8, 24, 10, 11, 9, 40, 22, 30, 14, 40, 26, 8)):
        ws2.column_dimensions[col].width = width
    ws2.freeze_panes = 'A2'
    wb2.save(OUT_XLSX)
    json.dump(out, open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'wierszy: {len(out)}, kodów: {len(seen)}')
    for k, v in report.items():
        print(f'\n## {k} ({len(v)})'); [print('  ', x) for x in v]

if __name__ == '__main__':
    main()
