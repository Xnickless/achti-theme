#!/usr/bin/env python3
"""Podmiana metki: wycina prawdziwą blaszkę ACHTI z packshotu i wkleja ją w wygenerowane zdjęcie.

Model obrazowy nie potrafi napisać tak małego tekstu (wychodzi „AORITI”), więc blaszkę wklejamy
pikselowo. Położenie na obu zdjęciach wykrywa gemini-3.1-pro-preview (bounding box 0-1000).

  python3 tools/podmien_metke.py --foto=<wygenerowane.png> [--code=AZ-2937] [--out=...] [--debug]

Uruchamiać pythonem z Pillow: ~/Claude/achti-foto/venv/bin/python
"""
import sys, os, io, json, base64, urllib.request, urllib.error
from PIL import Image, ImageEnhance, ImageFilter, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_import import _ssl_ctx

CTX = _ssl_ctx()
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
PACK = os.path.expanduser('~/Claude/achti-foto/wyrownane')
DETEKTOR = 'gemini-3.1-pro-preview'
ARGS = {a.split('=', 1)[0]: a.split('=', 1)[1] for a in sys.argv if a.startswith('--') and '=' in a}


def bbox(path, maxpx=1600):
    """Zwraca (x0, y0, x1, y1) blaszki w pikselach oryginału albo None."""
    im = Image.open(path).convert('RGB')
    W, H = im.size
    small = im.copy(); small.thumbnail((maxpx, maxpx))
    buf = io.BytesIO(); small.save(buf, 'JPEG', quality=92)
    prompt = ('Find the small rectangular metal brand plate attached to the knitted hat in this photo. '
              'Return ONLY compact JSON: {"box_2d":[ymin,xmin,ymax,xmax]} normalized to 0-1000. '
              'If there is no plate, return {"box_2d":null}.')
    body = {'contents': [{'parts': [
        {'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(buf.getvalue()).decode()}},
        {'text': prompt}]}], 'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json'}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{DETEKTOR}:generateContent',
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
    r = json.load(urllib.request.urlopen(req, timeout=180, context=CTX))
    txt = ''.join(x.get('text', '') for x in r['candidates'][0]['content']['parts'])
    d = json.loads(txt)
    box = d.get('box_2d') or d.get('box_2') or d.get('box')
    if not box:
        return None
    ymin, xmin, ymax, xmax = box
    return (int(xmin / 1000 * W), int(ymin / 1000 * H), int(xmax / 1000 * W), int(ymax / 1000 * H))


def dopasuj_kolor(src, dst_patch):
    """Zrównuje jasność i temperaturę wklejanej blaszki z otoczeniem w zdjęciu docelowym."""
    s = ImageStat.Stat(src.convert('RGB')).mean
    d = ImageStat.Stat(dst_patch.convert('RGB')).mean
    out = src.convert('RGB')
    if s[0] and s[1] and s[2]:
        r, g, b = out.split()
        r = r.point(lambda v: min(255, int(v * (d[0] / s[0]) ** 0.75)))
        g = g.point(lambda v: min(255, int(v * (d[1] / s[1]) ** 0.75)))
        b = b.point(lambda v: min(255, int(v * (d[2] / s[2]) ** 0.75)))
        out = Image.merge('RGB', (r, g, b))
    return out


def main():
    foto = ARGS.get('--foto')
    if not foto or not os.path.exists(foto):
        print(__doc__); return
    code = ARGS.get('--code') or os.path.basename(foto).split('_')[0]
    pack = f'{PACK}/{code}-wyrownane.jpg'
    if not os.path.exists(pack):
        print('brak packshotu', pack); return

    b_src = bbox(pack)
    b_dst = bbox(foto)
    if not b_src or not b_dst:
        print('nie wykryto blaszki', 'packshot' if not b_src else '', 'zdjęcie' if not b_dst else ''); return

    im = Image.open(foto).convert('RGB')
    src = Image.open(pack).convert('RGB')

    # wykryty prostokąt bywa mniejszy niż narysowana blaszka — powiększamy go, żeby zakryć „duchy” liter
    dw0, dh0 = b_dst[2] - b_dst[0], b_dst[3] - b_dst[1]
    if dw0 < 6 or dh0 < 3:
        print('blaszka za mała, pomijam', dw0, dh0); return
    px, py = int(dw0 * 0.20), int(dh0 * 0.60)
    box_d = (b_dst[0] - px, b_dst[1] - py, b_dst[2] + px, b_dst[3] + py)
    dw, dh = box_d[2] - box_d[0], box_d[3] - box_d[1]

    sw0, sh0 = b_src[2] - b_src[0], b_src[3] - b_src[1]
    sx, sy = int(sw0 * 0.20), int(sh0 * 0.60)
    plate = src.crop((b_src[0] - sx, b_src[1] - sy, b_src[2] + sx, b_src[3] + sy)).resize((dw, dh), Image.LANCZOS)

    dst_patch = im.crop(box_d)
    plate = dopasuj_kolor(plate, dst_patch)
    plate = ImageEnhance.Sharpness(plate).enhance(1.15)

    # maska: pełna blaszka kryje, wąski pas dzianiny dookoła przechodzi miękko w tło
    feather = max(1.5, dw * 0.06)
    mask = Image.new('L', (dw, dh), 0)
    inset_x, inset_y = max(1, int(px * 0.5)), max(1, int(py * 0.5))
    Image.Image.paste(mask, Image.new('L', (max(1, dw - 2 * inset_x), max(1, dh - 2 * inset_y)), 255), (inset_x, inset_y))
    mask = mask.filter(ImageFilter.GaussianBlur(feather))

    im.paste(plate, (box_d[0], box_d[1]), mask)
    cx, cy = (b_dst[0] + b_dst[2]) // 2, (b_dst[1] + b_dst[3]) // 2
    out = ARGS.get('--out') or foto.replace('.png', '-ok.png')
    im.save(out)
    print('OK  ', os.path.basename(out), f'blaszka {dw0}x{dh0} px w {im.size[0]}x{im.size[1]}')
    if '--debug' in sys.argv:
        z = im.crop((max(0, cx - dw * 4), max(0, cy - dh * 4), cx + dw * 4, cy + dh * 4))
        z = z.resize((z.width * 3, z.height * 3), Image.LANCZOS)
        z.save('/tmp/metka-zoom.jpg', quality=95)
        print('zoom -> /tmp/metka-zoom.jpg')


if __name__ == '__main__':
    main()
