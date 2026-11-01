#!/usr/bin/env python3
"""Opisy produktów w stylu Adriana (dokument „DO ZROBIENIA DLA KAMILA”, 20.10.2026) — Gemini ogląda packshot czapki
i pisze opis PL + EN/DE/FR na podstawie zdjęcia i danych produktu (bez nazw przędzy, bez konkretnych kolorów).

  python3 tools/opisy_ai.py gen [--codes=AZ-3096PC,…] [--limit=N] [--force] [--workers=6]
  python3 tools/opisy_ai.py apply [--codes=…] [--dry-run]

gen   → tools/opisy-ai.json {kod: {pl|en|de|fr: {lead, p1, p2}}} (pomija gotowe, chyba że --force)
apply → achti-produkty.json pole „opis” = [lead w <strong>, p1, p2], opis w sklepie przez catalog_text.body_for
        (lista cech i specyfikacja bez zmian) + tools/translations/opis-overrides.json dla EN/DE/FR.
        Potem: translate_catalog.py → set_translations.py en fr de --only=products.
"""
import base64
import concurrent.futures as cf
import json
import os
import ssl
import sys
import urllib.request

import certifi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog_text as ct  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'achti-produkty.json')
OUT = os.path.join(HERE, 'opisy-ai.json')
OVR = os.path.join(HERE, 'translations', 'opis-overrides.json')
PACK = os.path.expanduser('~/Claude/achti-foto/wyrownane')
KEY = open(os.path.expanduser('~/.config/achti/gemini_key')).read().strip()
CTX = ssl.create_default_context(cafile=certifi.where())
MODEL = 'gemini-3.5-flash'

WZOR = """Stylowa czapka zimowa z wyrazistym wzorem i efektownym pomponem, łącząca modny wygląd z komfortem noszenia.
Model „Nazwa” wyróżnia się dekoracyjnym, wielokolorowym wzorem inspirowanym zimowymi motywami oraz szerokim, prążkowanym wywinięciem. Miękka, dzianinowa struktura zapewnia wygodne dopasowanie, a duży, puszysty pompon nadaje całości charakterystycznego wyglądu.
To propozycja do kolekcji jesienno-zimowych, doskonale sprawdzająca się w ofercie sklepów odzieżowych, butików oraz marek akcesoriów zimowych."""

PROMPT = """Jesteś copywriterem polskiego producenta czapek zimowych Achti (sprzedaż hurtowa B2B dla sklepów i marek).
Na zdjęciu jest produkt: {kind_pl} {seg_pl} „{name}”.
Dane produktu (pewne, używaj tylko ich i tego, co widać na zdjęciu):
- rodzaj: {kind_pl}; dla kogo: {seg_pl}
- pompon: {pompon}
- podszycie: {podszycie}
- skład: {sklad}
- rozmiar: {size}

Napisz opis DOKŁADNIE w stylu i układzie tego wzoru klienta (3 części):
---
{wzor}
---
Zasady:
1. "lead": jedno zdanie (do 20 słów), które od razu mówi, jaki to produkt i czym się wyróżnia — jak pierwsze zdanie wzoru.
2. "p1": 2–3 zdania zaczynające się od „Model „{name}” wyróżnia się …” — opisz to, co NAPRAWDĘ widać na zdjęciu: rodzaj splotu
   (np. warkocze, prążek, ażur, żakardowy wzór, gruba dzianina, melanż, efekt futerka), krój (np. klasyczna, długa, z wywinięciem,
   beanie), pompon (tylko jeśli dane mówią TAK), wykończenie. Podszycie wspomnij zgodnie z danymi. Nie wymyślaj cech, których nie widać.
3. "p2": jedno zdanie o tym, do jakiej oferty/kolekcji model pasuje (sklepy, butiki, marki akcesoriów) — różne słowa niż we wzorze, nie kopiuj.
4. NIE podawaj konkretnych kolorów (czapka ma wiele wariantów kolorystycznych) — możesz pisać o charakterze: „wielokolorowy wzór”,
   „stonowana kolorystyka” tylko gdy wzór na to wskazuje. NIE używaj nazw przędzy ani marek (VEZUV, VINCI, MADERA, ROMA, TURBO itp.),
   nie podawaj procentów składu, nie pisz o cenie. Bez wykrzykników i superlatywów typu „najlepsza”.
6. Wzór pokazuje TYLKO styl i układ — nie kopiuj z niego zdań ani zwrotów (każdy produkt ma mieć własne sformułowania).
   Nie powtarzaj tego samego słowa w sąsiednich zdaniach (np. „pełne… pełną”). Pisz bezbłędną polszczyzną — sprawdź odmianę
   i polskie znaki (np. „z wygodą”, nie „z wygoda”).
5. Ten sam tekst przetłumacz naturalnie (nie dosłownie) na angielski, niemiecki i francuski — styl katalogu B2B, nazwa modelu bez zmian,
   cudzysłów zgodny z językiem (“Name” / „Name“ / « Name »).
Zwróć wyłącznie JSON: {{"pl": {{"lead": "", "p1": "", "p2": ""}}, "en": {{...}}, "de": {{...}}, "fr": {{...}}}}"""

