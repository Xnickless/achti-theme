"""Kółka koloru z AI (Gemini, Nano Banana Pro): zdjęcie próbki z karty → czysty kwadrat jak czapka (15.10.2026).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/kolka_ai.py SRC GEM OUT KARTA [--only="SET 1,SET 11"]
      [--obrot=plik:stopnie,…] [--ramka="SET n:y0,x0,y1,x1;…"] [--model=gemini-3-pro-image] [--force] [--uwaga="dodatkowe zdanie do promptu"]
      KARTA = "*" → kolejka kart modeli (kolory ze sklepu wg manifest.json, bez kart z motywami), [--limit=10] [--arkusz=plik.jpg]

Model dostaje wycinek próbki (obrócony ściągaczem w dół, z metką) i wzór Kamila (wzor-kolka-2344.png) i rysuje
kwadrat: dzianina z pasami u góry, ściągacz na dole przez całą szerokość, bez metki i tła. ~0,134 $ za kółko.
"""
import base64
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

import certifi
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pelna_probka import trim_overlaps  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
CTX = ssl.create_default_context(cafile=certifi.where())
WZOR = os.path.join(HERE, 'wzor-kolka-2344.png')

PROMPT = """Instrukcja klienta (PL): „Wytnij kółeczko w każdym kolorze tak, żeby było widać cały obszar czapki: ściągacz + góra dzianiny.”

IMAGE 1 is a photo of ONE knitted fabric sample of a winter hat (a manufacturer's colour card). It has ALREADY been
rotated as the hat is worn: the BOTTOM of IMAGE 1 is the cuff / lower edge of the hat, the TOP is the crown side.
Keep exactly this orientation — do not rotate or flip it. A paper tag with a string lies on it and neighbouring
samples or background may show at the edges.
IMAGE 2 shows the target style: six round swatches, each a close, straight-on view of a hat's fabric — patterned knit
filling the upper ~70 %, the ribbed cuff as a straight horizontal band across the FULL width at the bottom ~25-30 %.

Create ONE square image (it will be cropped to a circle) of THIS sample in exactly that style:
- show the WHOLE height of the sample, scaled proportionally: from the ribs of the cuff at the bottom up to the last
  (top) colour band — every colour band of the sample must be visible, none cropped away;
- reproduce the knit of IMAGE 1 faithfully: the same stitch structure and scale, the same yarn colours and their mix,
  the same order and proportions of colour bands from top to bottom, the same cuff colour and rib width;
- the cuff is a straight, even, horizontal ribbed band spanning the whole width at the bottom, vertical ribs;
- fabric fills the entire square edge to edge: NO tag, string, label, text, background, card, seams, frayed edges,
  folds or neighbouring samples; flat, evenly lit like a studio scan, no shadows, no vignette;
- do not invent new colours or patterns, do not stylise; it must look like a real photograph of the knit;
- COLOUR FIDELITY is the most important rule: every yarn colour must match IMAGE 1 exactly in hue, lightness and
  saturation (a beige band stays the same beige, a grey stays grey — no yellow, green or brighter tints), the same number
  of colour bands with the same heights; never add a band or a colour that is not in IMAGE 1;
- keep the exact stitch structure of each band (ribs stay ribs, plain jersey stays jersey, chenille stays chenille) —
  do not turn one band into another texture;
- IMAGE 2 is ONLY a layout reference (circle filled with fabric, cuff band at the bottom) — take NOTHING else from it:
  no vertical streaks, shading columns or colour gradients that are not in IMAGE 1; colour bands run horizontally
  exactly as on the sample;
- if the sample in IMAGE 1 has NO ribbed cuff (e.g. a plain square swatch): the real hat still has one — add at the
  bottom a lower ribbed band (~15-20 % of the height) knitted from THE SAME yarn and colours as the sample (same mix),
  only the stitch changes to vertical ribs; keep the body's stitch and texture exactly (purl ridges stay purl ridges)."""

PACK_NOTE = """IMAGE 3 is the finished hat of this model, photographed in ANOTHER colour: use it ONLY to see how the cuff and
the knit are built (cuff height, rib type, stitch). Take NO colours from IMAGE 3 — all colours come from IMAGE 1."""
PACK = os.path.expanduser('~/Claude/achti-foto/wyrownane')


