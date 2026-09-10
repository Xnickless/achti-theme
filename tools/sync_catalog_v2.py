#!/usr/bin/env python3
"""Synchronizuje sklep z katalogiem v2 (tools/katalog-v2.json + zdjęcia „ACHTI B2B Full Size - biale tlo”).
- każdy wiersz v2 dopasowany do produktu w sklepie po nazwie starego zdjęcia (achti-produkty.json → tytuł),
- podmiana zdjęcia, SKU (sufiksy wariantów, AZ-607PCV1), rozmiaru, materiału (metapola, tagi, opis),
- nowe produkty (brak w sklepie) tworzone z szablonu; produkty spoza Full Size usuwane,
- porządek w metapolu inne_kolory (usunięte ID, powiązania wariantów tego samego kodu),
- aktualizacja achti-produkty.json (źródło dla tłumaczeń).
Użycie: python3 tools/sync_catalog_v2.py [--dry-run] [--only=photos,data,create,delete,groups] [--all-photos] [--photos-dir=...]"""
import sys, os, re, json, unicodedata, collections
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si

HERE = os.path.dirname(__file__)
HOME = os.path.expanduser('~')
PHOTOS = os.path.join(HOME, 'Downloads/ACHTI B2B Full Size - biale tlo')
V2 = json.load(open(os.path.join(HERE, 'katalog-v2.json'), encoding='utf-8'))
OLD_PATH = os.path.join(HERE, 'achti-produkty.json')
OLD = json.load(open(OLD_PATH, encoding='utf-8'))
DRY = '--dry-run' in sys.argv
ALL_PHOTOS = '--all-photos' in sys.argv  # podmień zdjęcia także tam, gdzie już jest obraz 2000 px
ONLY = None
for a in sys.argv[1:]:
    if a.startswith('--only='): ONLY = set(a.split('=', 1)[1].split(','))
    if a.startswith('--photos-dir='): PHOTOS = os.path.expanduser(a.split('=', 1)[1])
    if a.startswith('--codes='): V2 = [r for r in V2 if r['kod'] in set(a.split('=', 1)[1].split(','))]  # tylko wybrane kody (bez usuwania!)
def want(step): return not ONLY or step in ONLY

norm = lambda f: re.sub(r'\.jpe?g$', '', f, flags=re.I).upper().strip()
slug = lambda m: re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', m).encode('ascii', 'ignore').decode().lower()).strip('-')
def title_case_mat(m):  # 'VEZUV TURBO' -> 'Vezuv Turbo', 'LAMBSLOOK 90/10' -> 'Lambslook 90/10'
    return ' '.join(w if '/' in w else w.capitalize() for w in m.split())

GROUP_PRICE = {'G3': '39.00', 'G5': '49.00', 'G7': '59.00', 'G10': '69.00', 'G12': '79.00'}  # ceny przykładowe jak w set_prices.py
SUFFIX_LABEL = {'TURBO': 'Turbo', 'BP': 'bez pompona'}  # BOY/GIRL już w słowie Chłopięca/Dziewczęca

LINING = {  # kolumna „podszycie” z arkusza Adriana -> (fraza w opisie, cecha w liście)
    'Pełne podszycie polarowe 100% poliester': (' z pełnym podszyciem polarowym', 'Pełne podszycie polarowe (100% poliester)'),
    'Opaska polarowa 100% poliester': (' z polarową opaską w środku', 'Wewnętrzna opaska polarowa (100% poliester)'),
    'Podwójna dzianina': (' o podwójnej dzianinie', 'Podwójna dzianina — ciepła bez podszycia'),
    'Bez podszycia': ('', 'Pojedyncza dzianina, bez podszycia'),
}

