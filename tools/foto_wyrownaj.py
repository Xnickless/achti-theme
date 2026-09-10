#!/usr/bin/env python3
"""Wyrównuje zdjęcia produktów w sklepie: każda czapka przeskalowana do tej samej wysokości (72% kadru, max 80% szerokości)
i postawiona na wspólnej linii podstawy (90% wysokości kadru), białe tło 2000×2500. Dzięki temu kafelki w siatce są równe.

Źródło = aktualne zdjęcie produktu w Shopify (białe tło po obróbce). Oryginały zapisywane do ~/Claude/achti-foto/oryginal/<kod>.jpg,
wyniki do ~/Claude/achti-foto/wyrownane/<kod>-wyrownane.jpg. Nowe zdjęcie wgrywane pod nazwą „<kod>-wyrownane.jpg”,
więc produkty już przerobione są pomijane (po nazwie pliku w URL) — skrypt można uruchamiać ponownie.

Maska tła: zalewanie od rogów po czystej bieli + strefa przejściowa z kluczem jasności (poświata między włóknami pompona).
Wymaga Pillow (venv: python3 -m venv ~/Claude/achti-foto/venv && ~/Claude/achti-foto/venv/bin/pip install pillow).

Użycie: <python z Pillow> tools/foto_wyrownaj.py [--dry-run] [--codes=AZ-1,AZ-2] [--limit=N] [--only=download,process,upload]
"""
import sys, os, re, io, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import shopify_import as si
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 2000, 2500
BOX_H, BOX_W, BASE = 0.72, 0.80, 0.90
ROOT = os.path.expanduser('~/Claude/achti-foto')
ORIG, OUT = os.path.join(ROOT, 'oryginal'), os.path.join(ROOT, 'wyrownane')
os.makedirs(ORIG, exist_ok=True); os.makedirs(OUT, exist_ok=True)
DRY = '--dry-run' in sys.argv
CODES = next((set(a.split('=', 1)[1].split(',')) for a in sys.argv if a.startswith('--codes=')), None)
LIMIT = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--limit=')), None)
ONLY = next((set(a.split('=', 1)[1].split(',')) for a in sys.argv if a.startswith('--only=')), {'download', 'process', 'upload'})

def flood(img, thresh):
    m = img.copy()
    for seed in [(0, 0), (img.width - 1, 0), (0, img.height - 1), (img.width - 1, img.height - 1)]:
        ImageDraw.floodfill(m, seed, (255, 0, 255), thresh=thresh)
    R, G, B = m.split()
    return ImageChops.multiply(ImageChops.multiply(R.point(lambda v: 255 if v == 255 else 0), G.point(lambda v: 255 if v == 0 else 0)), B.point(lambda v: 255 if v == 255 else 0))

