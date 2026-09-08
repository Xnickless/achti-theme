#!/usr/bin/env python3
"""Wgrywa tłumaczenia stron i polityk (tools/translations/pages/<locale>/<nazwa>.html) przez translationsRegister.
Źródła (aktualna treść PL ze sklepu) i mapowanie zasobów: tools/translations/pages-src/ (_meta.json).
Użycie: python3 tools/set_page_translations.py en de fr [--dry-run]
Przed wgraniem sprawdza, czy treść PL w sklepie nadal zgadza się z pages-src (digest); jeśli nie — pomija dokument i ostrzega."""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'translations', 'pages-src'); TR = os.path.join(HERE, 'translations', 'pages')
META = json.load(open(os.path.join(SRC, '_meta.json'), encoding='utf-8'))
TITLES = {  # tytuły stron (PAGE) — polityki (SHOP_POLICY) mają tylko body
    'warunki-wspolpracy': {'en': 'Terms of cooperation', 'de': 'Kooperationsbedingungen', 'fr': 'Conditions de collaboration'},
    'faq': {'en': 'FAQ', 'de': 'FAQ', 'fr': 'FAQ'},
    'polityka-cookies': {'en': 'Cookie Policy', 'de': 'Cookie-Richtlinie', 'fr': 'Politique relative aux cookies'},
}
DRY = '--dry-run' in sys.argv
locales = [a for a in sys.argv[1:] if not a.startswith('--')] or ['en', 'de', 'fr']

def current(rtype):
    r = si.gql('query($t:TranslatableResourceType!){ translatableResources(first:20, resourceType:$t){ nodes{ resourceId translatableContent{ key digest value } } } }', {'t': rtype})
    return {n['resourceId']: {c['key']: c for c in n['translatableContent']} for n in r['translatableResources']['nodes']}

state = {**current('SHOP_POLICY'), **current('PAGE')}
for name, m in META.items():
    cm = state.get(m['id'])
    if not cm: print('BRAK zasobu w sklepie:', name); continue
    src_now = cm[m['body_key']]['value']; src_saved = open(os.path.join(SRC, name + '.html'), encoding='utf-8').read()
    if re.sub(r'\s+', ' ', src_now).strip() != re.sub(r'\s+', ' ', src_saved).strip():
        print(f'UWAGA: {name} — treść PL w sklepie zmieniła się od czasu tłumaczenia, pomijam (odśwież pages-src i tłumaczenia)'); continue
    for loc in locales:
        path = os.path.join(TR, loc, name + '.html')
        if not os.path.exists(path): print('brak pliku', path); continue
        body = open(path, encoding='utf-8').read().strip()
        payload = [{'key': m['body_key'], 'value': body, 'translatableContentDigest': cm[m['body_key']]['digest'], 'locale': loc}]
        if 'title' in cm and name in TITLES:
            payload.append({'key': 'title', 'value': TITLES[name][loc], 'translatableContentDigest': cm['title']['digest'], 'locale': loc})
        if DRY: print('[dry]', loc, name, len(body), 'znaków'); continue
        r = si.gql('mutation($id:ID!,$t:[TranslationInput!]!){ translationsRegister(resourceId:$id, translations:$t){ userErrors{ field message } } }', {'id': m['id'], 't': payload})
        errs = r['translationsRegister']['userErrors']
        print(('BŁĄD ' + str(errs)) if errs else 'ok', loc, name)
