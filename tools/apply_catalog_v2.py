#!/usr/bin/env python3
"""Nanosi na sklep arkusz Adriana „achti-katalog-v2 (…).xlsx” (Google Drive, folder WORKSPACE ACHTI x KAMIL DZIEDZIC).
Kolumny: kod (nagłówek bywa uszkodzony — pierwsza kolumna), typ (Czapka zimowa / Opaska zimowa), podszycie, material (skład %),
rozmiar, Cena netto, Płeć (Ona / On / Unisex / Dla dzieci Dziewczynka|Chłopczyk|Unisex), plik, nazwa_produktu, kolory (po przecinku),
cena promocyjna, opis, tagi, waga_g.

Arkusz jest źródłem prawdy (dopasowanie po SKU; gdy kod się zmienił, np. AZ-3038 -> AZ-3038PC, dopasowanie po nazwie pliku zdjęcia
albo po części liczbowej kodu i aktualizacja SKU):
- tytuł = „Czapka zimowa damska <nazwa_produktu>” (męska / unisex / dziecięca / chłopięca / dziewczęca; „Opaska zimowa …”), tools/catalog_text.py;
- opis = kolumna opis (jeśli jest) albo szablon; zawsze z cechami i specyfikacją (skład, podszycie, rozmiar, kod);
- tagi płci wg Płeć (damskie / meskie / dzieci; rozmiar 50-52, 52-54 = dzieci), tag `opaski` dla opasek, reszta tagów bez zmian;
- metapola custom.sklad (material z %), custom.rozmiar; cena netto -> cena wariantu (+ zdjęcie tagu `cena-do-uzupelnienia`);
  cena promocyjna -> cena z przekreśloną ceną netto; waga_g -> waga wariantu.
- kolory (po przecinku) NIE są nanoszone (warianty kolorów wymagają decyzji o zdjęciach) — tylko raport.
Aktualizuje tools/achti-produkty.json (name, segment, product_type, flags, sklad, podszycie, opis, price…) — źródło dla translate_catalog.py.

Użycie: python3 tools/apply_catalog_v2.py --xlsx=~/Downloads/achti-katalog-v2.xlsx [--dry-run] [--codes=AZ-1,AZ-2]
"""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
import catalog_text as ct
import openpyxl