REF_NOTE = """IMAGE 4 is an already approved circle of ANOTHER colour of this same model: match its framing, zoom level,
stitch scale and the height of the cuff band exactly, so all colours of the model look consistent. Take NO colours from IMAGE 4."""

QC_PROMPT = """IMAGE 1 is a photo of a knitted hat sample (bottom = cuff side). IMAGE 2 was generated from it and should be a
clean square close-up of the same fabric. Check IMAGE 2 strictly:
1) same colours and the same order of colour bands from bottom to top as IMAGE 1 (none missing, none invented);
2) same stitch / pattern type and similar scale (e.g. chunky purl ridges must not become fine jersey);
3) orientation: the cuff / ribbed band is at the BOTTOM (as in IMAGE 1), bands horizontal;
4) no tag, string, text, background, seams or frayed edges; fabric fills the whole square.
Return JSON {"ok": true|false, "problems": "short English description of what is wrong, empty if ok"}."""


def check(win, out_img):
    """Automatyczna kontrola kółka (gemini-3.5-flash, ~0,1 gr): zgodność kolorów, splotu, kierunku, brak metki."""
    body = {'contents': [{'parts': [part(win), part(out_img), {'text': QC_PROMPT}]}],
            'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.1,
                                 'thinkingConfig': {'thinkingLevel': 'low'}}}
    req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent',
                                 data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120, context=CTX))
        return json.loads(r['candidates'][0]['content']['parts'][-1]['text'])
    except Exception as e:  # noqa: BLE001
        return {'ok': True, 'problems': f'(kontrola nieudana: {type(e).__name__})'}


def packshot(card):
    for code in re.findall(r'AZ-\w+', card):
        p = os.path.join(PACK, f'{code}-wyrownane.jpg')
        if os.path.exists(p):
            im = cv2.imread(p)
            return cv2.resize(im, None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA)


def part(img_bgr):
    ok, buf = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return {'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(buf.tobytes()).decode()}}


def window(img, b, rot, pad=0.02):
    H, W = img.shape[:2]
    y0, x0, y1, x1 = b[0] * H / 1000, b[1] * W / 1000, b[2] * H / 1000, b[3] * W / 1000
    dy, dx = (y1 - y0) * pad, (x1 - x0) * pad
    win = img[max(0, int(y0 - dy)):int(y1 + dy), max(0, int(x0 - dx)):int(x1 + dx)]
    k = {0: 0, 90: -1, 180: 2, 270: 1}[rot % 360]
    win = np.ascontiguousarray(np.rot90(win, k))
    s = 1024 / max(win.shape[:2])
    return cv2.resize(win, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else win


def generate(model, parts, size='2K'):
    cfg = {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '1:1', 'imageSize': size}}
    body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': cfg}).encode()
    for i in range(3):
        req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
                                     data=body, headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=300, context=CTX))
        except urllib.error.HTTPError as e:
            print('HTTP', e.code, e.read().decode()[:200])
            if e.code in (402, 403):
                return None
            time.sleep(10 * (i + 1))
            continue
        except Exception as e:  # noqa: BLE001  timeout / zerwane połączenie — ponów
            print('sieć:', type(e).__name__)
            time.sleep(10 * (i + 1))
            continue
        for p in (r.get('candidates') or [{}])[0].get('content', {}).get('parts', []):
            if 'inlineData' in p:
                return base64.b64decode(p['inlineData']['data'])
        print('brak obrazu', json.dumps(r)[:200])
    return None


def natural(t):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', t)]


def cards_queue(src):
    """Karty modeli w kolejności numerów, z kolorami ze sklepu (manifest.json); bez kart z motywami."""
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    motywy = set(os.listdir(os.path.join(HERE, 'motywy')))
    return [(c, set(man[c])) for c in sorted(man, key=natural)
            if 'AZ-' in c and c not in motywy and os.path.isdir(os.path.join(src, c))]


