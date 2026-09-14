"""Wykrywanie pompona na packshotach (Gemini, model tekstowy z obrazem) -> tools/pompon.json {SKU: true/false}.
Opaski pomijane (tag `opaski` w achti-produkty.json). Uruchamiać pythonem z Pillow (Xcode). Klucz: ~/.config/achti/gemini_key.
  python3 tools/detect_pompon.py [--force] [--limit=N]   (pomija już ocenione, zapisuje po każdej odpowiedzi)"""
import os, sys, re, json, io, base64, ssl, time, urllib.request, concurrent.futures as cf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.expanduser('~/Downloads/ACHTI B2B Full Size - rozjasnione')
OUT = os.path.join(HERE, 'pompon.json')
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
MODEL = 'gemini-3.5-flash-lite'  # gemini-2.5-flash zwraca 404 (wycofany dla nowych kont)
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
FORCE = '--force' in sys.argv
LIMIT = int(next((a[8:] for a in sys.argv if a.startswith('--limit=')), '0'))
PROMPT = ('Na zdjęciu jest czapka zimowa na białym tle. Czy ma na czubku pompon (kulkę z futerka albo włóczki)? '
          'Odpowiedz wyłącznie jednym słowem: TAK albo NIE.')

def photo_for(sku, files):
    base = re.sub(r'-(TURBO|BOY|GIRL|BP)$', '', sku)
    num = re.match(r'AZ-\d+', sku.upper()).group(0)  # kod zmieniony po imporcie (AZ-3038 -> AZ-3038PC): dopasuj po części liczbowej
    c = ([f for f in files if f.upper().startswith(sku.upper() + ' ')] or [f for f in files if f.upper().startswith(base.upper() + ' ')]
         or [f for f in files if re.match(num + r'(?:[A-Z]*) ', f.upper())])
    return os.path.join(PHOTOS, c[0]) if c else None

def ask(path):
    im = Image.open(path).convert('RGB'); im.thumbnail((512, 640))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=85)
    body = {'contents': [{'parts': [{'text': PROMPT}, {'inlineData': {'mimeType': 'image/jpeg', 'data': base64.b64encode(b.getvalue()).decode()}}]}],
            'generationConfig': {'temperature': 0, 'maxOutputTokens': 5}}
    for i in range(4):
        req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                                     data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120, context=CTX))
            txt = r['candidates'][0]['content']['parts'][0]['text'].strip().upper()
            if txt.startswith('TAK'): return True
            if txt.startswith('NIE'): return False
            print('niejasna odpowiedź:', os.path.basename(path), txt)
        except urllib.error.HTTPError as e:
            print('HTTP', e.code, e.read().decode()[:120]); time.sleep(15 * (i + 1))
        except Exception as e:
            print('ERR', type(e).__name__, str(e)[:100]); time.sleep(5)
    return None

prods = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
res = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) and not FORCE else {}
files = sorted(os.listdir(PHOTOS))
todo = [p for p in prods if 'opaski' not in p.get('tags', []) and p.get('product_type') != 'Opaska' and (FORCE or p['code'] not in res)]
if LIMIT: todo = todo[:LIMIT]
print('do oceny:', len(todo), '(pominięte opaski i już ocenione)')
lock = __import__('threading').Lock()
def work(p):
    path = photo_for(p['code'], files)
    if not path: print('brak zdjęcia', p['code']); return
    v = ask(path)
    if v is None: return
    with lock:
        res[p['code']] = v
        json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(work, todo))
print('ocenione łącznie:', len(res), '| z pomponem:', sum(res.values()), '| bez:', sum(1 for v in res.values() if not v))
