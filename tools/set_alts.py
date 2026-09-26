#!/usr/bin/env python3
"""Opisy alternatywne (alt) zdjęć produktów = aktualny tytuł produktu.
Packshoty miały w alt robocze nazwy z pierwszego importu („Czapka Zimowa Damska Beanie Łódź”).
Zdjęcia na modelce (alt z dopiskiem „na modelce”, upload_model_photos.py) dostają „<tytuł> — na modelce”.
Użycie: python3 tools/set_alts.py [--dry-run]. Po zmianie nazw modeli uruchomić ponownie — zmienia tylko niezgodne."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shopify_import as si

DRY = '--dry-run' in sys.argv
MARK = 'na modelce'
products, cursor = [], None
while True:
    r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title media(first:20){ nodes{ id alt } } }
                  pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
    products += r['products']['nodes']
    if not r['products']['pageInfo']['hasNextPage']: break
    cursor = r['products']['pageInfo']['endCursor']

n = 0
for p in products:
    zmiany = []
    for m in p['media']['nodes']:
        want = f"{p['title']} — {MARK}" if MARK in (m['alt'] or '') else p['title']
        if m['alt'] != want:
            zmiany.append({'id': m['id'], 'alt': want})
    if not zmiany: continue
    if DRY:
        if n < 5: print(' ', p['title'], '|', [z['alt'] for z in zmiany])
        n += 1; continue
    r = si.gql('''mutation($pid:ID!,$m:[UpdateMediaInput!]!){ productUpdateMedia(productId:$pid, media:$m){
                  mediaUserErrors{ field message } } }''', {'pid': p['id'], 'm': zmiany})
    err = r['productUpdateMedia']['mediaUserErrors']
    if err: print('  BŁĄD', p['title'], err)
    else: n += 1
print(f'produktów: {len(products)}, ' + ('do zmiany' if DRY else 'zmienione') + f': {n}')
