#!/usr/bin/env python3
"""Katalog PDF B2B z produktów w sklepie (dane z Admin API, zdjęcia z folderu lokalnego).
Dwie wersje: bez cen (dla gości) i z cenami netto (dla zalogowanych firm).
Użycie: python3 tools/build_catalog_pdf.py [--lang=pl|en|de|fr] [--upload]
  --lang    język katalogu (tytuły i skład z tools/translations/<loc>.json — te same tłumaczenia co w sklepie; ceny zawsze PLN netto)
  --upload  wgrywa oba PDF do Shopify → Pliki (cennik pod losową nazwą), usuwa poprzednie pliki tego języka
            i wpisuje adresy do config/settings_data.json (b2b_catalog_pdf[_<loc>] / b2b_catalog_pdf_prices[_<loc>]) — potem push motywu.
Wynik: ~/Downloads/achti-katalog-b2b[-<loc>].pdf, ~/Downloads/achti-katalog-b2b-ceny[-<loc>].pdf
Uruchamiać pythonem z Pillow: /Applications/Xcode.app/Contents/Developer/usr/bin/python3"""
import sys, os, re, json, io, base64, html, datetime, subprocess, collections
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si
from PIL import Image

HOME = os.path.expanduser('~')
PHOTOS = os.path.join(HOME, 'Downloads/ACHTI B2B Full Size - rozjasnione')
OUT_DIR = os.path.join(HOME, 'Downloads')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
LOGO_URL = 'https://cdn.shopify.com/s/files/1/1032/7841/2118/files/achti_poziom_jpg.jpg'
SHOP_URL = 'https://ccucsr-si.myshopify.com'  # docelowo domena klienta
SEASON = '2026/2027'
THUMB = 520  # px szerokości zdjęcia w PDF (waga pliku)
LANG = next((a[7:] for a in sys.argv if a.startswith('--lang=')), 'pl')
SFX = '' if LANG == 'pl' else f'-{LANG}'