def build_text(city, segword, is_komin, mats, size, flags, code, sklad=None, podszycie=None, is_opaska=False):
    """Polski tytuł + opis wg szablonu z generate_catalog.py (rozszerzony 10.09.2026 o skład, podszycie i opaski)."""
    if is_komin:
        title = f"Komin Zimowy Damski {city}"
    elif is_opaska:
        title = f"Opaska Zimowa Damska {city}"
    else:
        title = f"Czapka Zimowa {segword} Beanie {city}"
    suffix = []
    if 'CEKIN' in flags or 'CEKINY' in flags: suffix.append('z Cekinami')
    if 'MULTI' in flags: suffix.append('Multikolor')
    if suffix: title += ' ' + ' '.join(suffix)
    mat_txt = ' i '.join(mats) if mats else 'miękkiej dzianiny'
    lining_phrase, lining_feat = LINING.get(podszycie or '', ('', None))
    if is_komin:
        intro = f"Komin zimowy {city} to uniwersalny dodatek z dzianiny {mat_txt}{lining_phrase}, który zastępuje szalik i chroni szyję przed wiatrem. Klasyczna forma sprawdza się w codziennych stylizacjach i dobrze uzupełnia ofertę czapek."
        feats = ['Miękka, elastyczna dzianina', 'Nie uciska i nie krępuje ruchów', 'Uniwersalny rozmiar', 'Idealny na sezon jesień–zima']
    elif is_opaska:
        intro = f"Opaska zimowa {city} to model damski z dzianiny {mat_txt}{lining_phrase}, który chroni uszy i czoło przed zimnem, nie spłaszczając fryzury. Sprawdza się na spacer, do biegania i na co dzień, a jej klasyczny wygląd łatwo łączy się z zimowymi stylizacjami."
        feats = ['Miękka, elastyczna dzianina', 'Zakrywa uszy, nie spłaszcza fryzury', 'Uniwersalny rozmiar' if size == 'One Size' else f'Rozmiar {size}', 'Idealna na sezon jesień–zima']
    else:
        who = {'Dziecięca': 'dla dzieci', 'Chłopięca': 'dla chłopców', 'Dziewczęca': 'dla dziewczynek'}.get(segword, 'damska')
        intro = f"Czapka zimowa {city} to model {who} z dzianiny {mat_txt}{lining_phrase}, łączący klasyczny fason z wygodą noszenia. Dobrze trzyma kształt, jest ciepła i lekka, a jej ponadczasowy wygląd sprawia, że łatwo komponuje się z zimowymi stylizacjami."
        feats = ['Miękka i komfortowa dzianina', 'Elastyczny fason dopasowujący się do głowy', 'Uniwersalny rozmiar' if size == 'One Size' else f'Rozmiar {size}', 'Idealna na sezon jesień–zima']
        if 'CEKIN' in flags or 'CEKINY' in flags: feats.insert(1, 'Zdobienie cekinami')
        if 'MULTI' in flags: feats.insert(1, 'Wielokolorowy wzór')
        if 'BEZ POMPONA' in flags: feats.insert(1, 'Wersja bez pompona')
    if lining_feat: feats.insert(-2, lining_feat)
    spec = ["Model: " + city, "Kod: " + code, "Materiał: " + (', '.join(mats) or 'do uzupełnienia')]
    if sklad: spec.append("Skład: " + sklad)
    if podszycie: spec.append("Podszycie: " + podszycie)
    spec += ["Rozmiar: " + size, "Sezon: jesień / zima"]
    body = (f"<p>{intro}</p><p>Model {city} stanowi dobre uzupełnienie oferty sklepów odzieżowych, butików oraz punktów sprzedaży akcesoriów zimowych.</p><p><strong>Cechy produktu:</strong><br>"
            + "<br>".join('✔ ' + f for f in feats)
            + "</p><p><strong>Specyfikacja:</strong></p><ul>" + ''.join(f'<li>{x}</li>' for x in spec) + "</ul>")
    return title, body

def segword_for(r, old):
    flags = r['_flags']
    if 'BOY' in flags: return 'Chłopięca'
    if 'GIRL' in flags: return 'Dziewczęca'
    size = r['rozmiar'] or ''
    if re.fullmatch(r'\d{2}-\d{2}', size) and int(size[:2]) < 56: return 'Dziecięca'
    if old and 'Dziecięca' in old['title']: return 'Dziecięca'
    return 'Damska'

