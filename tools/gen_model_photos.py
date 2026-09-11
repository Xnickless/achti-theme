#!/usr/bin/env python3
"""Zdjęcia „na modelce” z packshotów (Gemini image API — „nano banana”).

Klucz: ~/.config/achti/gemini_key (projekt gen-lang-client-0310151608).
Modele: gemini-3-pro-image (Nano Banana Pro, najwierniejszy wzór dzianiny, ~0,134 $/zdj.),
        gemini-3.1-flash-image (~0,101 $/zdj. w 2K), gemini-2.5-flash-image (~0,039 $/zdj.).

  python3 tools/gen_model_photos.py refs [--only=kobieta-A,...]   # kandydatki/kandydaci na modelkę (tekst → obraz)
  python3 tools/gen_model_photos.py hat <ref.png> <packshot.jpg> <wyj.png> [--kind=hat|headband|snood]
  python3 tools/gen_model_photos.py batch [--codes=AZ-1,AZ-2] [--limit=20] [--persona=kobieta-A] [--force]
  python3 tools/gen_model_photos.py preview                      # strona HTML do oceny (packshot | modelka)

Wspólne flagi: --model=<id>, --size=1K|2K|4K, --workers=N, --dry-run.
Katalogi: ~/Claude/achti-foto/modelki/{refs,out}, packshoty z ~/Claude/achti-foto/wyrownane.
"""
import sys, os, json, base64, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shopify_import import _ssl_ctx

CTX = _ssl_ctx()
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
ROOT = os.path.expanduser('~/Claude/achti-foto')
REFS, OUT, PACK = f'{ROOT}/modelki/refs', f'{ROOT}/modelki/out', f'{ROOT}/wyrownane'
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'achti-produkty.json')

ARGS = {a.split('=', 1)[0]: a.split('=', 1)[1] for a in sys.argv if a.startswith('--') and '=' in a}
FLAGS = {a for a in sys.argv if a.startswith('--') and '=' not in a}
MODEL = ARGS.get('--model', 'gemini-3-pro-image')
SIZE = ARGS.get('--size', '2K')
WORKERS = int(ARGS.get('--workers', 3))
DRY = '--dry-run' in FLAGS

# Persony: jedna twarz na segment daje spójną serię zdjęć w całym sklepie.
PERSONAS = {
    'kobieta-A': 'a 27-year-old Central European woman with long straight light-brown hair, oval face, natural light makeup, warm friendly look',
    'kobieta-B': 'a 30-year-old Central European woman with shoulder-length wavy dark-blonde hair, soft features, subtle freckles, calm elegant look',
    'kobieta-C': 'a 24-year-old Central European woman with long dark-brown hair, defined cheekbones, clean natural makeup, confident editorial look',
    'kobieta-D': 'a 35-year-old Central European woman with a chin-length light-blonde bob, fine features, minimal makeup, premium editorial look',
    'mezczyzna-A': 'a 32-year-old Central European man with short dark-brown hair and light stubble, friendly relaxed look',
    'mezczyzna-B': 'a 40-year-old Central European man with short greying hair and a trimmed beard, calm confident look',
}
# Który segment katalogu idzie na którą personę (dzieci: patrz uwaga w README/CLAUDE.md).
SEGMENT_PERSONA = {'damskie': 'kobieta-A', 'meskie': 'mezczyzna-A', 'unisex': 'kobieta-A'}

PROMPT_REF = (
    'Professional e-commerce beauty headshot of {desc}. '
    'Head and shoulders, front view, facing camera, gentle natural closed-lip smile, relaxed shoulders. '
    'Plain cream crew-neck knit top, no jewellery, no hat, no scarf. Hair styled naturally and fully visible. '
    'Soft even studio light from the front, no harsh shadows. Seamless pure white background. '
    'Photorealistic, sharp focus, natural skin texture with visible pores, no heavy retouching, 85mm lens, 4:5 portrait.'
)

