"""Gemini wskazuje próbki kolorów na zdjęciach kolorników: wskaz.py SRC CACHE [--model=] [--only=folder,…] [--tryb=set|motyw|probka]

Uruchamiać pythonem z venv achti-foto (certifi). SRC = zdjęcia 2000 px (<SRC>/<folder>/<plik>.JPG), CACHE = <CACHE>/<folder>/<plik>.json
(pomija zdjęcia już opisane). Wynik dla zdjęcia: [{"label": "SET 7" | "203", "box_2d": [ymin, xmin, ymax, xmax]}]
w skali 0–1000. Pole box_2d to fragment samej dzianiny/przędzy danej próbki (bez metek, napisów i krawędzi),
z którego wytnij.py robi kółko.
"""
import base64
import concurrent.futures as cf
import json
import re
import os
import ssl
import sys
import urllib.request

import certifi

CTX = ssl.create_default_context(cafile=certifi.where())
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()

PROMPT = """This photo shows a colour card of a knitwear manufacturer. It is one of two kinds:
A) knitted fabric samples (pieces of a hat) with a hanging tag that says the model code and "SET <number>" — each sample is one colour set;
B) a yarn palette: yarn wraps or knitted squares, each with a printed colour code next to it (e.g. "203", "SC410", "L15994", "17555", "93H", "0M8").

For EVERY colour sample visible in the photo return:
- "label": for kind A exactly "SET <number>" read from the tag attached to THAT sample; for kind B the colour code printed next to/below THAT swatch (copy it exactly, uppercase).
- "box_2d": [ymin, xmin, ymax, xmax] normalised to 0-1000 — a SQUARE-ish region lying ENTIRELY on the fabric/yarn of that sample that best represents its colours and pattern (as large as possible, but never including the tag, printed text, background, card paper, edges, or a neighbouring sample). For kind A prefer the main patterned body of the sample, not the ribbed cuff.
Skip samples whose label you cannot read. Return only a JSON array."""


PROMPT_SET = """This photo shows knitted fabric samples of a hat model (a manufacturer's colour card). Each sample is one
colour set and carries a tag/label that says "SET <number>" (or "ZESTAW <number>"). Samples may be photographed rotated.
A sample often has several colour bands (e.g. top band, middle band, ribbed cuff) - together they ARE the colour set.

For EVERY sample return:
- "label": "SET <number>" read from the tag or printed label belonging to THAT sample.
- "rotation": 0, 90, 180 or 270 - degrees CLOCKWISE to rotate the photo so that the sample looks as the hat is worn:
  colour bands / stripes / pattern rows run HORIZONTALLY and the ribbed cuff (if any) is at the BOTTOM.
- "box_2d": [ymin, xmin, ymax, xmax] (0-1000, in the ORIGINAL unrotated photo) - a rectangle lying entirely on the knitted
  fabric of THAT sample that crosses ALL of its colour bands (from the first band to the last, including the cuff colour),
  is as wide as possible, and contains NO tag, label, string, printed text, paper, background, frayed edge or neighbouring
  sample. If a tag covers part of a band, place the rectangle beside the tag, not over it.
Skip samples whose label you cannot read. Return only a JSON array."""


PROMPT_PROBKA = """This photo shows knitted fabric samples of a hat model (a manufacturer's colour card). Each sample is one
colour set and carries a tag/label that says "SET <number>" (or "ZESTAW <number>"). Samples may be photographed rotated
and may touch or overlap each other slightly.

For EVERY sample return:
- "label": "SET <number>" read from the tag or printed label belonging to THAT sample.
- "rotation": 0, 90, 180 or 270 - degrees CLOCKWISE to rotate the photo so that the sample looks as the hat is worn:
  colour bands / stripes / pattern rows run HORIZONTALLY and the ribbed cuff (if any) is at the BOTTOM.
- "box_2d": [ymin, xmin, ymax, xmax] (0-1000, in the ORIGINAL unrotated photo) - the bounding box of the WHOLE knitted
  piece of THAT sample, edge to edge (all colour bands and the whole cuff), tight to the fabric, without background
  and without the neighbouring samples. Ignore the tag when drawing this box.
- "tag_2d": [ymin, xmin, ymax, xmax] (0-1000) - the bounding box of the paper tag / label (with its string) lying on THAT sample.
Every object MUST contain all four keys: label, rotation, box_2d, tag_2d.
Skip samples whose label you cannot read. Return only a JSON array."""