# ---------- stan sklepu ----------
def fetch_shop():
    out, cursor = {}, None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title handle tags status
            variants(first:1){ nodes{ id sku price inventoryItem{ id } } } media(first:10){ nodes{ id ... on MediaImage { image { width } } } }
            metafields(first:10, namespace:"custom"){ nodes{ id key type value } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            v = p['variants']['nodes'][0]
            out[p['id']] = dict(id=p['id'], title=p['title'], handle=p['handle'], tags=p['tags'], sku=v['sku'] or '', variant_id=v['id'],
                                price=v['price'], media=[m['id'] for m in p['media']['nodes']], media_w=[(m.get('image') or {}).get('width') for m in p['media']['nodes']],
                                mf={m['key']: m for m in p['metafields']['nodes']})
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return out

def mut(query, variables, label):
    if DRY:
        print('   [dry]', label); return {}
    r = si.gql(query, variables)
    key = next(iter(r)); errs = r[key].get('userErrors')
    if errs: print('   BŁĄD', label, errs)
    return r

def set_photo(pid, old_media_ids, path, alt):
    if old_media_ids:
        mut('''mutation($pid:ID!,$ids:[ID!]!){ productDeleteMedia(productId:$pid, mediaIds:$ids){ userErrors{ field message } } }''', {'pid': pid, 'ids': old_media_ids}, f'usuń media {len(old_media_ids)}')
    if DRY:
        print('   [dry] wgraj', os.path.basename(path)); return
    url = si.staged_upload(path)
    mut('''mutation($pid:ID!,$m:[CreateMediaInput!]!){ productCreateMedia(productId:$pid, media:$m){ userErrors{ field message } } }''',
        {'pid': pid, 'm': [{'originalSource': url, 'alt': alt, 'mediaContentType': 'IMAGE'}]}, 'wgraj zdjęcie')

def set_metafields(pid, defs, values):
    mfs = [{'ownerId': pid, 'namespace': 'custom', 'key': k, 'type': defs[k], 'value': si.mf_value(defs[k], v)} for k, v in values.items() if k in defs]
    if mfs: mut('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''', {'m': mfs}, f'metapola {list(values)}')

def main():
    shop = fetch_shop()
    defs = si.metafield_defs()
    by_title = {p['title']: p for p in shop.values()}
    by_sku = collections.defaultdict(list)
    for p in shop.values(): by_sku[p['sku'].upper()].append(p)
    oldmap = {norm(os.path.basename(o['photo'] or '')): o for o in OLD}
    cities = re.search(r'CITIES="""(.*?)"""', open(os.path.join(HERE, 'generate_catalog.py'), encoding='utf-8').read(), re.S).group(1).split()
    used_cities = {w for o in OLD for w in o['title'].split() if w in set(cities)}
    free_cities = [c for c in cities if c not in used_cities]
    cityset = set(cities)
    def city_of(title):
        for w in title.split():
            if w in cityset: return w
        return title.split()[-1]
    missing = [r['plik'] for r in V2 if not os.path.exists(os.path.join(PHOTOS, os.path.splitext(r['plik'])[0] + '.jpg'))]
    if missing and not DRY:
        print(f'BRAK {len(missing)} ZDJĘĆ w folderze wyjściowym, np. {missing[:3]} — przerwane'); return

    matched_pids, new_old = set(), []
    photos_done = 0
    for r in V2:
        photo = os.path.join(PHOTOS, os.path.splitext(r['plik'])[0] + '.jpg')
        if not os.path.exists(photo) and not DRY: continue
        base_code = r.get('_base_code') or r['kod']
        old = oldmap.get(norm(r['plik']))
        if not old:
            c = [o for o in OLD if o['code'].upper() in (base_code.upper(), base_code.upper().rstrip('1'))]
            old = c[0] if len(c) == 1 else None
        prod = by_title.get(old['title']) if old else None
        if not prod and not old:
            c = by_sku.get(r['kod'].upper()) or by_sku.get(base_code.upper())
            prod = c[0] if c and len(c) == 1 else None
        mats_pl = [title_case_mat(m) for m in r['_materials']]
        size = r['rozmiar'] or (old['size'] if old else 'One Size')
        is_komin = r['typ'] == 'Komin'
        flags = r['_flags']
        tags = ['cena-do-upelnienia'.replace('upelnienia', 'uzupelnienia')]
        segword = segword_for(r, old)
        tags.append('dzieci' if segword != 'Damska' else 'damskie')
        if r['_group']: tags.append('grupa-' + r['_group'].lower())
        tags += [slug(m) for m in mats_pl]
        if is_komin: tags.append('kominy')
        if old:
            for t in old['tags']:
                if t in ('nowosc', 'premium', 'meskie'): tags.append(t)
        tags = sorted(set(tags))

        if prod:
            matched_pids.add(prod['id'])
            city = city_of(old['title'] if old else prod['title'])
            # tytuł/opis: przelicz z szablonu, sufiks wariantu w tytule
            title, body = build_text(city, segword, is_komin, mats_pl, size, flags, r['kod'])
            if r.get('_base_code'):
                lab = SUFFIX_LABEL.get(r['kod'].rsplit('-', 1)[-1])
                if lab: title += f' ({lab})'
            changes = []
            if want('data'):
                if prod['sku'] != r['kod']: changes.append(f"sku {prod['sku']}→{r['kod']}")
                if sorted(prod['tags']) != tags: changes.append('tagi')
                if prod['title'] != title: changes.append(f"tytuł „{prod['title']}”→„{title}”")
                if changes:
                    print(f"* {r['kod']}: " + ', '.join(changes))
                    mut('''mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ field message } } }''',
                        {'p': {'id': prod['id'], 'title': title, 'descriptionHtml': body, 'tags': tags}}, 'productUpdate')
                    if prod['sku'] != r['kod']:
                        mut('''mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ field message } } }''',
                            {'pid': prod['id'], 'v': [{'id': prod['variant_id'], 'inventoryItem': {'sku': r['kod']}}]}, 'sku')
                    set_metafields(prod['id'], defs, {'rozmiar': size, 'sklad': ', '.join(mats_pl)})
            if want('photos'):
                if not ALL_PHOTOS and len(prod['media']) == 1 and prod['media_w'][0] == 2000:
                    pass  # już podmienione (nowe zdjęcia mają 2000 px, stare 1024)
                else:
                    set_photo(prod['id'], prod['media'], photo, title); photos_done += 1
                    print(f"  foto {photos_done}: {r['kod']}", flush=True)
            entry = old or {}
            entry.update(code=r['kod'], title=title, body_html=body, product_type='Komin' if is_komin else 'Czapka', vendor='Achti', tags=tags,
                         size=size, materials=mats_pl, photo=photo, price=entry.get('price', '0.00'), shop_id=prod['id'], plik=r['plik'])
            if not old: new_old.append(entry)
        else:
            # nowy produkt
            city = free_cities.pop(0)
            title, body = build_text(city, segword, is_komin, mats_pl, size, flags, r['kod'])
            if r.get('_base_code'):
                lab = SUFFIX_LABEL.get(r['kod'].rsplit('-', 1)[-1])
                if lab: title += f' ({lab})'
            price = GROUP_PRICE.get(r['_group'] or '', '0.00')
            base = by_sku.get(base_code.upper())
            if base: price = base[0]['price']
            p = dict(code=r['kod'], title=title, body_html=body, product_type='Komin' if is_komin else 'Czapka', vendor='Achti', tags=tags,
                     size=size, materials=mats_pl, photo=photo, price=price, plik=r['plik'])
            print(f"+ NOWY {r['kod']} „{title}” cena {price}")
            if want('create') and not DRY:
                handle = si.create_product(p, defs)
                p['handle'] = handle
            new_old.append(p)

    # usuwanie: produkty w sklepie bez dopasowania do v2
    CODES_ONLY = any(a.startswith('--codes=') for a in sys.argv)
    to_delete = [] if CODES_ONLY else [p for pid, p in shop.items() if pid not in matched_pids and not any(n.get('handle') and n['code'] == p['sku'] for n in new_old)]
    print(f"\nusuwane: {len(to_delete)}")
    for p in to_delete:
        print(f"- {p['sku']} „{p['title']}”")
        if want('delete'):
            mut('''mutation($id:ID!){ productDelete(input:{id:$id}){ deletedProductId userErrors{ field message } } }''', {'id': p['id']}, 'productDelete')
    deleted_ids = {p['id'] for p in to_delete}

    # inne_kolory: usuń skasowane, dodaj powiązania wariantów tego samego kodu
    if want('groups') and not DRY:
        shop2 = fetch_shop()
        by_base = collections.defaultdict(list)
        for p in shop2.values():
            m = re.match(r'^(AZ-\d+[A-Z0-9]*)', p['sku'].upper())
            if m: by_base[m.group(1)].append(p['id'])
        n = 0
        for p in shop2.values():
            mf = p['mf'].get('inne_kolory')
            ids = json.loads(mf['value']) if mf else []
            ids = [i for i in ids if i in shop2 and i not in deleted_ids]
            m = re.match(r'^(AZ-\d+[A-Z0-9]*)', p['sku'].upper())
            if m:
                for sib in by_base[m.group(1)]:
                    if sib != p['id'] and sib not in ids: ids.append(sib)
            old_ids = json.loads(mf['value']) if mf else []
            if ids != old_ids:
                mut('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''',
                    {'m': [{'ownerId': p['id'], 'namespace': 'custom', 'key': 'inne_kolory', 'type': 'list.product_reference', 'value': json.dumps(ids)}]}, 'inne_kolory'); n += 1
        print('inne_kolory zaktualizowane:', n)

    # zapis achti-produkty.json
    if not DRY and not CODES_ONLY:
        keep = [o for o in OLD if norm(os.path.basename(o['photo'] or '')) in {norm(r['plik']) for r in V2} or o.get('shop_id') in matched_pids]
        json.dump(keep + [n for n in new_old if n not in keep], open(OLD_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('achti-produkty.json:', len(keep) + len([n for n in new_old if n not in keep]))
    print('zdjęcia podmienione:', photos_done)

if __name__ == '__main__':
    main()