PROMPT_HAT = (
    'Image 1 shows the model. Image 2 shows the product: a knitted winter {what} photographed on white. '
    'Create a professional e-commerce studio photo of exactly the same person from image 1 wearing exactly the product from image 2. '
    'Reproduce the product faithfully and completely: identical knit structure and stitch pattern, identical colours and colour blocks, '
    'identical proportions and fit, the same pompom (size, colour, fluffiness) if present, and the small metal brand label in the same place. '
    'Do not redesign, recolour or simplify the product. Do not add patterns that are not in image 2. '
    'Framing: head and shoulders, front view, looking at the camera with a gentle natural expression, hair as in image 1 falling naturally around the {what}. '
    'The person wears a plain neutral top (light grey or cream), no other accessories, no jewellery. '
    'Lighting: soft, even studio light, no harsh shadows. Background: plain pure white, seamless. '
    'Photorealistic, sharp, high detail, natural skin texture, 4:5 portrait.'
)


def part_image(path):
    mime = 'image/png' if path.lower().endswith('.png') else 'image/jpeg'
    return {'inlineData': {'mimeType': mime, 'data': base64.b64encode(open(path, 'rb').read()).decode()}}


def generate(parts, out, aspect='4:5', tries=3):
    """Jedno wywołanie API; zapisuje pierwszy obraz z odpowiedzi. Zwraca True/False."""
    cfg = {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': aspect}}
    if 'pro' in MODEL or '3.1' in MODEL:
        cfg['imageConfig']['imageSize'] = SIZE
    body = {'contents': [{'parts': parts}], 'generationConfig': cfg}
    if DRY:
        print('[dry]', os.path.basename(out)); return True
    for i in range(tries):
        req = urllib.request.Request(
            f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300, context=CTX))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            print(f'HTTP {e.code} {os.path.basename(out)} {msg}')
            if e.code == 429:  # limit: czekaj dłużej, nie zasypuj API
                time.sleep(20 * (i + 1)); continue
            time.sleep(5 * (i + 1)); continue
        except Exception as e:
            print('ERR', type(e).__name__, str(e)[:120]); time.sleep(5); continue
        cand = (r.get('candidates') or [{}])[0]
        for p in cand.get('content', {}).get('parts', []):
            if 'inlineData' in p:
                os.makedirs(os.path.dirname(out), exist_ok=True)
                open(out, 'wb').write(base64.b64decode(p['inlineData']['data']))
                return True
        print('brak obrazu:', cand.get('finishReason'), json.dumps(r)[:200])
        time.sleep(3)
    return False


def products():
    """Kody z katalogu + segment (damskie/meskie/dzieci) i typ produktu."""
    d = json.load(open(DATA, encoding='utf-8'))
    items = d if isinstance(d, list) else d.get('products', d)
    out = []
    for p in items:
        code = p.get('code') or p.get('sku')
        if not code:
            continue
        tags = set(p.get('tags') or [])
        seg = 'dzieci' if 'dzieci' in tags else ('meskie' if 'meskie' in tags else 'damskie')
        kind = 'headband' if 'opaski' in tags else 'hat (beanie)'
        out.append({'code': code, 'seg': seg, 'kind': kind, 'name': p.get('name') or p.get('title', '')})
    return out


def packshot(code):
    for name in (f'{code}-wyrownane.jpg', f'{code}.jpg', f'{code}.png'):
        p = os.path.join(PACK, name)
        if os.path.exists(p):
            return p
    return None


def cmd_refs():
    only = set(ARGS.get('--only', '').split(',')) - {''}
    jobs = [(k, v) for k, v in PERSONAS.items() if not only or k in only]
    os.makedirs(REFS, exist_ok=True)

    def one(job):
        k, desc = job
        out = f'{REFS}/{k}.png'
        if os.path.exists(out) and '--force' not in FLAGS:
            print('jest', k); return
        t = time.time()
        ok = generate([{'text': PROMPT_REF.format(desc=desc)}], out)
        print(('OK  ' if ok else 'BŁĄD'), k, f'{time.time()-t:.0f}s')

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, jobs))


