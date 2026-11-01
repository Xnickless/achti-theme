#!/usr/bin/env python3
"""Katalog PDF B2B z produktów w sklepie (dane i zdjęcia z Admin API / CDN Shopify, cache w ~/Claude/achti-foto/katalog-cache).
Układ wg szkicu Kamila (27.10.2026): 2 produkty na stronę A4 — po lewej packshot i zdjęcie na modelce, po prawej nazwa, kod,
cena netto, opis + specyfikacja, pod spodem kolorystyka (próbki jak w sklepie: pliki kolor-<kolornik>-<kolor>.jpg).
Gdy kolorów jest więcej niż mieści połówka strony (ACRYLIC 100%), reszta idzie na kolejną połówkę/stronę „kolorystyka — cd.”.
Dwie wersje: bez cen (dla gości) i z cenami netto (dla zalogowanych firm).
Użycie: python3 tools/build_catalog_pdf.py [--lang=pl|en|de|fr] [--upload]
  --lang    język katalogu (tytuły i skład z tools/translations/<loc>.json — te same tłumaczenia co w sklepie; ceny zawsze PLN netto)
  --upload  wgrywa oba PDF do Shopify → Pliki (cennik pod losową nazwą), usuwa poprzednie pliki tego języka
            i wpisuje adresy do config/settings_data.json (b2b_catalog_pdf[_<loc>] / b2b_catalog_pdf_prices[_<loc>]) — potem push motywu.
Wynik: ~/Downloads/achti-katalog-b2b[-<loc>].pdf, ~/Downloads/achti-katalog-b2b-ceny[-<loc>].pdf
Uruchamiać pythonem z Pillow: ~/Claude/achti-foto/venv/bin/python3 (PDF musi mieć < 20 MB — limit plików Shopify)."""
import sys, os, re, json, io, base64, html, datetime, subprocess, collections
sys.path.insert(0, os.path.dirname(__file__)); import shopify_import as si

HOME = os.path.expanduser('~')
PHOTOS = os.path.join(HOME, 'Downloads/ACHTI B2B Full Size - rozjasnione')
OUT_DIR = os.path.join(HOME, 'Downloads')
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
LOGO_URL = 'https://cdn.shopify.com/s/files/1/1032/7841/2118/files/achti_poziom_jpg.jpg'
SHOP_URL = 'https://b2b.achti.com'
CACHE = os.path.join(HOME, 'Claude/achti-foto/katalog-cache')
TIERS = [(24, 8), (40, 10), (65, 13)]  # (maks. próbek pod opisem, próbek w rzędzie) — kółka maleją przy dużej palecie
SW_PER_CONT = 78     # tyle próbek na połówce strony z kontynuacją kolorystyki (6 rzędów po 13; ACRYLIC 100 = 24 + 76)
SEASON = '2026/2027'
LANG = next((a[7:] for a in sys.argv if a.startswith('--lang=')), 'pl')
SFX = '' if LANG == 'pl' else f'-{LANG}'