def alpha_of(img, lo=234, hi=253):
    """255 = tło. Ciężkie filtry w 1/4 skali."""
    core = flood(img, 10)
    small = img.resize((img.width // 4, img.height // 4), Image.BILINEAR)
    core_s = core.resize(small.size, Image.BILINEAR)
    ext_s = ImageChops.multiply(flood(small, 30), core_s.filter(ImageFilter.MaxFilter(35)))
    ring = ImageChops.subtract(ext_s.filter(ImageFilter.MaxFilter(11)), core_s).resize(img.size, Image.BILINEAR)
    r, g, b = img.split(); mn = ImageChops.darker(ImageChops.darker(r, g), b)
    key = mn.point(lambda v: 0 if v <= lo else 255 if v >= hi else int((v - lo) * 255 / (hi - lo)))
    return ImageChops.lighter(core, ImageChops.multiply(ring, key)).filter(ImageFilter.GaussianBlur(0.8))

def normalize(img):
    img = img.convert('RGB')
    if img.size != (W, H):
        canvas = Image.new('RGB', (W, H), (255, 255, 255)); im2 = img.copy(); im2.thumbnail((W, H), Image.LANCZOS)
        canvas.paste(im2, ((W - im2.width) // 2, (H - im2.height) // 2)); img = canvas
    a = alpha_of(img)
    hat = ImageChops.invert(a).point(lambda v: 255 if v > 40 else 0)
    bb = hat.getbbox()
    if not bb: return None, 'brak obrysu'
    x0, y0, x1, y1 = bb; hw, hh = x1 - x0, y1 - y0
    if hh < H * 0.2: return None, f'obrys za mały ({hw}x{hh})'
    s = min(H * BOX_H / hh, W * BOX_W / hw)
    rgba = img.convert('RGBA'); rgba.putalpha(ImageChops.invert(a))
    crop = rgba.crop(bb).resize((max(1, int(hw * s)), max(1, int(hh * s))), Image.LANCZOS)
    out = Image.new('RGB', (W, H), (255, 255, 255))
    out.paste(crop, ((W - crop.width) // 2, int(H * BASE) - crop.height), crop)
    return out, f'skala {s:.2f}'

def fetch():
    out, cursor = [], None
    while True:
        r = si.gql('''query($c:String){ products(first:100, after:$c){ nodes{ id title variants(first:1){ nodes{ sku } }
            media(first:5){ nodes{ id alt ... on MediaImage { image { url } } } } } pageInfo{ hasNextPage endCursor } } }''', {'c': cursor})
        for p in r['products']['nodes']:
            sku = (p['variants']['nodes'][0]['sku'] or '').upper()
            media = [m for m in p['media']['nodes'] if m.get('image')]
            if not sku or not media: continue
            out.append(dict(id=p['id'], title=p['title'], sku=sku, media=media))
        if not r['products']['pageInfo']['hasNextPage']: break
        cursor = r['products']['pageInfo']['endCursor']
    return out

def main():
    prods = fetch()
    if CODES: prods = [p for p in prods if p['sku'] in CODES]
    todo = [p for p in prods if 'wyrownane' not in p['media'][0]['image']['url']]
    print(f'produktów: {len(prods)}, do zrobienia: {len(todo)}', flush=True)
    if LIMIT: todo = todo[:LIMIT]
    done = skipped = 0
    for i, p in enumerate(todo, 1):
        code = p['sku']; url = p['media'][0]['image']['url']
        src = os.path.join(ORIG, code + '.jpg'); dst = os.path.join(OUT, code + '-wyrownane.jpg')
        try:
            if 'download' in ONLY and not os.path.exists(src):
                with urllib.request.urlopen(url, timeout=60, context=si._CTX) as r: open(src, 'wb').write(r.read())
            if 'process' in ONLY and not os.path.exists(dst):
                out, info = normalize(Image.open(src))
                if out is None: print(f'  {code}: POMINIĘTY ({info})', flush=True); skipped += 1; continue
                out.save(dst, quality=92, optimize=True)
            if 'upload' in ONLY and not DRY:
                staged = si.staged_upload(dst)
                r = si.gql('''mutation($pid:ID!,$m:[CreateMediaInput!]!){ productCreateMedia(productId:$pid, media:$m){ media{ id } mediaUserErrors{ field message } } }''',
                           {'pid': p['id'], 'm': [{'originalSource': staged, 'alt': p['media'][0].get('alt') or p['title'], 'mediaContentType': 'IMAGE'}]})
                errs = r['productCreateMedia']['mediaUserErrors']
                if errs: print(f'  {code}: BŁĄD wgrywania {errs}', flush=True); continue
                old_ids = [m['id'] for m in p['media']]
                si.gql('''mutation($pid:ID!,$ids:[ID!]!){ productDeleteMedia(productId:$pid, mediaIds:$ids){ mediaUserErrors{ field message } } }''', {'pid': p['id'], 'ids': old_ids})
            done += 1
            print(f'{i}/{len(todo)} {code} OK', flush=True)
        except Exception as e:
            print(f'  {code}: BŁĄD {e!r}', flush=True)
    print(f'gotowe: {done}, pominięte: {skipped}' + (' (dry-run: bez wgrywania)' if DRY else ''))

if __name__ == '__main__':
    main()