PROMPT_MOTYW = """This photo shows knitted fabric samples of a hat model (a manufacturer's colour card). Each sample is one
colour set and carries a tag/label that says "SET <number>" (or "ZESTAW <number>"). Samples may be photographed rotated.

For EVERY sample return:
- "label": "SET <number>" read from the tag or printed label belonging to THAT sample.
- "rotation": 0, 90, 180 or 270 - degrees CLOCKWISE to rotate the photo so that the sample looks as the hat is worn
  (pattern rows / colour bands horizontal, ribbed cuff at the bottom, motifs upright).
- "box_2d": [ymin, xmin, ymax, xmax] (0-1000, in the ORIGINAL unrotated photo) - a SQUARE region framing ONE COMPLETE,
  representative motif of the sample (e.g. one whole heart, one whole star, one full repeat of the jacquard / cable /
  cross pattern) centred in the square, with a small margin of the surrounding background knit on every side so the motif
  is not cut. If the sample has no distinct motif (plain or striped knit), frame the area showing all its colours.
  The square must lie entirely on that sample and contain NO tag, label, string, printed text, paper or neighbouring sample.
Skip samples whose label you cannot read. Return only a JSON array."""


def ask(path, model, prompt=PROMPT):
    img = base64.b64encode(open(path, 'rb').read()).decode()
    body = {
        'contents': [{'parts': [{'inline_data': {'mime_type': 'image/jpeg', 'data': img}}, {'text': prompt}]}],
        'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.1,
                             'thinkingConfig': {'thinkingLevel': 'low'}},
    }
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}',
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=180, context=CTX))
    txt = r['candidates'][0]['content']['parts'][-1]['text']
    usage = r.get('usageMetadata', {})
    txt = re.sub(r'"label":\s*"([a-z_0-9]+)":\s*(?=\[)', r'"\1": ', txt)  # usterka modelu: „"label": "tag_2d": [...]”
    return json.loads(txt), usage


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
    src, cache = args
    model = opts.get('model', 'gemini-3.5-flash')
    only = set(opts['only'].split(',')) if 'only' in opts else None
    prompt = {'set': PROMPT_SET, 'motyw': PROMPT_MOTYW, 'probka': PROMPT_PROBKA}.get(opts.get('tryb'), PROMPT)
    # tryb set: tylko karty modeli (foldery z „AZ-” w nazwie)
    if opts.get('tryb') in ('set', 'motyw', 'probka') and not only:
        only = {f for f in os.listdir(src) if 'AZ-' in f}
    jobs = []
    for folder in sorted(os.listdir(src)):
        if only and folder not in only or not os.path.isdir(os.path.join(src, folder)):
            continue
        os.makedirs(os.path.join(cache, folder), exist_ok=True)
        for fn in sorted(os.listdir(os.path.join(src, folder))):
            out = os.path.join(cache, folder, fn + '.json')
            if fn.lower().endswith(('.jpg', '.jpeg')) and not os.path.exists(out):
                jobs.append((os.path.join(src, folder, fn), out))
    print(len(jobs), 'zdjęć do opisania')
    tok = [0, 0]

    def run(job):
        path, out = job
        for _ in range(3):
            try:
                res, usage = ask(path, model, prompt)
                json.dump(res, open(out, 'w'), ensure_ascii=False)
                tok[0] += usage.get('promptTokenCount', 0)
                tok[1] += usage.get('candidatesTokenCount', 0) + usage.get('thoughtsTokenCount', 0)
                return f'{len(res):3d}  {path}'
            except Exception as e:  # noqa: BLE001
                err = e
        return f'BŁĄD {path}: {err}'

    with cf.ThreadPoolExecutor(int(opts.get('workers', 6))) as ex:
        for line in ex.map(run, jobs):
            print(line, flush=True)
    print('tokeny wejście/wyjście:', tok)


if __name__ == '__main__':
    main()