T = {  # teksty stałe katalogu
 'pl': dict(title='Katalog B2B', prices=' — cennik hurtowy', sub='Czapki zimowe, kominy i opaski. Polska produkcja, dzianiny premium, własne wzory.',
   sub_prices='Ceny netto w PLN, bez VAT. Rabaty ilościowe według warunków współpracy.', sub_free='Ceny hurtowe dostępne po zalogowaniu na platformie B2B.',
   toc='— {n} modeli, str. {pg}', of='z', net='zł netto', platform='Platforma B2B', reg='Rejestracja firmy (NIP / VAT UE)', reg2='po akceptacji konta ceny hurtowe i zamówienia online',
   code='Kod z katalogu wpisany w wyszukiwarkę sklepu prowadzi do produktu', ship='Wysyłka do krajów UE', upd='Aktualizacja',
   note='Cała oferta realizowana jest na zamówienie; modele oznaczone w sklepie jako „Dostępny od ręki” wysyłamy z magazynu. Zdjęcia poglądowe, kolory mogą różnić się od rzeczywistych.',
   foot='Achti · Katalog B2B', colours='Kolorystyka', cont='kolorystyka — cd.', ncol='{n} kolorów', one='Jeden kolor', sections={'Kominy i opaski': 'Kominy i opaski', 'Czapki dziecięce': 'Czapki dziecięce', 'Czapki męskie': 'Czapki męskie', 'Czapki damskie': 'Czapki damskie'}, dec=','),
 'en': dict(title='B2B Catalogue', prices=' — wholesale price list', sub='Winter beanies, snoods and headbands. Made in Poland, premium knits, own designs.',
   sub_prices='Net prices in PLN, excl. VAT. Volume discounts as per terms of cooperation.', sub_free='Wholesale prices available after logging in to the B2B platform.',
   toc='— {n} models, p. {pg}', of='of', net='PLN net', platform='B2B platform', reg='Company registration (Tax ID / EU VAT)', reg2='wholesale prices and online ordering once the account is approved',
   code='Type a catalogue code into the shop search to open the product', ship='Shipping to EU countries', upd='Updated',
   note='The whole range is made to order; models marked “In stock” in the shop ship from our warehouse. Photos are illustrative, colours may differ from the actual product.',
   foot='Achti · B2B Catalogue', colours='Colours', cont='colours — continued', ncol='{n} colours', one='Single colour', sections={'Kominy i opaski': 'Snoods & headbands', 'Czapki dziecięce': "Kids' beanies", 'Czapki męskie': "Men's beanies", 'Czapki damskie': "Women's beanies"}, dec='.'),
 'de': dict(title='B2B-Katalog', prices=' — Großhandelspreisliste', sub='Wintermützen, Loops und Stirnbänder. Hergestellt in Polen, Premium-Strick, eigene Designs.',
   sub_prices='Nettopreise in PLN, zzgl. MwSt. Mengenrabatte gemäß Kooperationsbedingungen.', sub_free='Großhandelspreise nach Anmeldung auf der B2B-Plattform.',
   toc='— {n} Modelle, S. {pg}', of='von', net='PLN netto', platform='B2B-Plattform', reg='Firmenregistrierung (Steuernummer / EU-USt-IdNr.)', reg2='nach Freigabe des Kontos Großhandelspreise und Online-Bestellung',
   code='Katalogcode in die Shop-Suche eingeben, um das Produkt zu öffnen', ship='Versand in EU-Länder', upd='Stand',
   note='Das gesamte Sortiment wird auf Bestellung gefertigt; im Shop als „Sofort verfügbar“ gekennzeichnete Modelle versenden wir ab Lager. Fotos beispielhaft, Farbabweichungen möglich.',
   foot='Achti · B2B-Katalog', colours='Farben', cont='Farben — Fortsetzung', ncol='{n} Farben', one='Eine Farbe', sections={'Kominy i opaski': 'Loops & Stirnbänder', 'Czapki dziecięce': 'Kindermützen', 'Czapki męskie': 'Herrenmützen', 'Czapki damskie': 'Damenmützen'}, dec=','),
 'fr': dict(title='Catalogue B2B', prices=' — tarif de gros', sub='Bonnets d’hiver, snoods et bandeaux. Fabrication polonaise, mailles premium, modèles exclusifs.',
   sub_prices='Prix nets en PLN, hors TVA. Remises sur quantité selon les conditions de coopération.', sub_free='Prix de gros disponibles après connexion à la plateforme B2B.',
   toc='— {n} modèles, p. {pg}', of='sur', net='PLN HT', platform='Plateforme B2B', reg='Inscription de l’entreprise (SIREN / TVA UE)', reg2='prix de gros et commande en ligne après validation du compte',
   code='Saisissez un code du catalogue dans la recherche de la boutique pour ouvrir le produit', ship='Livraison dans les pays de l’UE', upd='Mise à jour',
   note='Toute l’offre est fabriquée sur commande ; les modèles signalés « En stock » dans la boutique partent de notre entrepôt. Photos non contractuelles, les couleurs peuvent différer.',
   foot='Achti · Catalogue B2B', colours='Coloris', cont='coloris — suite', ncol='{n} coloris', one='Coloris unique', sections={'Kominy i opaski': 'Snoods et bandeaux', 'Czapki dziecięce': 'Bonnets enfant', 'Czapki męskie': 'Bonnets homme', 'Czapki damskie': 'Bonnets femme'}, dec=','),
}[LANG]

