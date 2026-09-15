"""Wstawia do arkusza Adriana (achti-katalog-v2.xlsx) aktualne nazwy modeli ze sklepu.
Bez tego kolejny przebieg apply_catalog_v2.py przywróciłby stare imiona.
  python3 tools/aktualizuj_arkusz.py [--in=plik.xlsx] [--out=plik.xlsx]
Zmienione komórki są podświetlone na żółto. Uruchamiać pythonem z openpyxl."""
import openpyxl, json, re, os, sys
from openpyxl.styles import PatternFill, Font

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = next((a[5:] for a in sys.argv if a.startswith('--in=')), os.path.join(HERE, 'achti-katalog-v2-drive.xlsx'))
OUT = next((a[6:] for a in sys.argv if a.startswith('--out=')), os.path.expanduser('~/Downloads/achti-katalog-v3.xlsx'))

sklep = {p['code'].upper(): p.get('name') for p in json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))}
wb = openpyxl.load_workbook(SRC); ws = wb.active
H = {c.value: i + 1 for i, c in enumerate(ws[1])}
kod_col, plik_col, nazwa_col = H.get('∂'), H['plik'], H['nazwa_produktu']

def kody(row):
    """Kandydaci na SKU: z kolumny kodu i z nazwy pliku, z sufiksami wariantów i bez."""
    out = []
    for col in (kod_col, plik_col):
        if not col: continue
        v = str(ws.cell(row, col).value or '').upper()
        m = re.match(r'(AZ-[0-9]+[A-Z0-9]*)', v)
        if not m: continue
        k = m.group(1)
        plik = str(ws.cell(row, plik_col).value or '').upper()
        sfx = ('-BP' if 'BEZ POM' in plik else '-TURBO' if 'TURBO' in plik
               else '-BOY' if re.search(r'\bBOY\b', plik) else '-GIRL' if re.search(r'\bGIRL\b', plik) else '')
        # wariant z sufiksem ma pierwszeństwo, ale tylko jeśli taki SKU istnieje
        out += [k + sfx, k, k + 'PC', k + 'LPC', re.sub(r'PC$', '', k)]
    return [k for k in dict.fromkeys(out) if k]

zmian, brak, zolty = 0, [], PatternFill('solid', fgColor='FFF3CD')
for r in range(2, ws.max_row + 1):
    sku = next((k for k in kody(r) if k in sklep), None)
    if not sku: brak.append(f'wiersz {r}'); continue
    nowa = sklep[sku]
    if ws.cell(r, nazwa_col).value != nowa:
        ws.cell(r, nazwa_col).value = nowa
        ws.cell(r, nazwa_col).fill = zolty
        zmian += 1
ws.cell(1, nazwa_col).font = Font(bold=True)
wb.save(OUT)

# kontrola: każdy wiersz musi mieć nazwę zgodną ze sklepem
wb2 = openpyxl.load_workbook(OUT); ws2 = wb2.active
zle = [r for r in range(2, ws2.max_row + 1)
       if (sku := next((k for k in kody(r) if k in sklep), None)) and sklep[sku] != ws2.cell(r, nazwa_col).value]
print(f'zmienione: {zmian} | wiersze bez dopasowania: {brak or "brak"} | niezgodne po zapisie: {zle or "brak"}')
print('zapisano:', OUT, f'({os.path.getsize(OUT)} B)')