def boxes_for(src, gem, card, fn):
    """Ramki próbek (wskaz.py --tryb=probka), dociągane z Gemini, gdy ich brak (~5 gr za zdjęcie)."""
    jp = os.path.join(gem, card, fn + '.json')
    if not os.path.exists(jp):
        import wskaz
        for i in range(3):  # model czasem zwraca uszkodzony JSON
            try:
                res, _ = wskaz.ask(os.path.join(src, card, fn), 'gemini-3.5-flash', wskaz.PROMPT_PROBKA)
                break
            except (ValueError, KeyError) as e:
                print('ramki: ponawiam', card, fn, type(e).__name__)
        else:
            return []
        os.makedirs(os.path.dirname(jp), exist_ok=True)
        json.dump(res, open(jp, 'w'), ensure_ascii=False)
    return trim_overlaps(json.load(open(jp)))


def fill_corners(im):
    """Model czasem oddaje ośmiokąt z białymi rogami — przybliżenie, aż rogi są dzianiną."""
    h = im.shape[0]
    for z in (1.0, 0.88, 0.8, 0.72):
        c = int(h * (1 - z) / 2)
        sq = im[c:h - c, c:h - c]
        k = max(4, sq.shape[0] // 14)
        hsv = cv2.cvtColor(sq, cv2.COLOR_BGR2HSV)
        g = cv2.cvtColor(sq, cv2.COLOR_BGR2GRAY).astype(np.float32)
        # tło = jasne, bez koloru i GŁADKIE (jasna przędza ma fakturę, więc się nie łapie)
        white = [((hsv[y:y + k, x:x + k, 2] > 225) & (hsv[y:y + k, x:x + k, 1] < 25)).mean()
                 if g[y:y + k, x:x + k].std() < 6 else 0.0
                 for y in (0, sq.shape[0] - k) for x in (0, sq.shape[1] - k)]
        if max(white) < 0.3:
            return cv2.resize(sq, (h, h), interpolation=cv2.INTER_CUBIC) if c else im
    return im


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    src, gem, out, card = args
    model = opts.get('model') or 'gemini-3-pro-image'
    only = set(opts['only'].split(',')) if opts.get('only') else None
    limit = int(opts.get('limit') or 10 ** 6)
    fix = dict((p.split(':')[0], int(p.split(':')[1])) for p in opts.get('obrot', '').split(',') if p)
    boxes = {p.split(':')[0]: [float(v) for v in p.split(':')[1].split(',')] for p in opts.get('ramka', '').split(';') if p}
    wzor = cv2.imread(WZOR)
    # KARTA = nazwa folderu albo „*” = kolejka wszystkich kart modeli (kolory ze sklepu), --limit = ile nowych kółek
    # --kierunki=kierunki-ai.json: karta -> obrót (stopnie w prawo od surowego zdjęcia), ustalony z Kamilem/Adrianem;
    # karty z null (kierunek nieznany) są pomijane
    kier = json.load(open(os.path.join(HERE, opts['kierunki']))) if opts.get('kierunki') else None
    if card == '*' and kier is not None:
        man = json.load(open(os.path.join(HERE, 'manifest.json')))
        queue = [(c, set(man[c])) for c in sorted(kier, key=natural) if kier[c] is not None and os.path.isdir(os.path.join(src, c))]
    elif card == '*':
        queue = cards_queue(src)
    else:  # jedna karta — tylko kolory, które są w sklepie (manifest), jeśli karta tam jest
        man = json.load(open(os.path.join(HERE, 'manifest.json')))
        queue = [(card, set(man[card]) if card in man else None)]
    size = opts.get('size') or '2K'
    qc_all = {}
    if opts.get('najpierw'):  # --najpierw=AZ-2344PC — ta karta na początek kolejki
        queue.sort(key=lambda q: opts['najpierw'] not in q[0])
    made = []
    for card, colors in queue:
        for fn in sorted(os.listdir(os.path.join(src, card))):
            if not fn.lower().endswith(('.jpg', '.jpeg')):
                continue
            if len(made) >= limit:
                break
            img = None
            for s in boxes_for(src, gem, card, fn):
                m = re.search(r'(?:SET|ZESTAW)\W*(\d+)', str(s.get('label', '')).upper())
                if not m or len(made) >= limit:
                    continue
                name = f'SET {int(m.group(1))}'
                dst = os.path.join(out, card, name + '.jpg')
                if (only and name not in only or colors is not None and name not in colors
                        or os.path.exists(dst) and 'force' not in opts):
                    continue
                img = cv2.imread(os.path.join(src, card, fn)) if img is None else img
                kc = kier.get(card) if kier is not None else None  # int albo {"*": domyślny, "IMG_x.JPG": wyjątek}
                if isinstance(kc, dict):
                    kc = kc.get(fn, kc.get('*'))
                rot = kc if kc is not None else fix.get(fn, s.get('rotation', 0))
                win = window(img, boxes.get(name, s['box_2d']), rot)
                os.makedirs(os.path.join(out, card, '_wejscie'), exist_ok=True)
                cv2.imwrite(os.path.join(out, card, '_wejscie', name + '.jpg'), win)
                pk = packshot(card)
                # wzorzec skali: pierwsze gotowe kółko tej karty (spójny kadr wszystkich kolorów modelu)
                done = sorted((f for f in os.listdir(os.path.join(out, card)) if f.startswith('SET ') and f != name + '.jpg'),
                              key=natural) if os.path.isdir(os.path.join(out, card)) else []
                ref = cv2.imread(os.path.join(out, card, done[0])) if done else None
                parts = [part(win), part(wzor), part(pk if pk is not None else wzor)] + ([part(ref)] if ref is not None else [])
                base = PROMPT + ('\n\n' + PACK_NOTE if pk is not None else '') + ('\n\n' + REF_NOTE if ref is not None else '') \
                    + ('\n\n' + opts['uwaga'] if opts.get('uwaga') else '')
                im, qc = None, None
                for attempt in range(2):  # druga próba z uwagami z kontroli
                    txt = base + (f"\n\nA previous attempt had these problems — fix them: {qc['problems']}" if qc else '')
                    data = generate(model, parts + [{'text': txt}], size)
                    if not data:
                        break
                    im = fill_corners(cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR))
                    qc = check(win, cv2.resize(im, (768, 768), interpolation=cv2.INTER_AREA))
                    if qc.get('ok'):
                        break
                if im is None:
                    print('NIE', card, name)
                    continue
                cv2.imwrite(dst, cv2.resize(im, (480, 480), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 90])
                qc_all.setdefault(card, {})[name] = qc
                qp = os.path.join(out, card, '_qc.json')
                old = json.load(open(qp)) if os.path.exists(qp) else {}
                old[name] = qc
                json.dump(old, open(qp, 'w'), ensure_ascii=False, indent=1)
                made.append((card, name))
                print('OK' if qc.get('ok') else 'UWAGA', card, name, '' if qc.get('ok') else qc.get('problems'), flush=True)
    if 'arkusz' in opts and made:
        sheet(out, made, opts['arkusz'])


def sheet(out, made, path):
    """Arkusz do akceptacji: zdjęcie próbki nad kółkiem z AI, po 5 w rzędzie."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 18)
    T = 300
    rows = (len(made) + 4) // 5
    s = Image.new('RGB', (5 * (T + 20), rows * (2 * T + 70)), 'white')
    d = ImageDraw.Draw(s)
    for i, (card, name) in enumerate(made):
        x, y = i % 5 * (T + 20) + 10, i // 5 * (2 * T + 70) + 10
        a = Image.open(os.path.join(out, card, '_wejscie', name + '.jpg'))
        a.thumbnail((T, T))
        s.paste(a, (x + (T - a.width) // 2, y + (T - a.height) // 2))
        b = Image.open(os.path.join(out, card, name + '.jpg')).resize((T, T))
        m = Image.new('L', (T, T))
        ImageDraw.Draw(m).ellipse((0, 0, T - 1, T - 1), fill=255)
        s.paste(b, (x, y + T + 10), m)
        d.text((x + T // 2, y + 2 * T + 18), f"{card.replace('COLORCARD ', '').split()[0]} · {name}", font=f,
               fill='#222', anchor='ma')
    s.save(path, quality=88)
    print('arkusz:', path)


if __name__ == '__main__':
    main()
