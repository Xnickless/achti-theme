#!/usr/bin/env python3
"""Zapisuje grupy modeli (tools/model-groups.json: listy nazw plików zdjęć) do metapola custom.inne_kolory
na każdym produkcie grupy. Użycie: python3 tools/set_model_groups.py [--clear]  (--clear czyści pole na wszystkich produktach)."""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si
code_of=lambda f: re.match(r'^(AZ-\d+[A-Z]*)',f).group(1)
sku={}; cursor=None
while True:
    r=si.gql('''query($c:String){ products(first:250, after:$c){ nodes{ id title variants(first:1){ nodes{ sku } } } pageInfo{ hasNextPage endCursor } } }''',{'c':cursor})
    for p in r['products']['nodes']:
        s=(p['variants']['nodes'][0]['sku'] or '').upper()
        if s: sku[s]=p
    if not r['products']['pageInfo']['hasNextPage']: break
    cursor=r['products']['pageInfo']['endCursor']
def setmf(pid, ids):
    d=si.gql('''mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){ userErrors{ field message } } }''',
        {'m':[{'ownerId':pid,'namespace':'custom','key':'inne_kolory','type':'list.product_reference','value':json.dumps(ids)}]})
    return d['metafieldsSet']['userErrors']
if '--clear' in sys.argv:
    n=0
    for p in sku.values(): setmf(p['id'],[]); n+=1
    print('wyczyszczono:',n); sys.exit()
groups=json.load(open(os.path.join(os.path.dirname(__file__),'model-groups.json'))); n=0
for g in groups:
    prods=[sku.get(code_of(f).upper()) for f in g]; prods=[p for p in prods if p]
    if len(prods)<2: continue
    ids=[p['id'] for p in prods]
    for p in prods:
        e=setmf(p['id'],[i for i in ids if i!=p['id']]); n+=1
        if e: print('błąd',p['title'],e)
print('zapisano na produktach:',n)
