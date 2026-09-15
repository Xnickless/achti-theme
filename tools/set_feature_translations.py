"""Tłumaczenia wartości metapola `custom.cechy` (EN/DE/FR) — to one są etykietami filtru „Cechy” na listingu.
  python3 tools/set_feature_translations.py [en fr de] [--dry-run]
Uruchamiać po każdym set_feature_metafield.py (zmiana wartości PL unieważnia tłumaczenie — digest)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

DRY = '--dry-run' in sys.argv
LOCALES = [a for a in sys.argv[1:] if not a.startswith('--')] or ['en', 'fr', 'de']
T = {
    'Z wełną':      {'en': 'With wool',      'de': 'Mit Wolle',      'fr': 'Avec laine'},
    'Wełna merino': {'en': 'Merino wool',    'de': 'Merinowolle',    'fr': 'Laine mérinos'},
    'Z podszyciem': {'en': 'Lined',          'de': 'Gefüttert',      'fr': 'Doublé'},
    'Bez podszycia':{'en': 'Unlined',        'de': 'Ungefüttert',    'fr': 'Non doublé'},
    'Z pomponem':   {'en': 'With pompom',    'de': 'Mit Bommel',     'fr': 'Avec pompon'},
    'Bez pompona':  {'en': 'Without pompom', 'de': 'Ohne Bommel',    'fr': 'Sans pompon'},
}

def cechy_resources():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ translatableResources(first:250, after:$c, resourceType:METAFIELD){
                nodes{ resourceId translatableContent{ key value digest } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})['translatableResources']
        for n in r['nodes']:
            for c in n['translatableContent']:
                v = c['value'] or ''
                if not v.startswith('['): continue
                try: items = json.loads(v)
                except Exception: continue
                if items and all(i in T for i in items):
                    out.append((n['resourceId'], c)); break
        if not r['pageInfo']['hasNextPage']: break
        cursor = r['pageInfo']['endCursor']
    return out

res = cechy_resources()
print('metapól „cechy” do przetłumaczenia:', len(res))
for loc in LOCALES:
    n = 0
    for rid, c in res:
        items = json.loads(c['value'])
        val = json.dumps([T[i][loc] for i in items], ensure_ascii=False)
        if DRY:
            if n < 3: print(f'  [{loc}] {c["value"]} -> {val}')
            n += 1; continue
        r = si.gql('''mutation($id:ID!,$t:[TranslationInput!]!){ translationsRegister(resourceId:$id, translations:$t){ userErrors{ message } } }''',
                   {'id': rid, 't': [{'key': c['key'], 'value': val, 'translatableContentDigest': c['digest'], 'locale': loc}]})
        if r['translationsRegister']['userErrors']: print('BŁĄD', rid, r['translationsRegister']['userErrors'])
        else: n += 1
    print(f'  {loc}: {n}')
