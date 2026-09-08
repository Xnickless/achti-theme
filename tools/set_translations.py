#!/usr/bin/env python3
"""Wgrywa tłumaczenia z tools/translations/<locale>.json przez Admin API (translationsRegister)
i opcjonalnie publikuje język. Wymaga scope: read/write_translations, read/write_locales,
read_content (strony, menu), read_themes (teksty motywu), read_products.
Użycie:  python3 tools/set_translations.py en [fr de] [--publish] [--only products,collections,menu,theme]"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si

HERE = os.path.dirname(__file__)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
flags = [a for a in sys.argv[1:] if a.startswith('--')]
locales = args or ['en']
only = None
for f in flags:
    if f.startswith('--only'):
        only = set(f.split('=', 1)[1].split(','))
publish = '--publish' in flags

def translatable(rtype):
    """Zwraca listę {resourceId, translatableContent:[{key,value,digest,locale}]} dla typu zasobu."""
    out, cursor = [], None
    while True:
        r = si.gql('''query($t:TranslatableResourceType!,$c:String){ translatableResources(first:100, resourceType:$t, after:$c){
            nodes{ resourceId translatableContent{ key value digest locale } } pageInfo{ hasNextPage endCursor } } }''', {'t': rtype, 'c': cursor})
        out += r['translatableResources']['nodes']
        if not r['translatableResources']['pageInfo']['hasNextPage']: break
        cursor = r['translatableResources']['pageInfo']['endCursor']
    return out

def register(resource_id, translations):
    """translations: list of {key, value, digest, locale}"""
    if not translations: return
    for i in range(0, len(translations), 100):
        r = si.gql('''mutation($id:ID!,$t:[TranslationInput!]!){ translationsRegister(resourceId:$id, translations:$t){ userErrors{ field message } } }''',
                   {'id': resource_id, 't': translations[{'k': i}['k']:i + 100]})
        errs = r['translationsRegister']['userErrors']
        if errs: print('  błąd', resource_id, errs)

def content_map(node):
    return {c['key']: c for c in node['translatableContent']}

def do_products(loc, data):
    trs = data['products']
    # SKU -> product id
    sku_to_id = {}
    cursor = None
    while True:
        r = si.gql('''query($c:String){ products(first:250, after:$c){ nodes{ id variants(first:1){ nodes{ sku } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            s = (p['variants']['nodes'][0]['sku'] or '').upper()
            if s: sku_to_id[s] = p['id']
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    nodes = {n['resourceId']: n for n in translatable('PRODUCT')}
    n_ok = 0
    for code, tr in trs.items():
        pid = sku_to_id.get(code.upper())
        node = pid and nodes.get(pid)
        if not node:
            print('  brak produktu', code); continue
        cm = content_map(node)
        payload = []
        for key, val in (('title', tr['title']), ('body_html', tr['body_html'])):
            if key in cm:
                payload.append({'key': key, 'value': val, 'translatableContentDigest': cm[key]['digest'], 'locale': loc})
        register(pid, payload); n_ok += 1
    print(f'  produkty: {n_ok}')
    # metapola (custom.rozmiar / custom.sklad) jako osobne zasoby METAFIELD
    mf_nodes = translatable('METAFIELD')
    n_mf = 0
    for node in mf_nodes:
        cm = content_map(node)
        if 'value' not in cm: continue
        # nie mamy mapowania metafield->produkt bez dodatkowego zapytania; tłumaczymy po wartości PL
        pl = cm['value']['value']
        val = None
        if pl == 'One Size': val = {'en': 'One Size', 'fr': 'Taille unique', 'de': 'Einheitsgröße'}[loc]
        elif pl in ('Akryl',): val = {'en': 'Acrylic', 'fr': 'Acrylique', 'de': 'Acryl'}[loc]
        if val:
            register(node['resourceId'], [{'key': 'value', 'value': val, 'translatableContentDigest': cm['value']['digest'], 'locale': loc}]); n_mf += 1
    print(f'  metapola: {n_mf}')

def do_collections(loc, data):
    nodes = translatable('COLLECTION')
    handles = {}
    cursor = None
    while True:
        r = si.gql('''query($c:String){ collections(first:100, after:$c){ nodes{ id handle } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for c in r['collections']['nodes']: handles[c['id']] = c['handle']
        if not r['collections']['pageInfo']['hasNextPage']: break
        cursor = r['collections']['pageInfo']['endCursor']
    n = 0
    for node in nodes:
        h = handles.get(node['resourceId'])
        tr = data['collections'].get(h)
        if not tr: continue
        cm = content_map(node); payload = []
        if 'title' in cm and tr[0]: payload.append({'key': 'title', 'value': tr[0], 'translatableContentDigest': cm['title']['digest'], 'locale': loc})
        if 'body_html' in cm and tr[1]: payload.append({'key': 'body_html', 'value': f'<p>{tr[1]}</p>', 'translatableContentDigest': cm['body_html']['digest'], 'locale': loc})
        register(node['resourceId'], payload); n += 1
    print(f'  kolekcje: {n}')

def do_menu(loc, data):
    n = 0
    for rtype in ('ONLINE_STORE_MENU', 'LINK'):
        try:
            nodes = translatable(rtype)
        except Exception as e:
            print('  pomijam', rtype, str(e)[:80]); continue
        for node in nodes:
            cm = content_map(node); payload = []
            for key, c in cm.items():
                val = data['menu'].get(c['value'])
                if val: payload.append({'key': key, 'value': val, 'translatableContentDigest': c['digest'], 'locale': loc})
            if payload: register(node['resourceId'], payload); n += 1
    print(f'  menu: {n}')

def do_theme(loc, data):
    nodes = translatable('ONLINE_STORE_THEME')
    n = 0
    for node in nodes:
        cm = content_map(node); payload = []
        for key, c in cm.items():
            src = re.sub(r'<[^>]+>', '', c['value'] or '').strip()
            val = data['theme'].get(src)
            if val:
                out = c['value'].replace(src, val) if src != c['value'] else val
                payload.append({'key': key, 'value': out, 'translatableContentDigest': c['digest'], 'locale': loc})
        if payload: register(node['resourceId'], payload); n += len(payload)
    print(f'  teksty motywu: {n}')

def do_publish(loc):
    r = si.gql('''mutation($l:String!){ shopLocaleUpdate(locale:$l, shopLocale:{published:true}){ shopLocale{ locale published } userErrors{ message } } }''', {'l': loc})
    print('  publikacja:', r['shopLocaleUpdate'])

for loc in locales:
    data = json.load(open(os.path.join(HERE, 'translations', f'{loc}.json'), encoding='utf-8'))
    print('==', loc)
    if not only or 'products' in only: do_products(loc, data)
    if not only or 'collections' in only: do_collections(loc, data)
    if not only or 'menu' in only: do_menu(loc, data)
    if not only or 'theme' in only: do_theme(loc, data)
    if publish: do_publish(loc)