def translate(prods):
    """Tytuł, opis, skład i rozmiar z tools/translations/<loc>.json (klasyfikacja do sekcji zostaje po danych PL)."""
    if LANG == 'pl': return
    path = os.path.join(os.path.dirname(__file__), 'translations', f'{LANG}.json')
    tr = json.load(open(path, encoding='utf-8'))['products']
    miss = []
    for p in prods:
        t = tr.get(p['sku']) or tr.get(p['sku'].upper())
        if not t: miss.append(p['sku']); continue
        p['title_pl'] = p['title']; p['title'] = t['title']
        if t.get('body_html'): p['body'] = t['body_html']
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

def handleize(t):
    """Jak filtr Liquid handleize (nazwy plików próbek kolorów)."""
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', t.lower())).strip('-')

def swatch_files():
    """nazwa pliku kolor-….jpg → URL w Shopify → Pliki (Shopify dokleja _<uuid> przy duplikatach nazw)."""
    out, cur = {}, None
    while True:
        r = si.gql('query($c:String){ files(first:250, after:$c, query:"filename:kolor-"){ nodes{ ... on MediaImage { image{ url } } } pageInfo{ hasNextPage endCursor } } }', {'c': cur})['files']
        for n in r['nodes']:
            u = (n.get('image') or {}).get('url')
            if not u: continue
            name = re.sub(r'_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=\.)', '', u.split('/')[-1].split('?')[0])
            out.setdefault(name, u)
        if not r['pageInfo']['hasNextPage']: return out
        cur = r['pageInfo']['endCursor']

