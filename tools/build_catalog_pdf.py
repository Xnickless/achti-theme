#!/usr/bin/env python3
"""Katalog PDF B2B z produktów w sklepie (dane z Admin API, zdjęcia z folderu lokalnego).
Dwie wersje: bez cen (dla gości) i z cenami netto (dla zalogowanych firm).
Użycie: python3 tools/build_catalog_pdf.py [--upload]
  --upload  wgrywa oba PDF do Shopify → Pliki i wypisuje adresy (do ustawień motywu „B2B — dostęp do cen”).
Wynik: ~/Downloads/achti-katalog-b2b.pdf, ~/Downloads/achti-katalog-b2b-ceny.pdf"""
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

SECTIONS = [  # (tytuł, funkcja klasyfikująca) — kolejność ma znaczenie, produkt trafia do pierwszej pasującej
    ('Kominy i opaski', lambda p: p['type'] == 'Komin' or p['title'].startswith('Komin') or 'kominy' in p['tags'] or p['headband']),
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
    .cover h1 { font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: 34pt; line-height: 1.1; margin: 0 0 6mm; }
    .cover .sub { font-size: 12pt; color: #5f5a55; max-width: 120mm; line-height: 1.5; }
    .cover .meta { font-size: 9.5pt; color: #5f5a55; line-height: 1.6; }
    .cover .note { font-size: 9pt; color: #7b6f64; border-top: 1px solid #ddd6ce; padding-top: 4mm; }
    .head { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e3ded8; padding-bottom: 2mm; margin-bottom: 4mm; }
    .head h2 { font-family: "Fraunces", Georgia, serif; font-weight: 600; font-size: 15pt; margin: 0; }
    .head span { font-size: 8.5pt; color: #7b6f64; letter-spacing: .08em; text-transform: uppercase; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm 5mm; }
    .item { break-inside: avoid; }
    .item .ph { width: 100%; aspect-ratio: 1/1; background: #fff; border-radius: 2mm; overflow: hidden; }
    .item .ph img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .item .code { font-weight: 600; font-size: 9.5pt; margin-top: 2mm; letter-spacing: .04em; }
    .item .name { font-size: 8pt; color: #3d3a37; line-height: 1.3; min-height: 2.6em; max-height: 2.6em; overflow: hidden; }
    .item .spec { font-size: 7.5pt; color: #7b6f64; line-height: 1.35; margin-top: .8mm; }
    .item .price { font-size: 9.5pt; font-weight: 600; margin-top: 1mm; }
    .foot { position: absolute; left: 14mm; right: 14mm; bottom: 7mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #7b6f64; border-top: 1px solid #e3ded8; padding-top: 2mm; }
    .toc { font-size: 11pt; line-height: 2; }
    '''
    pages = []
    title = 'Katalog B2B' + (' — cennik hurtowy' if with_prices else '')
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
                spec = ' · '.join(x for x in (p['material'], p['size']) if x)
                price = f'<div class="price">{float(p["price"]):.2f} zł netto</div>' if with_prices else ''
                cells.append(f'''<div class="item"><div class="ph"><img src="{photo_data(p['sku'])}"></div>
                  <div class="code">{html.escape(p['sku'])}</div><div class="name">{html.escape(p['title'])}</div>
                  <div class="spec">{html.escape(spec)}</div>{price}</div>''')
            body_pages.append(f'''<div class="page"><div class="head"><h2>{sec_title}</h2><span>{i + 1}–{i + len(chunk)} z {len(items)}</span></div>
              <div class="grid">{''.join(cells)}</div><div class="foot"><span>Achti · Katalog B2B {SEASON}</span><span>{SHOP_URL}</span><span>{page_no}</span></div></div>''')
    rest = sorted([p for p in prods if p['sku'] not in used], key=lambda p: sku_key(p['sku']))
    if rest: print('UWAGA: produkty poza sekcjami:', [p['sku'] for p in rest])
    toc_html = ''.join(f'<div>{t} <span style="color:#7b6f64">— {n} modeli, str. {pg}</span></div>' for t, n, pg in toc)
    pages.append(f'''<div class="page cover"><div><img class="logo" src="{LOGO_URL}"></div>
      <div><h1>{title}<br>{SEASON}</h1><div class="sub">Czapki zimowe, kominy i opaski. Polska produkcja, dzianiny premium, własne wzory.
      {'Ceny netto w PLN, bez VAT. Rabaty ilościowe według warunków współpracy.' if with_prices else 'Ceny hurtowe dostępne po zalogowaniu na platformie B2B.'}</div>
      <div class="toc" style="margin-top:8mm">{toc_html}</div></div>
      <div class="meta">Platforma B2B: {SHOP_URL}<br>Rejestracja firmy (NIP / VAT UE): {SHOP_URL}/pages/rejestracja · po akceptacji konta ceny hurtowe i zamówienia online<br>Kod z katalogu wpisany w wyszukiwarkę sklepu prowadzi do produktu · Wysyłka do krajów UE · Aktualizacja: {today}</div>
      <div class="note">Cała oferta realizowana jest na zamówienie; modele oznaczone w sklepie jako „Dostępny od ręki” wysyłamy z magazynu. Zdjęcia poglądowe, kolory mogą różnić się od rzeczywistych.</div></div>''')
    pages += body_pages
    return f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Jost:wght@400;500;600&display=swap"><style>{css}</style></head><body>{"".join(pages)}</body></html>'

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

if __name__ == '__main__':
    if '--upload-only' in sys.argv:
        for name in ('achti-katalog-b2b.pdf', 'achti-katalog-b2b-ceny.pdf'):
            print(name, '->', upload(os.path.join(OUT_DIR, name)))
        sys.exit()
    prods = fetch(); print('produktów:', len(prods))
    for p in prods:
        p['headband'] = bool(re.search(r'opask|headband', p['title'], re.I))
    outs = []
    for with_prices, name in ((False, 'achti-katalog-b2b.pdf'), (True, 'achti-katalog-b2b-ceny.pdf')):
        h = build_html(prods, with_prices); hp = os.path.join(OUT_DIR, name.replace('.pdf', '.html')); open(hp, 'w', encoding='utf-8').write(h)
        pp = os.path.join(OUT_DIR, name); to_pdf(hp, pp); os.remove(hp); outs.append(pp)
        print(name, f'{os.path.getsize(pp) / 1e6:.1f} MB')
    if '--upload' in sys.argv:
        for pp in outs:
            print(os.path.basename(pp), '->', upload(pp))