T = {  # teksty stałe katalogu
 'pl': dict(title='Katalog B2B', prices=' — cennik hurtowy', sub='Czapki zimowe, kominy i opaski. Polska produkcja, dzianiny premium, własne wzory.',
   sub_prices='Ceny netto w PLN, bez VAT. Rabaty ilościowe według warunków współpracy.', sub_free='Ceny hurtowe dostępne po zalogowaniu na platformie B2B.',
   toc='— {n} modeli, str. {pg}', of='z', net='zł netto', platform='Platforma B2B', reg='Rejestracja firmy (NIP / VAT UE)', reg2='po akceptacji konta ceny hurtowe i zamówienia online',
   code='Kod z katalogu wpisany w wyszukiwarkę sklepu prowadzi do produktu', ship='Wysyłka do krajów UE', upd='Aktualizacja',
   note='Cała oferta realizowana jest na zamówienie; modele oznaczone w sklepie jako „Dostępny od ręki” wysyłamy z magazynu. Zdjęcia poglądowe, kolory mogą różnić się od rzeczywistych.',
   foot='Achti · Katalog B2B', sections={'Kominy i opaski': 'Kominy i opaski', 'Czapki dziecięce': 'Czapki dziecięce', 'Czapki męskie': 'Czapki męskie', 'Czapki damskie': 'Czapki damskie'}, dec=','),
 'en': dict(title='B2B Catalogue', prices=' — wholesale price list', sub='Winter beanies, snoods and headbands. Made in Poland, premium knits, own designs.',
   sub_prices='Net prices in PLN, excl. VAT. Volume discounts as per terms of cooperation.', sub_free='Wholesale prices available after logging in to the B2B platform.',
   toc='— {n} models, p. {pg}', of='of', net='PLN net', platform='B2B platform', reg='Company registration (Tax ID / EU VAT)', reg2='wholesale prices and online ordering once the account is approved',
   code='Type a catalogue code into the shop search to open the product', ship='Shipping to EU countries', upd='Updated',
   note='The whole range is made to order; models marked “In stock” in the shop ship from our warehouse. Photos are illustrative, colours may differ from the actual product.',
   foot='Achti · B2B Catalogue', sections={'Kominy i opaski': 'Snoods & headbands', 'Czapki dziecięce': "Kids' beanies", 'Czapki męskie': "Men's beanies", 'Czapki damskie': "Women's beanies"}, dec='.'),
 'de': dict(title='B2B-Katalog', prices=' — Großhandelspreisliste', sub='Wintermützen, Loops und Stirnbänder. Hergestellt in Polen, Premium-Strick, eigene Designs.',
   sub_prices='Nettopreise in PLN, zzgl. MwSt. Mengenrabatte gemäß Kooperationsbedingungen.', sub_free='Großhandelspreise nach Anmeldung auf der B2B-Plattform.',
   toc='— {n} Modelle, S. {pg}', of='von', net='PLN netto', platform='B2B-Plattform', reg='Firmenregistrierung (Steuernummer / EU-USt-IdNr.)', reg2='nach Freigabe des Kontos Großhandelspreise und Online-Bestellung',
   code='Katalogcode in die Shop-Suche eingeben, um das Produkt zu öffnen', ship='Versand in EU-Länder', upd='Stand',
   note='Das gesamte Sortiment wird auf Bestellung gefertigt; im Shop als „Sofort verfügbar“ gekennzeichnete Modelle versenden wir ab Lager. Fotos beispielhaft, Farbabweichungen möglich.',
   foot='Achti · B2B-Katalog', sections={'Kominy i opaski': 'Loops & Stirnbänder', 'Czapki dziecięce': 'Kindermützen', 'Czapki męskie': 'Herrenmützen', 'Czapki damskie': 'Damenmützen'}, dec=','),
 'fr': dict(title='Catalogue B2B', prices=' — tarif de gros', sub='Bonnets d’hiver, snoods et bandeaux. Fabrication polonaise, mailles premium, modèles exclusifs.',
   sub_prices='Prix nets en PLN, hors TVA. Remises sur quantité selon les conditions de coopération.', sub_free='Prix de gros disponibles après connexion à la plateforme B2B.',
   toc='— {n} modèles, p. {pg}', of='sur', net='PLN HT', platform='Plateforme B2B', reg='Inscription de l’entreprise (SIREN / TVA UE)', reg2='prix de gros et commande en ligne après validation du compte',
   code='Saisissez un code du catalogue dans la recherche de la boutique pour ouvrir le produit', ship='Livraison dans les pays de l’UE', upd='Mise à jour',
   note='Toute l’offre est fabriquée sur commande ; les modèles signalés « En stock » dans la boutique partent de notre entrepôt. Photos non contractuelles, les couleurs peuvent différer.',
   foot='Achti · Catalogue B2B', sections={'Kominy i opaski': 'Snoods et bandeaux', 'Czapki dziecięce': 'Bonnets enfant', 'Czapki męskie': 'Bonnets homme', 'Czapki damskie': 'Bonnets femme'}, dec=','),
}[LANG]

def translate(prods):
    """Tytuł, skład i rozmiar z tools/translations/<loc>.json (klasyfikacja do sekcji zostaje po danych PL)."""
    if LANG == 'pl': return
    path = os.path.join(os.path.dirname(__file__), 'translations', f'{LANG}.json')
    tr = json.load(open(path, encoding='utf-8'))['products']
    miss = []
    for p in prods:
        t = tr.get(p['sku']) or tr.get(p['sku'].upper())
        if not t: miss.append(p['sku']); continue
        p['title_pl'] = p['title']; p['title'] = t['title']
        mf = t.get('metafields') or {}
        if mf.get('custom.sklad'): p['material'] = mf['custom.sklad']
        if mf.get('custom.rozmiar'): p['size'] = mf['custom.rozmiar']
    if miss: print(f'UWAGA: brak tłumaczenia {LANG} dla', miss[:10], '…' if len(miss) > 10 else '')

