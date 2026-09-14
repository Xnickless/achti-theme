#!/usr/bin/env python3
"""Meta tytuł i opis SEO (PL) dla wszystkich produktów z tools/achti-produkty.json.
Tytuł: „<tytuł> · <kod>” (motyw dokleja „ – Achti”), opis: skład + podszycie + stały ogon, ≤ 160 znaków.
Użycie: python3 tools/set_seo.py [--dry-run] [--only=AZ-1145PC,AZ-910PC]
Potem tłumaczenia: translate_catalog.py + set_translations.py en fr de --only=products (klucze meta_* rejestrują się tylko, gdy PL jest ustawiony)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si

HERE = os.path.dirname(__file__)
DRY = '--dry-run' in sys.argv
ONLY = {x.strip().upper() for a in sys.argv if a.startswith('--only=') for x in a[7:].split(',')}
LINING_SHORT = {'Pełne podszycie polarowe 100% poliester': 'Pełne podszycie polarowe', 'Opaska polarowa 100% poliester': 'Opaska polarowa w środku',
                'Podwójna dzianina': 'Podwójna dzianina', 'Bez podszycia': 'Bez podszycia'}
TAIL = 'Achti — polski producent, hurt B2B, ceny po rejestracji.'

def description(p, limit=160):
    parts = [f"{p['title']} ({p['code']})."]
    sklad = p.get('sklad') or ', '.join(p.get('materials') or [])
    if sklad: parts.append(f"Skład: {sklad}.")
    lin = LINING_SHORT.get(p.get('podszycie') or '')
    if lin: parts.append(f"{lin}.")
    for cut in range(len(parts), 0, -1):
        out = ' '.join(parts[:cut] + [TAIL])
        if len(out) <= limit: return out
    return out[:limit - 1].rstrip() + '…'

products = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
n = 0
for p in products:
    if ONLY and p['code'].upper() not in ONLY: continue
    if not p.get('shop_id'): print('  brak shop_id', p['code']); continue
    seo = {'title': f"{p['title']} · {p['code']}", 'description': description(p)}
    if DRY:
        print(p['code'], '|', seo['title'], '|', len(seo['description']), seo['description']); n += 1; continue
    r = si.gql('mutation($i:ProductInput!){ productUpdate(input:$i){ product{ id } userErrors{ field message } } }',
               {'i': {'id': p['shop_id'], 'seo': seo}})
    err = r['productUpdate']['userErrors']
    if err: print('  BŁĄD', p['code'], err)
    else: n += 1
print('SEO ustawione:' if not DRY else 'do ustawienia:', n)
