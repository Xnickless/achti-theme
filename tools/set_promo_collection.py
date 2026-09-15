"""Zawartość kolekcji „Czapki reklamowe” = lista modeli, na których Achti robi hafty i naszywki
(folder Adriana na Drive „CZAPKI NA KTÓRYCH DA SIĘ ROBIĆ NASZYWKI LUB HAFTY”, 14.09.2026).
Wejście: plik z nazwami zdjęć albo kodami, jeden na wiersz (kod = początek nazwy).
  python3 tools/set_promo_collection.py <plik> [--handle=czapki-reklamowe] [--dry-run]
Kolekcja jest ręczna, więc skrypt dodaje brakujące i usuwa te, których nie ma na liście."""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

DRY = '--dry-run' in sys.argv
HANDLE = next((a[9:] for a in sys.argv if a.startswith('--handle=')), 'czapki-reklamowe')
path = next(a for a in sys.argv[1:] if not a.startswith('--'))

def code_of(line):
    """„AZ-910PC BEZ POM VEZUV …” -> AZ-910PC-BP; „AZ-2033PC … TURBO” -> AZ-2033PC-TURBO."""
    m = re.match(r'(AZ-[0-9]+[A-Z0-9]*)', line.strip().upper())
    if not m: return None
    code = m.group(1)
    rest = line.upper()
    if 'BEZ POM' in rest: code += '-BP'
    elif 'TURBO' in rest: code += '-TURBO'
    elif ' BOY' in rest: code += '-BOY'
    elif ' GIRL' in rest: code += '-GIRL'
    return code

want = []
for line in open(path, encoding='utf-8'):
    c = code_of(line)
    if c and c not in want: want.append(c)
print('kodów na liście:', len(want))

col = si.gql('query($h:String!){ collectionByHandle(handle:$h){ id title products(first:250){ nodes{ id title variants(first:1){ nodes{ sku } } } } } }', {'h': HANDLE})['collectionByHandle']
if not col: sys.exit(f'brak kolekcji {HANDLE}')
in_col = {(p['variants']['nodes'][0]['sku'] or '').upper(): p['id'] for p in col['products']['nodes']}

sku_to_id, cursor = {}, None
while True:
    r = si.gql('query($c:String){ products(first:250, after:$c){ nodes{ id variants(first:1){ nodes{ sku } } } pageInfo{ hasNextPage endCursor } } }', {'c': cursor})['products']
    for p in r['nodes']:
        s = (p['variants']['nodes'][0]['sku'] or '').upper()
        if s: sku_to_id[s] = p['id']
    if not r['pageInfo']['hasNextPage']: break
    cursor = r['pageInfo']['endCursor']

missing = [c for c in want if c not in sku_to_id]
add = [sku_to_id[c] for c in want if c in sku_to_id and c not in in_col]
remove = [pid for sku, pid in in_col.items() if sku not in want]
print(f'w sklepie: {len(want) - len(missing)}/{len(want)} | do dodania: {len(add)} | do usunięcia z kolekcji: {len(remove)}')
if missing: print('  BRAK W SKLEPIE:', missing)
if DRY: sys.exit()
if add:
    r = si.gql('mutation($id:ID!,$ids:[ID!]!){ collectionAddProducts(id:$id, productIds:$ids){ userErrors{ message } } }', {'id': col['id'], 'ids': add})
    print('  dodane:', len(add), r['collectionAddProducts']['userErrors'] or '')
if remove:
    r = si.gql('mutation($id:ID!,$ids:[ID!]!){ collectionRemoveProducts(id:$id, productIds:$ids){ userErrors{ message } } }', {'id': col['id'], 'ids': remove})
    print('  usunięte:', len(remove), r['collectionRemoveProducts']['userErrors'] or '')
print('gotowe')
