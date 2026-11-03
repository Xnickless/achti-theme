"""Obraca kółka kolorów już wgrane do Shopify → Pliki i podmienia je w miejscu (fileUpdate, ta sama nazwa).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/obroc_pliki.py tools/colorcards/obroty-03-11.json [--dry-run]

JSON: {kolornik: {"SET n" | "*": stopnie przeciwnie do wskazówek zegara}}. Oryginały zapisuje w ~/Claude/achti-foto/obroty-kopia/.
"""
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import shopify_import as si  # noqa: E402
from PIL import Image  # noqa: E402

DRY = '--dry-run' in sys.argv
plan = json.load(open([a for a in sys.argv[1:] if not a.startswith('--')][0]))
BACKUP = os.path.expanduser('~/Claude/achti-foto/obroty-kopia')
os.makedirs(BACKUP, exist_ok=True)


def handleize(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


for card, rules in plan.items():
    if card.startswith('_'):
        continue
    pref = f'kolor-{card}-'
    nodes = si.gql('''query($q:String){ files(first:250, query:$q){ nodes{ id ... on MediaImage { image{ url } } } } }''',
                   {'q': f'filename:{pref}*'})['files']['nodes']
    for n in nodes:
        url = (n.get('image') or {}).get('url') or ''
        fn = url.split('/')[-1].split('?')[0]
        if not fn.startswith(pref):
            continue
        color = fn[len(pref):-4]
        deg = next((d for k, d in rules.items() if k != '*' and handleize(k) == color), rules.get('*'))
        if not deg:
            continue
        print(fn, deg)
        if DRY:
            continue
        raw = subprocess.run(['curl', '-sf', url], capture_output=True, check=True).stdout
        open(os.path.join(BACKUP, fn), 'wb').write(raw)
        im = Image.open(io.BytesIO(raw)).convert('RGB').rotate(deg, expand=True)
        tmp = os.path.join(os.environ.get('TMPDIR', '/tmp'), fn)
        im.save(tmp, quality=92)
        r = si.gql('''mutation($f:[FileUpdateInput!]!){ fileUpdate(files:$f){ userErrors{ field message } } }''',
                   {'f': [{'id': n['id'], 'originalSource': si.staged_upload(tmp)}]})
        if r['fileUpdate']['userErrors']:
            print('  BŁĄD', r['fileUpdate']['userErrors'])
        os.remove(tmp)
