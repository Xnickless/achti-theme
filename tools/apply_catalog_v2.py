#!/usr/bin/env python3
"""Nanosi na sklep dane z arkusza Adriana „achti-katalog-v2.xlsx” (Google Drive, folder WORKSPACE ACHTI x KAMIL DZIEDZIC).
Kolumny arkusza: kod, typ (Czapka zimowa / Opaska zimowa), podszycie, material (skład surowcowy), rozmiar, Cena netto, Płeć,
plik, nazwa_produktu, kolory (po przecinku), cena promocyjna, opis, tagi, waga_g.

Co robi (dopasowanie po SKU = kod):
- typ „Opaska zimowa” -> tytuł „Opaska Zimowa Damska <miasto>”, productType Opaska, tag `opaski`, opis wg szablonu opaski;
- material ze znakiem % -> metapole custom.sklad (zakładka „Skład”) + wiersz „Skład” w opisie;
- podszycie -> zdanie w opisie, cecha w liście i wiersz „Podszycie” w specyfikacji;
- rozmiar -> metapole custom.rozmiar (gdy inny);
- Cena netto (liczba) -> cena wariantu, usunięcie tagu `cena-do-uzupelnienia`;
- cena promocyjna (liczba) -> compareAtPrice = cena netto, cena = promocyjna;
- Płeć „Unisex” -> dodatkowo tag `meskie`; waga_g -> waga wariantu (gramy);
- nazwa_produktu / kolory NIE są nanoszone automatycznie (wpisy w arkuszu wyglądają na testowe) — skrypt je tylko wypisuje.
Aktualizuje też tools/achti-produkty.json (tytuł, opis, sklad, podszycie, typ, cena), z którego translate_catalog.py generuje EN/FR/DE.

Użycie: python3 tools/apply_catalog_v2.py --xlsx=~/Downloads/achti-katalog-v2.xlsx [--dry-run] [--codes=AZ-1,AZ-2]
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
import sync_catalog_v2 as sc  # build_text, slug
import openpyxl

HERE = os.path.dirname(__file__)
DRY = '--dry-run' in sys.argv
XLSX = next((os.path.expanduser(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--xlsx=')), os.path.join(HERE, 'achti-katalog-v2-drive.xlsx'))
CODES = next((set(a.split('=', 1)[1].split(',')) for a in sys.argv if a.startswith('--codes=')), None)
OLD_PATH = os.path.join(HERE, 'achti-produkty.json')
RX = re.compile(r'^(Czapka Zimowa (Damska|Dziecięca|Chłopięca|Dziewczęca) Beanie|Komin Zimowy Damski|Opaska Zimowa Damska) (\S+(?: \S+)*?)( z Cekinami)?( Multikolor)?(?: \((Turbo|bez pompona)\))?$')
PRICE_TAG = 'cena-do-uzupelnienia'

def rt_text(value):
    """Tekst z metapola rich_text (JSON) albo zwykłej wartości."""
    if not value: return ''
    try:
        d = json.loads(value)
        out = []
        def walk(n):
            if isinstance(n, dict):
                if n.get('type') == 'text': out.append(n.get('value', ''))
                for c in n.get('children', []): walk(c)
        walk(d); return ''.join(out).strip()
    except Exception:
        return str(value).strip()

def num(v):
    if v is None or v == '': return None
    if isinstance(v, (int, float)): return float(v)
    s = str(v).strip().replace(',', '.').replace(' ', '')
    try: return float(s)
    except ValueError: return None

def read_rows():
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True)); hdr = [str(h).strip() if h else '' for h in rows[0]]
    out = {}
    for r in rows[1:]:
        d = {k: (v.strip() if isinstance(v, str) else v) for k, v in zip(hdr, r)}
        if d.get('kod'): out[str(d['kod']).strip().upper()] = d
    return out

def fetch_shop():
    out, cursor = {}, None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title tags productType
            variants(first:1){ nodes{ id sku price compareAtPrice inventoryItem{ id measurement{ weight{ value unit } } } } }
            metafields(first:10, namespace:"custom"){ nodes{ id key type value } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            v = p['variants']['nodes'][0]
            out[(v['sku'] or '').upper()] = dict(id=p['id'], title=p['title'], tags=p['tags'], type=p['productType'], variant_id=v['id'], price=v['price'],
                                                 compare=v['compareAtPrice'], weight=(v['inventoryItem']['measurement']['weight'] or {}).get('value'),
                                                 mf={m['key']: m for m in p['metafields']['nodes']})
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return out

def mut(query, variables, label):
    if DRY: return {}
    r = si.gql(query, variables)
    key = next(iter(r)); errs = r[key].get('userErrors')
    if errs: print('   BŁĄD', label, errs)
    return r

def main():
    rows = read_rows()
    shop = fetch_shop()
    defs = si.metafield_defs()
    old = json.load(open(OLD_PATH, encoding='utf-8')); old_by = {o['code'].upper(): o for o in old}
    stats = dict(cena=0, promo=0, sklad=0, podszycie=0, opaska=0, rozmiar=0, unisex=0, waga=0, tytul_opis=0, brak=0, pominiete=0)
    notes = []
    for code, r in rows.items():
        if CODES and code not in CODES: continue
        p = shop.get(code)
        if not p:
            stats['brak'] += 1; notes.append(f'brak w sklepie: {code}'); continue
        m = RX.match(p['title'])
        if not m:
            stats['pominiete'] += 1; notes.append(f'tytuł poza szablonem, pominięty: {code} „{p["title"]}”'); continue
        segword = m.group(2) or 'Damska'; city = m.group(3)
        flags = []
        if m.group(4): flags.append('CEKIN')
        if m.group(5): flags.append('MULTI')
        if m.group(6) == 'bez pompona': flags.append('BEZ POMPONA')
        is_komin = m.group(1).startswith('Komin')
        is_opaska = str(r.get('typ') or '').lower().startswith('opaska')
        o = old_by.get(code, {})
        mats = o.get('materials') or []
        size = str(r.get('rozmiar') or '').strip() or rt_text(p['mf'].get('rozmiar', {}).get('value')) or 'One Size'
        material = str(r.get('material') or '').strip()
        sklad = material if '%' in material else None
        podszycie = str(r.get('podszycie') or '').strip() or None
        if not sklad and material: notes.append(f'{code}: material „{material}” to nie skład procentowy — metapole Skład bez zmian')

        title, body = sc.build_text(city, segword, is_komin, mats, size, flags, code, sklad=sklad, podszycie=podszycie, is_opaska=is_opaska)
        if m.group(6) == 'Turbo': title += ' (Turbo)'
        elif m.group(6) == 'bez pompona': title += ' (bez pompona)'

        tags = set(p['tags'])
        if is_opaska: tags.add('opaski')
        plec = str(r.get('Płeć') or '').strip().lower()
        if plec == 'unisex': tags.add('meskie'); stats['unisex'] += 1
        elif plec and plec not in ('ona', 'damskie', 'kobieta', 'dziecięce', 'dziecko', 'chłopięce', 'dziewczęce'): notes.append(f'{code}: Płeć „{r["Płeć"]}” niezrozumiała, pominięta')
        cena = num(r.get('Cena netto')); promo = num(r.get('cena promocyjna'))
        if cena: tags.discard(PRICE_TAG)
        ptype = 'Opaska' if is_opaska else ('Komin' if is_komin else 'Czapka')

        changes = []
        if p['title'] != title: changes.append(f'tytuł „{p["title"]}”→„{title}”')
        if is_opaska and p['type'] != 'Opaska': stats['opaska'] += 1
        if sklad: stats['sklad'] += 1
        if podszycie: stats['podszycie'] += 1
        if sorted(tags) != sorted(p['tags']): changes.append('tagi ' + ','.join(sorted(set(tags) ^ set(p['tags']))))
        # produkt: tytuł, opis, tagi, typ — opis zawsze przeliczany (skład/podszycie), więc aktualizujemy zawsze
        stats['tytul_opis'] += 1
        mut('''mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ field message } } }''',
            {'p': {'id': p['id'], 'title': title, 'descriptionHtml': body, 'tags': sorted(tags), 'productType': ptype}}, f'{code} productUpdate')
        # metapola
        mfv = {}
        if sklad and rt_text(p['mf'].get('sklad', {}).get('value')) != sklad: mfv['sklad'] = sklad
        if rt_text(p['mf'].get('rozmiar', {}).get('value')) != size: mfv['rozmiar'] = size; stats['rozmiar'] += 1; changes.append(f'rozmiar→{size}')
        if mfv:
            mfs = [{'ownerId': p['id'], 'namespace': 'custom', 'key': k, 'type': defs[k], 'value': si.mf_value(defs[k], v)} for k, v in mfv.items()]
            mut('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''', {'m': mfs}, f'{code} metapola')
        # wariant: cena, cena promocyjna, waga
        v = {}
        if cena:
            if promo and promo < cena:
                v['price'] = f'{promo:.2f}'; v['compareAtPrice'] = f'{cena:.2f}'; stats['promo'] += 1
            else:
                v['price'] = f'{cena:.2f}'
                if p['compare']: v['compareAtPrice'] = None
            if v['price'] != p['price']: changes.append(f'cena {p["price"]}→{v["price"]}'); stats['cena'] += 1
            elif 'compareAtPrice' not in v or v['compareAtPrice'] == p['compare']: v = {}
        waga = num(r.get('waga_g'))
        if waga and (p['weight'] or 0) * 1000 != waga:
            v['inventoryItem'] = {'measurement': {'weight': {'value': waga, 'unit': 'GRAMS'}}}; changes.append(f'waga {waga:g} g'); stats['waga'] += 1
        if v:
            v['id'] = p['variant_id']
            mut('''mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ field message } } }''',
                {'pid': p['id'], 'v': [v]}, f'{code} wariant')
        if changes: print(f'* {code}: ' + '; '.join(changes))
        # zapis do achti-produkty.json (źródło dla translate_catalog.py)
        if o:
            o.update(title=title, body_html=body, size=size, product_type=ptype, tags=sorted(tags))
            if sklad: o['sklad'] = sklad
            if podszycie: o['podszycie'] = podszycie
            if cena: o['price'] = f'{cena:.2f}'
        for k in ('nazwa_produktu', 'kolory (po przecinku)', 'opis', 'tagi (damskie/meskie/dzieci/premium/nowosc)'):
            if r.get(k): notes.append(f'{code}: kolumna „{k}” = „{r[k]}” — NIE naniesiona automatycznie')
    if not DRY:
        json.dump(old, open(OLD_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\nPODSUMOWANIE' + (' (dry-run)' if DRY else ''), stats)
    for n in notes: print(' -', n)

if __name__ == '__main__':
    main()