def fetch():
    files = swatch_files(); print('plików próbek:', len(files))
    prods, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:3, after:$c, query:"status:active"){ nodes{ title handle productType tags descriptionHtml
            variants(first:250){ nodes{ sku price selectedOptions{ name value } } }
            metafields(first:8, namespace:"custom"){ nodes{ key value } }
            media(first:4){ nodes{ alt preview{ image{ url } } } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            vs = p['variants']['nodes']; v = vs[0]; mf = {m['key']: m['value'] for m in p['metafields']['nodes']}
            kol = handleize(mf.get('kolornik') or '')
            colours = []
            code = v['sku'] or ''
            for x in vs:
                val = next((o['value'] for o in x['selectedOptions'] if o['name'].lower() in ('kolor', 'color', 'colour')), None)
                if not val or not kol: continue
                if x['sku'] and x['sku'].endswith('-' + val.replace(' ', '')): code = x['sku'][:-(len(val.replace(' ', '')) + 1)]
                colours.append((val, files.get(handleize(f'kolor-{kol}-{val}') + '.jpg')))
            imgs = [(m['alt'] or '', (m['preview'] or {}).get('image', {}).get('url')) for m in p['media']['nodes']]
            pack = next((u for a, u in imgs if u and 'modelce' not in a), None)
            model = next((u for a, u in imgs if u and 'modelce' in a), None)
            miss = [c for c, u in colours if not u]
            if miss: print('UWAGA: brak pliku próbki', code, miss[:5])
            prods.append(dict(title=p['title'], handle=p['handle'], type=p['productType'], tags=p['tags'], sku=code, price=v['price'],
                              size=rich_text(mf.get('rozmiar', '')), material=rich_text(mf.get('sklad', '')), headband=False,
                              body=p['descriptionHtml'] or '', colours=[(c, u) for c, u in colours if u], probka=kol.startswith('az-'),
                              pack=pack, model=model))
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return prods

def cached(url, width, kind='photo'):
    """Pobiera obraz z CDN Shopify w danej szerokości do cache i przygotowuje go do PDF (Pillow), zwraca file://.
    kind: photo = JPEG q60; circle / square = próbka koloru wypalona na białym tle z obwódką (kółko albo zaokrąglony
    kwadrat z całą próbką) — Chrome nie rysuje wtedy tysięcy krzywych przycięcia, PDF mieści się w limicie 20 MB Shopify."""
    if not url: return ''
    import hashlib, urllib.request
    os.makedirs(CACHE, exist_ok=True)
    u = url + ('&' if '?' in url else '?') + f'width={width}'
    raw = os.path.join(CACHE, hashlib.md5(u.encode()).hexdigest() + '.jpg')
    out = raw[:-4] + f'-{kind}.jpg'
    if os.path.exists(out): return 'file://' + out
    if not os.path.exists(raw):
        for _ in range(3):
            try:
                with urllib.request.urlopen(u, timeout=60, context=si._CTX) as r: data = r.read()
                open(raw, 'wb').write(data); break
            except Exception as e: err = e
        else:
            print('UWAGA: nie pobrano', url, err); return ''
    from PIL import Image, ImageDraw, ImageOps
    im = Image.open(raw).convert('RGB')
    if kind == 'photo':
        im.save(out, 'JPEG', quality=60, optimize=True, progressive=True)
    else:
        S = 3 * width  # rysowanie w 3× i zmniejszenie = gładkie krawędzie
        bg = Image.new('RGB', (S, S), 'white'); mask = Image.new('L', (S, S), 0); d = ImageDraw.Draw(mask)
        if kind == 'circle':
            bg.paste(ImageOps.fit(im, (S, S)), (0, 0)); d.ellipse((0, 0, S - 1, S - 1), fill=255)
        else:
            im = ImageOps.contain(im, (S, S)); bg.paste(im, ((S - im.width) // 2, (S - im.height) // 2)); d.rounded_rectangle((0, 0, S - 1, S - 1), radius=S // 14, fill=255)
        img = Image.composite(bg, Image.new('RGB', (S, S), 'white'), mask)
        ring = ImageDraw.Draw(img); box = (2, 2, S - 3, S - 3)
        (ring.ellipse if kind == 'circle' else lambda b, **k: ring.rounded_rectangle(b, radius=S // 14, **k))(box, outline=(227, 222, 216), width=4)
        img.resize((width, width), Image.LANCZOS).save(out, 'JPEG', quality=70, optimize=True)
    return 'file://' + out

def prefetch(prods):
    from concurrent.futures import ThreadPoolExecutor
    jobs = [(p['pack'], 360) for p in prods] + [(p['model'], 320) for p in prods] + [(u, 120, 'square' if p['probka'] else 'circle') for p in prods for _, u in p['colours']]
    with ThreadPoolExecutor(12) as ex: list(ex.map(lambda j: cached(*j), list(dict.fromkeys(j for j in jobs if j[0]))))

def desc_parts(body):
    """Z opisu produktu: zdanie wstępne (pogrubione), akapit główny, pozycje specyfikacji (bez kodu — jest w nagłówku)."""
    paras = re.findall(r'<p>(.*?)</p>', body, re.S)
    txt = lambda h: html.unescape(re.sub(r'<[^>]+>', '', h)).strip()
    intro = txt(paras[0]) if paras else ''
    main = next((txt(x) for x in paras[1:] if '<strong>' not in x and '✔' not in x), '')
    spec = [txt(li) for li in re.findall(r'<li>(.*?)</li>', body, re.S)]
    spec = [x for x in spec if not re.match(r'(Kod|Code|Code produit|Artikelnummer|Model|Modèle|Modell)\s*:', x, re.I)]
    return intro, main, spec

def sku_key(s):
    m = re.match(r'AZ-(\d+)(.*)', s or ''); return (int(m.group(1)), m.group(2)) if m else (10**9, s)

def swatches(cols, probka):
    kind = 'square' if probka else 'circle'
    return ''.join(f'<div class="sw"><img src="{cached(u, 120, kind)}"><span>{html.escape(c)}</span></div>' for c, u in cols)

def slot_cap(n):
    return next(((cap, cols) for cap, cols in TIERS if n <= cap), TIERS[-1])

def product_slot(p, with_prices):
    intro, main, spec = desc_parts(p['body'])
    cap, cols = slot_cap(len(p['colours']))
    price = (f'<div class="price">{float(p["price"]):.2f}'.replace('.', T['dec']) + f' {T["net"]}</div>') if with_prices else ''
    n = len(p['colours'])
    col_head = f'<div class="colhead">{T["colours"]} <span>{T["ncol"].format(n=n) if n else T["one"]}</span></div>'
    model = f'<div class="ph model"><img src="{cached(p["model"], 320)}"></div>' if p['model'] else ''
    return f'''<div class="slot prod{'' if p['model'] else ' nomodel'}">
      <div class="left"><div class="ph pack"><img src="{cached(p['pack'], 360)}"></div>{model}</div>
      <div class="right">
        <div class="top"><div><div class="code">{html.escape(p['sku'])}</div><h3>{html.escape(p['title'])}</h3></div>{price}</div>
        <p class="intro">{html.escape(intro)}</p><p class="main">{html.escape(main)}</p>
        <ul class="spec">{''.join(f'<li>{html.escape(x)}</li>' for x in spec)}</ul>
        {col_head if n else ''}<div class="grid8 c{cols}" style="grid-template-columns:repeat({cols},1fr)">{swatches(p['colours'][:cap], p['probka'])}</div>
      </div></div>'''

def cont_slot(p, cols):
    return f'''<div class="slot cont"><div class="colhead">{html.escape(p['sku'])} · {html.escape(p['title'])} — {T['cont']}</div>
      <div class="grid13">{swatches(cols, p['probka'])}</div></div>'''

def build_html(prods, with_prices):
    today = datetime.date.today().strftime('%d.%m.%Y')
    css = '''
    @page { size: A4; margin: 0; }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Jost", "Helvetica Neue", Arial, sans-serif; color: #262626; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .page { width: 210mm; height: 297mm; padding: 10mm 12mm 14mm; page-break-after: always; position: relative; overflow: hidden; display: flex; flex-direction: column; }
    .cover { justify-content: space-between; background: #fff; padding: 12mm 14mm; }
    .cover img.logo { width: 70mm; }
    .cover h1 { font-family: "Tenor Sans", Georgia, serif; font-weight: 400; font-size: 27pt; line-height: 1.15; margin: 0 0 6mm; }
    .cover .sub { font-size: 12pt; color: #5f5a55; max-width: 120mm; line-height: 1.5; }
    .cover .meta { font-size: 9.5pt; color: #5f5a55; line-height: 1.6; }
    .cover .note { font-size: 9pt; color: #7b6f64; border-top: 1px solid #ddd6ce; padding-top: 4mm; }
    .toc { font-size: 11pt; line-height: 2; }
    .head { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e3ded8; padding-bottom: 2mm; }
    .head h2 { font-family: "Tenor Sans", Georgia, serif; font-weight: 400; font-size: 13pt; margin: 0; }
    .head span { font-size: 8pt; color: #7b6f64; letter-spacing: .08em; text-transform: uppercase; }
    .slot { height: 128mm; padding: 5mm 0; overflow: hidden; }
    .slot + .slot { border-top: 1px solid #cfc8c0; }
    .prod { display: grid; grid-template-columns: 50mm 1fr; gap: 7mm; }
    .left { display: grid; grid-template-rows: 1fr 1fr; gap: 3mm; height: 118mm; }
    .nomodel .left { grid-template-rows: 1fr; }
    .ph { background: #f2f1ef; overflow: hidden; }
    .ph img { width: 100%; height: 100%; display: block; }
    .pack { background: #fff; border: .2mm solid #ece9e5; }
    .pack img { object-fit: contain; }
    .model img { object-fit: cover; object-position: center 20%; }
    .right { display: flex; flex-direction: column; min-width: 0; height: 118mm; }
    .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 4mm; }
    .code { font-size: 8.5pt; letter-spacing: .08em; color: #7b6f64; }
    h3 { font-family: "Tenor Sans", Georgia, serif; font-weight: 400; font-size: 14pt; margin: .5mm 0 0; line-height: 1.2; }
    .price { font-size: 12pt; font-weight: 600; white-space: nowrap; }
    .intro { font-size: 8.6pt; font-weight: 500; line-height: 1.4; margin: 2.5mm 0 1.2mm; }
    .main { font-size: 8pt; line-height: 1.42; color: #3d3a37; margin: 0; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
    .spec { list-style: none; padding: 0; margin: 2mm 0 0; font-size: 7.6pt; line-height: 1.45; color: #5f5a55; columns: 2; column-gap: 5mm; }
    .spec li { break-inside: avoid; }
    .colhead { font-size: 8pt; letter-spacing: .08em; text-transform: uppercase; margin: auto 0 1.5mm; padding-top: 2.5mm; }
    .colhead span { color: #7b6f64; text-transform: none; letter-spacing: 0; margin-left: 2mm; }
    .grid8 { display: grid; grid-template-columns: repeat(8, 1fr); gap: 1.5mm 2mm; }
    .grid8.c13 { gap: 1mm 1.5mm; } .grid8.c13 .sw span, .grid13 .sw span { font-size: 5.6pt; }
    .cont .colhead { margin: 0 0 3mm; padding: 0; text-transform: none; letter-spacing: 0; font-size: 9.5pt; }
    .grid13 { display: grid; grid-template-columns: repeat(13, 1fr); gap: 2mm 2mm; }
    .sw { text-align: center; min-width: 0; }
    .sw img { width: 100%; aspect-ratio: 1; display: block; }  /* kształt i obwódka wypalone w obrazku (cached) */
    .sw span { display: block; font-size: 6.2pt; line-height: 1.2; margin-top: .6mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .foot { position: absolute; left: 12mm; right: 12mm; bottom: 6mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #7b6f64; border-top: 1px solid #e3ded8; padding-top: 2mm; }
    '''
    title = T['title'] + (T['prices'] if with_prices else '')
    used = set(); page_no = 1; toc = []; body_pages = []
    for sec_title, pred in SECTIONS:
        items = sorted([p for p in prods if p['sku'] not in used and pred(p)], key=lambda p: sku_key(p['sku']))
        for p in items: used.add(p['sku'])
        if not items: continue
        toc.append((sec_title, len(items), page_no + 1))
        slots = []
        for p in items:
            slots.append(product_slot(p, with_prices))
            rest = p['colours'][slot_cap(len(p['colours']))[0]:]
            for i in range(0, len(rest), SW_PER_CONT): slots.append(cont_slot(p, rest[i:i + SW_PER_CONT]))
        for i in range(0, len(slots), 2):
            page_no += 1
            body_pages.append(f'''<div class="page"><div class="head"><h2>{T['sections'].get(sec_title, sec_title)}</h2><span>{SEASON}</span></div>
              {''.join(slots[i:i + 2])}<div class="foot"><span>{T['foot']} {SEASON}</span><span>{SHOP_URL.replace('https://', '')}</span><span>{page_no}</span></div></div>''')
    rest = sorted([p for p in prods if p['sku'] not in used], key=lambda p: sku_key(p['sku']))
    if rest: print('UWAGA: produkty poza sekcjami:', [p['sku'] for p in rest])
    toc_html = ''.join(f'<div>{T["sections"].get(t, t)} <span style="color:#7b6f64">{T["toc"].format(n=n, pg=pg)}</span></div>' for t, n, pg in toc)
    pages = [f'''<div class="page cover"><div><img class="logo" src="{LOGO_URL}"></div>
      <div><h1>{title}<br>{SEASON}</h1><div class="sub">{T['sub']}
      {T['sub_prices'] if with_prices else T['sub_free']}</div>
      <div class="toc" style="margin-top:8mm">{toc_html}</div></div>
      <div class="meta">{T['platform']}: {SHOP_URL}<br>{T['reg']}: {SHOP_URL}/pages/rejestracja · {T['reg2']}<br>{T['code']} · {T['ship']} · {T['upd']}: {today}</div>
      <div class="note">{T['note']}</div></div>''']
    pages += body_pages
    return f'<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tenor+Sans&family=Jost:wght@400;500;600&display=swap"><style>{css}</style></head><body>{"".join(pages)}</body></html>'

def to_pdf(html_path, pdf_path):
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf_path}', '--allow-file-access-from-files', '--virtual-time-budget=60000', html_path], check=True, capture_output=True)

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
    prefetch(prods); print('zdjęcia w cache')
    if '--limit' in ' '.join(sys.argv):
        n = int(next(a[8:] for a in sys.argv if a.startswith('--limit=')))
        keep = set(p['sku'] for p in sorted(prods, key=lambda p: -len(p['colours']))[:2]) | set(p['sku'] for p in prods[:n])
        prods = [p for p in prods if p['sku'] in keep]
    outs = []
    for with_prices, name in ((False, names[0]), (True, names[1])):
        h = build_html(prods, with_prices); hp = os.path.join(OUT_DIR, name.replace('.pdf', '.html')); open(hp, 'w', encoding='utf-8').write(h)
        pp = os.path.join(OUT_DIR, name); to_pdf(hp, pp); os.remove(hp); outs.append(pp)
        print(name, f'{os.path.getsize(pp) / 1e6:.1f} MB')
    if '--upload' in sys.argv:
        upload_and_set(*outs)