HERE = os.path.dirname(__file__)
DRY = '--dry-run' in sys.argv
XLSX = next((os.path.expanduser(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--xlsx=')), os.path.join(HERE, 'achti-katalog-v2-drive.xlsx'))
CODES = next((set(a.split('=', 1)[1].split(',')) for a in sys.argv if a.startswith('--codes=')), None)
OLD_PATH = os.path.join(HERE, 'achti-produkty.json')
PRICE_TAG = 'cena-do-uzupelnienia'
norm_file = lambda f: re.sub(r'\.jpe?g$', '', os.path.basename(f or ''), flags=re.I).upper().strip()

def rt_text(value):
    if not value: return ''
    try:
        d = json.loads(value); out = []
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
    try: return float(str(v).strip().replace(',', '.').replace(' ', ''))
    except ValueError: return None

def read_rows():
    ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True)); hdr = [str(h).strip() if h else '' for h in rows[0]]
    hdr[0] = 'kod'  # w arkuszu z 10.09 nagłówek „kod” został nadpisany znakiem „∂”
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
            media(first:1){ nodes{ ... on MediaImage { image { url } } } }
            metafields(first:10, namespace:"custom"){ nodes{ id key type value } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            v = p['variants']['nodes'][0]
            img = (p['media']['nodes'][0].get('image') or {}).get('url', '') if p['media']['nodes'] else ''
            out[p['id']] = dict(id=p['id'], title=p['title'], tags=p['tags'], type=p['productType'], variant_id=v['id'], price=v['price'],
                                sku=(v['sku'] or '').upper(), compare=v['compareAtPrice'], weight=(v['inventoryItem']['measurement']['weight'] or {}).get('value'),
                                image=re.sub(r'\?.*$', '', img.rsplit('/', 1)[-1]), mf={m['key']: m for m in p['metafields']['nodes']})
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return out

def mut(query, variables, label):
    if DRY: return {}
    r = si.gql(query, variables)
    key = next(iter(r)); errs = r[key].get('userErrors')
    if errs: print('   BŁĄD', label, errs)
    return r

def find_product(code, r, shop, by_sku, old_by):
    """SKU -> nazwa pliku zdjęcia w sklepie / w achti-produkty.json -> część liczbowa kodu (gdy jednoznaczna)."""
    if code in by_sku: return by_sku[code]
    want = norm_file(r.get('plik'))
    for p in shop.values():
        if norm_file(p['image']).replace('_', ' ') == want.replace('_', ' '): return p
    for o in old_by.values():
        if o.get('plik') and norm_file(o['plik']) == want and o['code'].upper() in by_sku: return by_sku[o['code'].upper()]
    core = re.sub(r'\D', '', code)
    c = [p for s, p in by_sku.items() if re.sub(r'\D', '', s) == core]
    return c[0] if len(c) == 1 else None

def main():
    rows = read_rows()
    shop = fetch_shop()
    by_sku = {p['sku']: p for p in shop.values() if p['sku']}
    defs = si.metafield_defs()
    old = json.load(open(OLD_PATH, encoding='utf-8')); old_by = {o['code'].upper(): o for o in old}
    stats = dict(tytul=0, sku=0, cena=0, promo=0, sklad=0, rozmiar=0, waga=0, tagi=0, opis_wlasny=0, brak=0)
    notes = []
    seen = set()
    for code, r in rows.items():
        if CODES and code not in CODES: continue
        p = find_product(code, r, shop, by_sku, old_by)
        if not p:
            stats['brak'] += 1; notes.append(f'brak w sklepie: {code} ({r.get("plik")})'); continue
        seen.add(p['id'])
        o = old_by.get(code) or old_by.get(p['sku']) or {}
        name = str(r.get('nazwa_produktu') or '').strip()
        if not name:
            notes.append(f'{code}: brak nazwy w arkuszu — pominięty'); continue
        mats = o.get('materials') or []
        size = str(r.get('rozmiar') or '').strip() or rt_text(p['mf'].get('rozmiar', {}).get('value')) or 'One Size'
        material = str(r.get('material') or '').strip()
        sklad = material if '%' in material else (o.get('sklad') or None)
        if material and '%' not in material: notes.append(f'{code}: material „{material}” bez procentów — skład bez zmian')
        podszycie = str(r.get('podszycie') or '').strip() or o.get('podszycie') or None
        flags = o.get('flags') or ct.flags_from_old_title(p['title'])
        if '-BOY' in code: flags = sorted(set(flags) | {'BOY'})
        if '-GIRL' in code: flags = sorted(set(flags) | {'GIRL'})
        segment = ct.segment_from(r.get('Płeć'), size, flags)
        plec = str(r.get('Płeć') or '').strip().lower()
        if segment.startswith(('Dziec', 'Chłop', 'Dziew')) and 'dzieci' not in plec and plec: notes.append(f'{code}: rozmiar {size} = dziecięca, choć Płeć „{r["Płeć"]}”')
        kind = ct.product_kind(r.get('typ'))
        opis = str(r.get('opis') or '').strip() or None
        title = ct.title_for(name, segment, kind)
        body = ct.body_for(name, segment, kind, mats, size, flags, code, sklad=sklad, podszycie=podszycie, opis=opis)
        if opis: stats['opis_wlasny'] += 1

        tags = set(p['tags']) - ct.GENDER_TAGS | set(ct.SEGMENTS[segment][2])
        if kind == 'Opaska': tags.add('opaski')
        else: tags.discard('opaski')
        cena = num(r.get('Cena netto')); promo = num(r.get('cena promocyjna'))
        if cena: tags.discard(PRICE_TAG)

        changes = []
        if p['title'] != title: changes.append(f'tytuł „{p["title"]}”→„{title}”'); stats['tytul'] += 1
        if sorted(tags) != sorted(p['tags']): changes.append('tagi ' + ','.join(sorted(set(tags) ^ set(p['tags'])))); stats['tagi'] += 1
        mut('''mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ field message } } }''',
            {'p': {'id': p['id'], 'title': title, 'descriptionHtml': body, 'tags': sorted(tags), 'productType': kind}}, f'{code} productUpdate')
        mfv = {}
        if sklad and rt_text(p['mf'].get('sklad', {}).get('value')) != sklad: mfv['sklad'] = sklad; stats['sklad'] += 1
        if rt_text(p['mf'].get('rozmiar', {}).get('value')) != size: mfv['rozmiar'] = size; stats['rozmiar'] += 1; changes.append(f'rozmiar→{size}')
        if mfv:
            mfs = [{'ownerId': p['id'], 'namespace': 'custom', 'key': k, 'type': defs[k], 'value': si.mf_value(defs[k], v)} for k, v in mfv.items()]
            mut('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''', {'m': mfs}, f'{code} metapola')
        v = {}
        if p['sku'] != code:
            v['inventoryItem'] = {'sku': code}; changes.append(f'SKU {p["sku"]}→{code}'); stats['sku'] += 1
        if cena:
            if promo and promo < cena:
                v['price'] = f'{promo:.2f}'; v['compareAtPrice'] = f'{cena:.2f}'; stats['promo'] += 1
            else:
                v['price'] = f'{cena:.2f}'
                if p['compare']: v['compareAtPrice'] = None
            if v['price'] != p['price']: changes.append(f'cena {p["price"]}→{v["price"]}'); stats['cena'] += 1
            elif v.get('compareAtPrice', p['compare']) == p['compare']: v.pop('price'); v.pop('compareAtPrice', None)
        waga = num(r.get('waga_g'))
        if waga and round((p['weight'] or 0) * 1000) != round(waga):
            v.setdefault('inventoryItem', {})['measurement'] = {'weight': {'value': waga, 'unit': 'GRAMS'}}; changes.append(f'waga {waga:g} g'); stats['waga'] += 1
        if v:
            v['id'] = p['variant_id']
            mut('''mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ field message } } }''',
                {'pid': p['id'], 'v': [v]}, f'{code} wariant')
        if changes: print(f'* {code}: ' + '; '.join(changes))
        if o:
            o.update(code=code, title=title, body_html=body, size=size, product_type=kind, tags=sorted(tags), name=name, segment=segment, flags=flags,
                     plik=r.get('plik') or o.get('plik'))
            if sklad: o['sklad'] = sklad
            if podszycie: o['podszycie'] = podszycie
            if opis: o['opis'] = opis
            else: o.pop('opis', None)
            if cena: o['price'] = f'{cena:.2f}'
        else:
            notes.append(f'{code}: brak wpisu w achti-produkty.json (tłumaczenia nie zostaną wygenerowane)')
        if r.get('kolory (po przecinku)'): notes.append(f'{code}: kolory „{r["kolory (po przecinku)"]}” — NIE naniesione (warianty do decyzji)')
        if r.get('tagi (damskie/meskie/dzieci/premium/nowosc)'): notes.append(f'{code}: kolumna tagi „{r["tagi (damskie/meskie/dzieci/premium/nowosc)"]}” — NIE naniesiona')
    extra = [p for p in shop.values() if p['id'] not in seen]
    if extra and not CODES: notes.append('produkty w sklepie bez wiersza w arkuszu: ' + ', '.join(f"{p['sku']} „{p['title']}”" for p in extra))
    if not DRY:
        json.dump(old, open(OLD_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\nPODSUMOWANIE' + (' (dry-run)' if DRY else ''), stats)
    for n in notes: print(' -', n)

if __name__ == '__main__':
    main()