def cmd_batch():
    codes = set(ARGS.get('--codes', '').split(',')) - {''}
    limit = int(ARGS.get('--limit', 0))
    forced_persona = ARGS.get('--persona')
    todo = []
    for p in products():
        if codes and p['code'] not in codes:
            continue
        if p['seg'] == 'dzieci' and not forced_persona:
            continue  # zdjęcia dzieci generujemy tylko na wyraźne polecenie (polityka Google + zgody)
        persona = forced_persona or SEGMENT_PERSONA.get(p['seg'], 'kobieta-A')
        ref, pack = f'{REFS}/{persona}.png', packshot(p['code'])
        out = f'{OUT}/{p["code"]}.png'
        if not os.path.exists(ref):
            print('brak wzorca', ref); return
        if not pack:
            print('brak packshotu', p['code']); continue
        if os.path.exists(out) and '--force' not in FLAGS:
            continue
        todo.append((ref, pack, out, p))
    if limit:
        todo = todo[:limit]
    price = {'gemini-3-pro-image': 0.134, 'gemini-3.1-flash-image': 0.101, 'gemini-2.5-flash-image': 0.039}.get(MODEL, 0.1)
    print(f'{len(todo)} zdjęć, model {MODEL}, szacunek ~{len(todo)*price:.2f} USD')

    def one(job):
        ref, pack, out, p = job
        t = time.time()
        ok = generate([part_image(ref), part_image(pack), {'text': PROMPT_HAT.format(what=p['kind'])}], out)
        print(('OK  ' if ok else 'BŁĄD'), p['code'], p['name'], f'{time.time()-t:.0f}s')

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, todo))


def cmd_preview():
    rows = []
    for p in sorted(products(), key=lambda x: x['code']):
        gen_path, pack = f'{OUT}/{p["code"]}.png', packshot(p['code'])
        if not os.path.exists(gen_path):
            continue
        rows.append((p, pack, gen_path))
    html = ['<meta charset="utf-8"><title>Modelki AI — podgląd</title>',
            '<style>body{font-family:system-ui;margin:0;padding:24px;background:#f6f4f1;color:#221f1c}'
            'h1{font-weight:400}.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}'
            '.c{background:#fff;border:1px solid #e1dcd6;border-radius:8px;padding:12px}'
            '.p{display:grid;grid-template-columns:1fr 1fr;gap:8px}img{width:100%;border-radius:4px;display:block}'
            '.n{font-size:13px;color:#5a544e;margin-top:8px}</style>',
            f'<h1>Modelki AI — {len(rows)} zdjęć</h1><div class="g">']
    for p, pack, gen_path in rows:
        html.append(f'<div class="c"><div class="p"><img src="file://{pack}"><img src="file://{gen_path}"></div>'
                    f'<div class="n">{p["code"]} · {p["name"]} · {p["seg"]}</div></div>')
    html.append('</div>')
    dest = f'{ROOT}/modelki/podglad.html'
    open(dest, 'w', encoding='utf-8').write('\n'.join(html))
    print(dest, f'({len(rows)} zdjęć)')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'help'
    if cmd == 'refs':
        cmd_refs()
    elif cmd == 'batch':
        cmd_batch()
    elif cmd == 'preview':
        cmd_preview()
    elif cmd == 'hat':
        kind = ARGS.get('--kind', 'hat (beanie)')
        ok = generate([part_image(sys.argv[2]), part_image(sys.argv[3]), {'text': PROMPT_HAT.format(what=kind)}], sys.argv[4])
        print('OK' if ok else 'BŁĄD', sys.argv[4])
    else:
        print(__doc__)
