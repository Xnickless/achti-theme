#!/usr/bin/env python3
"""Generuje zdjęcia „na modelce” z packshotów (Gemini image API, klucz w ~/.config/achti/gemini_key).
Użycie: python3 tools/gen_model_photos.py ref <plik_wyj.png> "<opis modelki>"      # wzorzec modelki (tekst → obraz)
        python3 tools/gen_model_photos.py hat <ref.png> <packshot.jpg> <wyj.png> [--model=gemini-3-pro-image] [--kids]"""
import sys, os, json, base64, urllib.request, time, ssl
sys.path.insert(0, os.path.dirname(__file__)); from shopify_import import _ssl_ctx
CTX = _ssl_ctx()
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
MODEL = 'gemini-3-pro-image'
for a in sys.argv:
    if a.startswith('--model='): MODEL = a.split('=', 1)[1]

def part_image(path):
    mime = 'image/png' if path.lower().endswith('.png') else 'image/jpeg'
    return {'inlineData': {'mimeType': mime, 'data': base64.b64encode(open(path, 'rb').read()).decode()}}

def generate(parts, out, aspect='4:5', tries=3):
    body = {'contents': [{'parts': parts}],
            'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect, 'imageSize': '2K'}}}
    if 'flash' in MODEL or 'lite' in MODEL: body['generationConfig']['imageConfig'].pop('imageSize')
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
    for i in range(tries):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300, context=CTX))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]; print('HTTP', e.code, msg); time.sleep(5 * (i + 1)); continue
        for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
            if 'inlineData' in p:
                open(out, 'wb').write(base64.b64decode(p['inlineData']['data'])); return True
        print('brak obrazu w odpowiedzi:', json.dumps(r)[:400]); time.sleep(3)
    return False

PROMPT_HAT = ("Image 1 shows the model. Image 2 shows the product: a knitted winter {what} photographed on white. "
              "Create a professional e-commerce studio photo of exactly the same person from image 1 wearing exactly the product from image 2. "
              "Reproduce the product faithfully and completely: identical knit structure and stitch pattern, identical colours and colour blocks, "
              "the same pompom (size, colour, fluffiness) if present, and the small brand label in the same place. Do not redesign or simplify the product. "
              "Framing: head and shoulders, front view, looking at the camera with a gentle natural expression, hair as in image 1, "
              "the person wears a plain neutral top (light grey or cream), no other accessories, no jewellery. "
              "Lighting: soft, even studio light, no harsh shadows. Background: plain pure white, seamless. Photorealistic, sharp, high detail, 4:5 portrait.")

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'ref':
        ok = generate([{'text': sys.argv[3]}], sys.argv[2]); print('ref', 'ok' if ok else 'BŁĄD', sys.argv[2])
    elif cmd == 'hat':
        ref, hat, out = sys.argv[2], sys.argv[3], sys.argv[4]
        what = 'snood (neck warmer)' if '--snood' in sys.argv else ('headband' if '--headband' in sys.argv else 'hat (beanie)')
        ok = generate([part_image(ref), part_image(hat), {'text': PROMPT_HAT.format(what=what)}], out)
        print('hat', 'ok' if ok else 'BŁĄD', os.path.basename(hat), '->', out)
