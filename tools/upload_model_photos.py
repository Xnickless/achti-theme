#!/usr/bin/env python3
"""Wgrywa zdjęcia „na modelce” z ~/Claude/achti-foto/modelki/sesja jako DRUGIE zdjęcie produktu (packshot zostaje pierwszy).
Kafelek w listingu pokazuje drugie zdjęcie po najechaniu myszką (show_secondary_image w szablonach kolekcji/strony głównej).
Plik <sceneria>_<KOD>_<scena>.png → produkt po SKU. PNG 2K konwertowany do JPEG 1600×2000 (q=88).
Produkt, który ma już zdjęcie z dopiskiem ALT_MARK, jest pomijany; --force podmienia je na nowe.
Uruchamiać pythonem z Pillow: ~/Claude/achti-foto/venv/bin/python3 tools/upload_model_photos.py [--dry-run] [--codes=AZ-1,AZ-2] [--force]
Wynik zapisywany w tools/model-photos.json (kod → plik źródłowy)."""
import glob, json, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shopify_import as si
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser('~/Claude/achti-foto/modelki/sesja')
LOG = os.path.join(HERE, 'model-photos.json')
ALT_MARK = 'na modelce'
DRY = '--dry-run' in sys.argv
FORCE = '--force' in sys.argv
ONLY = {x.strip().upper() for a in sys.argv if a.startswith('--codes=') for x in a[8:].split(',') if x.strip()}

files = {}
for f in sorted(glob.glob(f'{SRC}/*.png')):
    m = re.search(r'_(AZ-[A-Z0-9-]+?)_[a-z_]+\.png$', os.path.basename(f))
    if m and (not ONLY or m.group(1) in ONLY):
        files[m.group(1)] = f
print('zdjęć do wgrania:', len(files))

log = json.load(open(LOG)) if os.path.exists(LOG) else {}
tmp = tempfile.mkdtemp()
for code, path in files.items():
    # sku:AZ-910PC dopasowuje też AZ-910PC-BP (wyszukiwanie po prefiksie) — bierzemy produkt z dokładnie tym kodem
    r = si.gql('''query($q:String){ products(first:10, query:$q){ nodes{ id title variants(first:1){ nodes{ sku } }
                  media(first:20){ nodes{ id alt } } } } }''', {'q': f'sku:{code}'})
    nodes = [n for n in r['products']['nodes'] if n['variants']['nodes'] and n['variants']['nodes'][0]['sku'] == code]
    if not nodes: print('  brak produktu', code); continue
    p = nodes[0]
    mine = [m['id'] for m in p['media']['nodes'] if ALT_MARK in (m['alt'] or '')]
    if mine and not FORCE: print('  jest', code); continue
    alt = f"{p['title']} — {ALT_MARK}"
    if DRY: print('  [dry]', code, p['title'], os.path.basename(path)); continue
    if mine:
        si.gql('mutation($pid:ID!,$ids:[ID!]!){ productDeleteMedia(productId:$pid, mediaIds:$ids){ mediaUserErrors{ message } } }',
               {'pid': p['id'], 'ids': mine})
    jpg = os.path.join(tmp, f'{code}-na-modelce.jpg')
    Image.open(path).convert('RGB').resize((1600, 2000), Image.LANCZOS).save(jpg, quality=88, optimize=True, progressive=True)
    url = si.staged_upload(jpg)
    res = si.gql('''mutation($pid:ID!,$m:[CreateMediaInput!]!){ productCreateMedia(productId:$pid, media:$m){
                    media{ id } mediaUserErrors{ field message } } }''',
                 {'pid': p['id'], 'm': [{'originalSource': url, 'alt': alt, 'mediaContentType': 'IMAGE'}]})
    err = res['productCreateMedia']['mediaUserErrors']
    if err: print('  BŁĄD', code, err); continue
    log[code] = os.path.basename(path)
    print('  OK', code, p['title'])
json.dump(log, open(LOG, 'w'), ensure_ascii=False, indent=1, sort_keys=True)
