#!/usr/bin/env python3
"""Ustawia ceny wariantów po tagu grupy cenowej (grupa-g3 itd.). Uruchom po imporcie.
Użycie: python3 tools/set_prices.py            (ceny z PRICES)
        python3 tools/set_prices.py --dry-run"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
PRICES={'grupa-g3':'39.00','grupa-g5':'49.00','grupa-g7':'59.00','grupa-g10':'69.00','grupa-g12':'79.00'}
DEFAULT='49.00'
dry='--dry-run' in sys.argv
cursor=None; updated=0
while True:
    d=si.gql('''query($c:String){ products(first:100, after:$c, query:"tag:cena-do-uzupelnienia"){ nodes{ id title tags variants(first:10){ nodes{ id price } } } pageInfo{ hasNextPage endCursor } } }''',{'c':cursor})
    for p in d['products']['nodes']:
        price=next((PRICES[t] for t in p['tags'] if t in PRICES),DEFAULT)
        vs=[v for v in p['variants']['nodes'] if v['price']!=price]
        if not vs: continue
        if dry: print(p['title'],'->',price); updated+=1; continue
        r=si.gql('''mutation($pid:ID!,$v:[ProductVariantsBulkInput!]!){ productVariantsBulkUpdate(productId:$pid, variants:$v){ userErrors{ message } } }''',
            {'pid':p['id'],'v':[{'id':v['id'],'price':price} for v in vs]})
        if r['productVariantsBulkUpdate']['userErrors']: print('błąd',p['title'],r['productVariantsBulkUpdate']['userErrors'])
        else: updated+=1
    pi=d['products']['pageInfo']
    if not pi['hasNextPage']: break
    cursor=pi['endCursor']
print('zaktualizowano produktów:',updated)