KIND = {'Czapka': 'czapka zimowa', 'Opaska': 'opaska zimowa', 'Komin': 'komin zimowy'}
SEG = {'Damska': 'damska (dla kobiet)', 'Męska': 'męska (dla mężczyzn)', 'Unisex': 'unisex',
       'Dziecięca': 'dziecięca', 'Chłopięca': 'dla chłopców', 'Dziewczęca': 'dla dziewczynek'}


def load(path, default):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default


def ask(p, pompon):
    photo = os.path.join(PACK, f"{p['code']}-wyrownane.jpg")
    parts = []
    if os.path.exists(photo):
        from PIL import Image
        import io
        im = Image.open(photo).convert('RGB')
        im.thumbnail((900, 900))
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=88)
        parts.append({'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(buf.getvalue()).decode()}})
    kind = ct.product_kind(p.get('product_type'))
    txt = PROMPT.format(kind_pl=KIND.get(kind, 'czapka zimowa'), seg_pl=SEG.get(p.get('segment'), 'damska'), name=p['name'],
                        pompon='brak (opaska)' if kind == 'Opaska' else ('TAK' if pompon else 'NIE'),
                        podszycie=p.get('podszycie') or 'brak danych', sklad=p.get('sklad') or 'brak danych',
                        size=p.get('size') or 'One Size', wzor=WZOR)
    body = {'contents': [{'parts': parts + [{'text': txt}]}],
            'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.6,
                                 'thinkingConfig': {'thinkingLevel': 'medium'}}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                                 data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': KEY})
    r = json.load(urllib.request.urlopen(req, timeout=180, context=CTX))
    out = json.loads(r['candidates'][0]['content']['parts'][-1]['text'])
    for loc in ('pl', 'en', 'de', 'fr'):
        assert all(out[loc].get(k) for k in ('lead', 'p1', 'p2')), loc
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [''])[:2] for a in sys.argv[1:] if a.startswith('--'))
    cmd = args[0] if args else 'gen'
    data = load(DATA, [])
    codes = set(opts['codes'].split(',')) if opts.get('codes') else None
    todo = [p for p in data if not codes or p['code'] in codes]
    res = load(OUT, {})
    if cmd == 'gen':
        pompon = load(os.path.join(HERE, 'pompon.json'), {})
        todo = [p for p in todo if p['code'] not in res or 'force' in opts][:int(opts.get('limit') or 10 ** 6)]
        print(len(todo), 'opisów do napisania')

        def run(p):
            for _ in range(3):
                try:
                    return p['code'], ask(p, pompon.get(p['code']))
                except Exception as e:  # noqa: BLE001
                    err = e
            return p['code'], 'BŁĄD ' + str(err)[:120]

        with cf.ThreadPoolExecutor(int(opts.get('workers') or 6)) as ex:
            for code, out in ex.map(run, todo):
                if isinstance(out, str):
                    print(code, out)
                    continue
                res[code] = out
                json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                print('ok', code, '—', out['pl']['lead'][:90], flush=True)
        return
    if cmd == 'apply':
        sys.path.insert(0, HERE)
        import shopify_import as si
        ovr = load(OVR, {})
        n = 0
        for p in todo:
            o = res.get(p['code'])
            if not o:
                continue
            p['opis'] = [f"<strong>{o['pl']['lead']}</strong>", o['pl']['p1'], o['pl']['p2']]
            ovr[p['code']] = {loc: [f"<strong>{o[loc]['lead']}</strong>", o[loc]['p1'], o[loc]['p2']] for loc in ('en', 'de', 'fr')}
            kind = ct.product_kind(p.get('product_type'))
            html = ct.body_for(p['name'], p['segment'], kind, [], p.get('size') or 'One Size', p.get('flags') or [],
                               p['code'], p.get('sklad'), p.get('podszycie'), p['opis'])
            p['body_html'] = html
            n += 1
            if 'dry-run' in opts:
                if n <= 2:
                    print(html[:600], '\n')
                continue
            r = si.gql('mutation($p:ProductUpdateInput!){ productUpdate(product:$p){ userErrors{ message } } }',
                       {'p': {'id': p['shop_id'], 'descriptionHtml': html}})
            if r['productUpdate']['userErrors']:
                print('BŁĄD', p['code'], r['productUpdate']['userErrors'])
        if 'dry-run' not in opts:
            json.dump(data, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            json.dump(ovr, open(OVR, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('opisów:', n, '(próba)' if 'dry-run' in opts else '')


if __name__ == '__main__':
    main()