SECTIONS = [  # (tytuł, funkcja klasyfikująca) — kolejność ma znaczenie, produkt trafia do pierwszej pasującej
    ('Kominy i opaski', lambda p: p['type'] == 'Komin' or p.get('title_pl', p['title']).startswith('Komin') or 'kominy' in p['tags'] or p['headband']),
    ('Czapki dziecięce', lambda p: 'dzieci' in p['tags']),
    ('Czapki męskie', lambda p: 'meskie' in p['tags'] and 'damskie' not in p['tags']),
    ('Czapki damskie', lambda p: 'damskie' in p['tags']),
]

def rich_text(v):
    try:
        d = json.loads(v); out = []
        def walk(n):
            if isinstance(n, dict):
                if n.get('type') == 'text': out.append(n.get('value', ''))
                for c in n.get('children', []): walk(c)
        walk(d); return ' '.join(out).strip()
    except Exception:
        return v or ''

def fetch():
    prods, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:250, after:$c, query:"status:active"){ nodes{ title handle productType tags
            variants(first:1){ nodes{ sku price } } metafields(first:6, namespace:"custom"){ nodes{ key value } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            v = p['variants']['nodes'][0]; mf = {m['key']: m['value'] for m in p['metafields']['nodes']}
            prods.append(dict(title=p['title'], handle=p['handle'], type=p['productType'], tags=p['tags'], sku=v['sku'] or '', price=v['price'],
                              size=rich_text(mf.get('rozmiar', '')), material=rich_text(mf.get('sklad', '')), headband=False))
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return prods

def photo_data(sku, cache={}):
    """Znajdź zdjęcie po kodzie w nazwie pliku, zmniejsz, zwróć data URL (JPEG)."""
    if not os.path.isdir(PHOTOS): return ''
    files = cache.setdefault('files', sorted(os.listdir(PHOTOS)))
    base = re.sub(r'-(TURBO|BOY|GIRL|BP)$', '', sku)
    cands = [f for f in files if f.upper().startswith(sku.upper() + ' ')] or [f for f in files if f.upper().startswith(base.upper() + ' ')]
    if not cands: return ''
    im = Image.open(os.path.join(PHOTOS, cands[0])).convert('RGB'); im.thumbnail((THUMB, THUMB * 5 // 4))
    # przytnij pusty biały margines góra/dół, żeby czapka była większa w kafelku
    b = io.BytesIO(); im.save(b, 'JPEG', quality=82, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()

def sku_key(s):
    m = re.match(r'AZ-(\d+)(.*)', s or ''); return (int(m.group(1)), m.group(2)) if m else (10**9, s)

def build_html(prods, with_prices):
    today = datetime.date.today().strftime('%d.%m.%Y')
    css = '''
    @page { size: A4; margin: 0; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Jost", "Helvetica Neue", Arial, sans-serif; color: #262626; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .page { width: 210mm; height: 297mm; padding: 12mm 14mm 12mm; page-break-after: always; position: relative; overflow: hidden; }
    .cover { display: flex; flex-direction: column; justify-content: space-between; background: #fff; }
    .cover img.logo { width: 70mm; }
    .cover h1 { font-family: "Tenor Sans", Georgia, serif; font-weight: 400; font-size: 27pt; line-height: 1.15; margin: 0 0 6mm; }
    .cover .sub { font-size: 12pt; color: #5f5a55; max-width: 120mm; line-height: 1.5; }
    .cover .meta { font-size: 9.5pt; color: #5f5a55; line-height: 1.6; }
    .cover .note { font-size: 9pt; color: #7b6f64; border-top: 1px solid #ddd6ce; padding-top: 4mm; }
    .head { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e3ded8; padding-bottom: 2mm; margin-bottom: 4mm; }
    .head h2 { font-family: "Tenor Sans", Georgia, serif; font-weight: 400; font-size: 15pt; margin: 0; }
    .head span { font-size: 8.5pt; color: #7b6f64; letter-spacing: .08em; text-transform: uppercase; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm 5mm; }
    .item { break-inside: avoid; }
    .item .ph { width: 100%; aspect-ratio: 1 / 0.93; background: #fff; border-radius: 2mm; overflow: hidden; }  /* niższe o 4 mm, żeby 2-liniowy skład nie wypychał ceny w stopkę */
    .item .ph img { width: 100%; height: 100%; object-fit: contain; display: block; }  /* zdjęcia 4:5 w kwadracie — całe, bez obcinania pompona */
    .item .code { font-weight: 600; font-size: 9.5pt; margin-top: 2mm; letter-spacing: .04em; }
    .item .name { font-size: 8pt; color: #3d3a37; line-height: 1.3; min-height: 2.6em; max-height: 2.6em; overflow: hidden; }
    .item .spec { font-size: 7.5pt; color: #7b6f64; line-height: 1.35; margin-top: .8mm; max-height: 2.7em; overflow: hidden; }
    .item .price { font-size: 9.5pt; font-weight: 600; margin-top: 1mm; }
    .foot { position: absolute; left: 14mm; right: 14mm; bottom: 7mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #7b6f64; border-top: 1px solid #e3ded8; padding-top: 2mm; }
    .toc { font-size: 11pt; line-height: 2; }
    '''
    pages = []
    title = T['title'] + (T['prices'] if with_prices else '')
    used = set(); per_page = 9; page_no = 1
    toc = []
    body_pages = []
    for sec_title, pred in SECTIONS:
        items = sorted([p for p in prods if p['sku'] not in used and pred(p)], key=lambda p: sku_key(p['sku']))
        for p in items: used.add(p['sku'])
        if not items: continue
        toc.append((sec_title, len(items), page_no + 1))
        for i in range(0, len(items), per_page):
            chunk = items[i:i + per_page]; page_no += 1
            cells = []
            for p in chunk:
                spec = ' · '.join(x for x in (p['material'], (p['size'] or '').replace('-', '\u2011')) if x)  # 52‑54 z twardym łącznikiem
                price = f'<div class="price">{float(p["price"]):.2f}'.replace('.', T['dec']) + f' {T["net"]}</div>' if with_prices else ''
                cells.append(f'''<div class="item"><div class="ph"><img src="{photo_data(p['sku'])}"></div>
                  <div class="code">{html.escape(p['sku'])}</div><div class="name">{html.escape(p['title'])}</div>
                  <div class="spec">{html.escape(spec)}</div>{price}</div>''')
            body_pages.append(f'''<div class="page"><div class="head"><h2>{T['sections'].get(sec_title, sec_title)}</h2><span>{i + 1}–{i + len(chunk)} {T['of']} {len(items)}</span></div>
              <div class="grid">{''.join(cells)}</div><div class="foot"><span>{T['foot']} {SEASON}</span><span>{SHOP_URL}</span><span>{page_no}</span></div></div>''')
    rest = sorted([p for p in prods if p['sku'] not in used], key=lambda p: sku_key(p['sku']))
    if rest: print('UWAGA: produkty poza sekcjami:', [p['sku'] for p in rest])
    toc_html = ''.join(f'<div>{T["sections"].get(t, t)} <span style="color:#7b6f64">{T["toc"].format(n=n, pg=pg)}</span></div>' for t, n, pg in toc)
    pages.append(f'''<div class="page cover"><div><img class="logo" src="{LOGO_URL}"></div>
      <div><h1>{title}<br>{SEASON}</h1><div class="sub">{T['sub']}
      {T['sub_prices'] if with_prices else T['sub_free']}</div>
      <div class="toc" style="margin-top:8mm">{toc_html}</div></div>
      <div class="meta">{T['platform']}: {SHOP_URL}<br>{T['reg']}: {SHOP_URL}/pages/rejestracja · {T['reg2']}<br>{T['code']} · {T['ship']} · {T['upd']}: {today}</div>
      <div class="note">{T['note']}</div></div>''')
    pages += body_pages
    return f'<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tenor+Sans&family=Jost:wght@400;500;600&display=swap"><style>{css}</style></head><body>{"".join(pages)}</body></html>'

def to_pdf(html_path, pdf_path):
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf_path}', '--virtual-time-budget=20000', html_path], check=True, capture_output=True)

def upload(path):
    url = si.staged_upload(path)
    r = si.gql('''mutation($f:[FileCreateInput!]!){ fileCreate(files:$f){ files{ id fileStatus ... on GenericFile { url } } userErrors{ field message } } }''',
               {'f': [{'originalSource': url, 'contentType': 'FILE', 'filename': os.path.basename(path)}]})
    fc = r['fileCreate']
    if fc['userErrors']: return fc
    fid = fc['files'][0]['id']
    import time
    for _ in range(20):  # plik przetwarza się chwilę, url pojawia się po READY
        q = si.gql('query($id:ID!){ node(id:$id){ ... on GenericFile { fileStatus url } } }', {'id': fid})['node']
        if q.get('url'): return q['url']
        time.sleep(3)
    return fc

def upload_and_set(free_pdf, prices_pdf):
    """Wgrywa parę PDF (cennik pod losową nazwą), usuwa poprzednie pliki tego języka i wpisuje adresy do settings_data.json."""
    import secrets, shutil
    r = si.gql('{ files(first:50, query:"filename:achti-katalog-b2b") { nodes { id ... on GenericFile { url } } } }')
    pat = re.compile(r'/files/achti-katalog-b2b(?:-cennik)?' + (SFX + r'(?:-[0-9a-f]{12})?' if SFX else r'(?:-[0-9a-f]{12})?') + r'(?:_[0-9a-f-]{36})?\.pdf')
    old = [n for n in r['files']['nodes'] if n.get('url') and pat.search(n['url'])]
    rnd = os.path.join(OUT_DIR, f'achti-katalog-b2b-cennik{SFX}-{secrets.token_hex(6)}.pdf'); shutil.copy(prices_pdf, rnd)
    urls = {'b2b_catalog_pdf' + SFX.replace('-', '_'): upload(free_pdf), 'b2b_catalog_pdf_prices' + SFX.replace('-', '_'): upload(rnd)}; os.remove(rnd)
    if not all(isinstance(u, str) for u in urls.values()): print('BŁĄD uploadu:', urls); return
    sd = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings_data.json'); txt = open(sd, encoding='utf-8').read()
    for k, u in urls.items():
        txt, n = re.subn(rf'"{k}": "[^"]*"', f'"{k}": "{u}"', txt, count=1)
        if not n:  # klucza jeszcze nie ma w settings_data — dopisz za b2b_catalog_pdf_prices
            txt = txt.replace('"b2b_catalog_pdf_prices": ', f'"{k}": "{u}",\n    "b2b_catalog_pdf_prices": ', 1)
        print(k, '->', u.split('/files/')[-1].split('?')[0])
    open(sd, 'w', encoding='utf-8').write(txt)
    if old:
        d = si.gql('mutation($ids:[ID!]!){ fileDelete(fileIds:$ids){ deletedFileIds userErrors{ message } } }', {'ids': [n['id'] for n in old]})
        print('usunięte poprzednie:', len(d['fileDelete']['deletedFileIds']), d['fileDelete']['userErrors'] or '')
    print('teraz: shopify theme push … --only config/settings_data.json')

if __name__ == '__main__':
    names = (f'achti-katalog-b2b{SFX}.pdf', f'achti-katalog-b2b-ceny{SFX}.pdf')
    if '--upload-only' in sys.argv:
        upload_and_set(*[os.path.join(OUT_DIR, n) for n in names]); sys.exit()
    prods = fetch(); print('produktów:', len(prods), 'język:', LANG)
    for p in prods:
        p['headband'] = bool(re.search(r'opask|headband', p['title'], re.I))
    translate(prods)
    outs = []
    for with_prices, name in ((False, names[0]), (True, names[1])):
        h = build_html(prods, with_prices); hp = os.path.join(OUT_DIR, name.replace('.pdf', '.html')); open(hp, 'w', encoding='utf-8').write(h)
        pp = os.path.join(OUT_DIR, name); to_pdf(hp, pp); os.remove(hp); outs.append(pp)
        print(name, f'{os.path.getsize(pp) / 1e6:.1f} MB')
    if '--upload' in sys.argv:
        upload_and_set(*outs)
