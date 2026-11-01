"""Strona HTML z wszystkimi wyciętymi kolorami do akceptacji: podglad.py CROPS OUT.html"""
import base64, io, json, os, re, sys, html
from PIL import Image

crops, out = sys.argv[1:3]
HERE = os.path.dirname(__file__)
manifest = json.load(open(os.path.join(crops, 'manifest.json')))
mapa = json.load(open(os.path.join(HERE, 'mapa.json')))
prods = {p['code']: p for p in json.load(open(os.path.join(HERE, '..', 'achti-produkty.json')))}
tree = json.load(open(os.path.join(HERE, 'drive-tree.json')))
# lokalne nazwy folderów różnią się od Drive (% → _): dopasowanie po nazwie z podmianą
drive_name = {c.replace('%', '_'): c for c in tree['colorcards']}

def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]

def thumb(path):
    im = Image.open(path).convert('RGB').resize((96, 96), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=72)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()

cards = []
for folder in sorted(manifest, key=lambda f: (not f.startswith('COLORCARD AZ'), natural(f))):
    colors = sorted(manifest[folder], key=natural)
    dn = drive_name.get(folder, folder)
    users = sorted(c for c, k in mapa.items() if k == dn)
    cards.append((dn, colors, users, folder))

missing = sorted(set(v for v in mapa.values() if v and v != '?') - {c[0] for c in cards})
sec = []
for dn, colors, users, folder in cards:
    title = re.sub(r'^COLORCARD\s+', '', dn)
    title = re.sub(r'\s+PLEASE USE.*', '', title)
    title = re.sub(r'\s{2,}', ' · ', title)
    kind = 'karta modelu' if all(c.startswith('SET ') for c in colors) else 'paleta przędzy'
    who = ', '.join(f'{u} {html.escape(prods[u]["name"])}' for u in users) if users else 'żadna czapka nie jest jeszcze przypisana'
    sw = ''.join(f'<figure><img src="{thumb(os.path.join(crops, folder, c + ".jpg"))}" alt="{html.escape(c)}" loading="lazy"><figcaption>{html.escape(c)}</figcaption></figure>' for c in colors)
    search = ' '.join([title] + users).lower()
    flag = ' big' if len(colors) > 80 else ''
    sec.append(f'''<section data-q="{html.escape(search)}" class="{kind.split()[0]}{flag}">
<header><h2>{html.escape(title)}</h2><span class="n">{len(colors)} kolorów · {kind}</span></header>
<p class="who"><b>{len(users)} {"czapka" if len(users)==1 else "czapek"}:</b> {who}</p>
{'<p class="warn">Karta dostawcy z całą paletą — czekamy na decyzję Adriana, czy brać wszystkie kolory, czy tylko zaznaczone.</p>' if flag else ''}
<div class="grid">{sw}</div></section>''')

total = sum(len(c[1]) for c in cards)
with_card = sum(1 for v in mapa.values() if v and v != '?')
page = open(os.path.join(HERE, 'podglad.tpl.html')).read()
page = page.replace('{{SECTIONS}}', '\n'.join(sec)).replace('{{TOTAL}}', str(total)).replace('{{CARDS}}', str(len(cards)))
page = page.replace('{{WITH}}', str(with_card)).replace('{{ASK}}', str(sum(1 for v in mapa.values() if v == '?')))
page = page.replace('{{ONE}}', str(sum(1 for v in mapa.values() if v is None)))
if missing:
    page = page.replace('{{MISSING}}', ', '.join(html.escape(re.sub(r'^COLORCARD\s+', '', m)) for m in missing))
else:
    page = re.sub(r'<p class="note">Brakuje.*?</p>', '', page)
open(out, 'w').write(page)
print(out, os.path.getsize(out) // 1024, 'KB; brak wyciętych kart:', len(missing))
