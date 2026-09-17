"""Przegląd wariantów kolorystycznych pasa „Nowości" i kafelków produktów — do wyboru przez klienta.
Buduje HTML (+ PDF przez Chrome) z prawdziwymi produktami i zdjęciami ze sklepu.
  python3 tools/warianty_kolorow.py            -> docs/warianty-kolorow.html
Uruchamiać pythonem z Pillow (Xcode). Punkt wyjścia: obecne ustawienie sklepu (pas #e4dfda, kafelki #f5f3f1).
"""
import os, re, io, base64, sys, colorsys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.expanduser('~/Downloads/ACHTI B2B Full Size - rozjasnione')
OBECNY = ('#e4dfda', '#f5f3f1')

PRODUKTY = [  # aktualna zawartość kolekcji „Nowości"
    ('AZ-3101PC', 'Czapka zimowa damska Erina', '28,60 PLN'),
    ('AZ-3102PC', 'Czapka zimowa damska Estela', '27,60 PLN'),
    ('AZ-3100PC', 'Czapka zimowa damska Dora', '29,60 PLN'),
    ('AZ-3099PC', 'Czapka zimowa damska Rosa', '28,20 PLN'),
    ('AZ-3098PC', 'Czapka zimowa damska Romina', '27,20 PLN'),
    ('AZ-3097PC', 'Czapka zimowa damska Romana', '27,50 PLN'),
]

def hx(r, g, b): return '#%02x%02x%02x' % (max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b))))
def rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def jasniej(h, proc):
    r, g, b = rgb(h); f = proc / 100
    return hx(r + (255 - r) * f, g + (255 - g) * f, b + (255 - b) * f)
def ciemniej(h, proc):
    r, g, b = rgb(h); f = 1 - proc / 100
    return hx(r * f, g * f, b * f)
def podton(h, stopnie, nasyc=1.0):
    r, g, b = [x / 255 for x in rgb(h)]
    hh, l, s = colorsys.rgb_to_hls(r, g, b)
    hh = (hh + stopnie / 360) % 1.0
    r, g, b = colorsys.hls_to_rgb(hh, l, min(1, s * nasyc))
    return hx(r * 255, g * 255, b * 255)

def warianty():
    pas, kaf = OBECNY
    W = []
    W.append(('Punkt wyjścia', [
        (pas, kaf, 'Obecne ustawienie sklepu', 'To, co widzisz teraz na stronie głównej.')]))
    W.append(('Pas ciemniejszy, kafelek bez zmian', [
        (ciemniej(pas, p), kaf, f'Pas ciemniejszy o {p} %', '') for p in (4, 8, 12, 18, 25)]))
    W.append(('Pas jaśniejszy, kafelek bez zmian', [
        (jasniej(pas, p), kaf, f'Pas jaśniejszy o {p} %', '') for p in (20, 40, 60, 80)] + [
        ('#ffffff', kaf, 'Pas biały', 'Sekcja znika jako pas, zostają same kafelki.')]))
    W.append(('Kafelek ciemniejszy, pas bez zmian', [
        (pas, ciemniej(kaf, p), f'Kafelek ciemniejszy o {p} %', '') for p in (2, 4, 6, 9)]))
    W.append(('Kafelek biały', [
        (pas, '#ffffff', 'Kafelek czysto biały', 'Najmocniejszy kontrast kafelka do pasa.'),
        (ciemniej(pas, 8), '#ffffff', 'Ciemniejszy pas, biały kafelek', ''),
        (ciemniej(pas, 16), '#ffffff', 'Jeszcze ciemniejszy pas, biały kafelek', '')]))
    W.append(('Cieplejszy podton (w stronę beżu)', [
        (podton(pas, -8, 1.3), podton(kaf, -8, 1.3), 'Ciepły, delikatny', ''),
        (podton(pas, -14, 1.7), podton(kaf, -14, 1.4), 'Ciepły, wyraźny', ''),
        (podton(ciemniej(pas, 10), -14, 1.7), podton(kaf, -10, 1.3), 'Ciepły i głębszy', '')]))
    W.append(('Chłodniejszy podton (w stronę szarości)', [
        (podton(pas, 20, 0.7), podton(kaf, 20, 0.7), 'Chłodny, delikatny', ''),
        (podton(pas, 30, 0.45), podton(kaf, 30, 0.5), 'Chłodny, prawie neutralny', ''),
        (podton(ciemniej(pas, 10), 30, 0.45), podton(kaf, 25, 0.5), 'Chłodny i głębszy', '')]))
    W.append(('Zieleń i oliwka', [
        (podton(pas, 45, 0.8), kaf, 'Pas z nutą zieleni', ''),
        (podton(ciemniej(pas, 12), 45, 1.1), podton(kaf, 45, 0.6), 'Szałwiowy', ''),
        ('#dfe0d8', '#f6f6f2', 'Jasna szałwia', '')]))
    W.append(('Róż i piaskowy', [
        (podton(pas, -20, 1.2), kaf, 'Pas z nutą różu', ''),
        ('#e8ddd6', '#faf5f2', 'Piaskowy ciepły', ''),
        ('#e6dcd4', '#f7f2ee', 'Piaskowy głębszy', '')]))
    W.append(('Kafelek ciemniejszy niż pas (odwrócenie)', [
        (jasniej(pas, 50), pas, 'Jasny pas, kafelek w obecnym kolorze', ''),
        ('#f7f5f2', '#e9e4de', 'Delikatne odwrócenie', ''),
        ('#ffffff', '#efeae4', 'Białe tło, wyraźny kafelek', '')]))
    out, n = [], 0
    for grupa, poz in W:
        lista = []
        for p, k, nazwa, opis in poz:
            n += 1
            lista.append(dict(nr=n, pas=p, kafel=k, nazwa=nazwa, opis=opis))
        out.append((grupa, lista))
    return out

def foto(code, cache={}):
    if code in cache: return cache[code]
    files = cache.setdefault('_f', sorted(os.listdir(PHOTOS)))
    num = re.match(r'AZ-\d+', code).group(0)
    c = [f for f in files if f.upper().startswith(code.upper() + ' ')] or [f for f in files if re.match(num + r'[A-Z]* ', f.upper())]
    if not c: return ''
    im = Image.open(os.path.join(PHOTOS, c[0])).convert('RGB'); im.thumbnail((300, 375))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=80)
    cache[code] = 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    return cache[code]

def build():
    grupy = warianty()
    ile = sum(len(g[1]) for g in grupy)
    kafle = ''.join(
        f'<figure class="tile" style="background:{{kafel}}"><div class="ph" style="background:{{kafel}}">'
        f'<img src="{foto(c)}" alt=""></div><figcaption><span class="nm">{t}</span>'
        f'<span class="sku">{c}</span><span class="pr">{p}</span></figcaption></figure>'
        for c, t, p in PRODUKTY)
    sekcje = []
    for grupa, poz in grupy:
        wiersze = ''.join(
            f'''<section class="wariant">
              <header><span class="nr">{w['nr']}</span><h3>{w['nazwa']}</h3>
                <p class="hex"><i style="background:{w['pas']}"></i>pas {w['pas']}<i style="background:{w['kafel']}"></i>kafelki {w['kafel']}</p></header>
              {f'<p class="opis">{w["opis"]}</p>' if w['opis'] else ''}
              <div class="band" style="background:{w['pas']}"><h4>Nowości</h4>
                <div class="grid">{kafle.replace('{kafel}', w['kafel'])}</div></div>
            </section>''' for w in poz)
        sekcje.append(f'<h2>{grupa}</h2>{wiersze}')
    html = f'''<title>Kolory sekcji Nowości — warianty</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tenor+Sans&family=Jost:wght@300;400;500&display=swap">
<style>
:root{{--bg:#faf8f5;--ink:#241f1b;--muted:#6d655c;--line:rgba(36,31,27,.14)}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#191715;--ink:#efe9e1;--muted:#a49b90;--line:rgba(239,233,225,.16)}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:300 15px/1.5 Jost,system-ui,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:44px 22px 80px}}
h1{{font-family:'Tenor Sans',Georgia,serif;font-weight:400;font-size:32px;margin:0 0 10px}}
.lead{{color:var(--muted);max-width:78ch;margin:0}}
h2{{font-family:'Tenor Sans',Georgia,serif;font-weight:400;font-size:21px;margin:44px 0 4px;padding-top:18px;border-top:1px solid var(--line);break-after:avoid}}
.wariant{{margin:18px 0 0;break-inside:avoid}}
.wariant header{{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 16px;margin-bottom:4px}}
.nr{{font-family:'Tenor Sans',Georgia,serif;font-size:20px;opacity:.4}}
.wariant h3{{font-family:'Tenor Sans',Georgia,serif;font-weight:400;font-size:18px;margin:0}}
.hex{{margin:0;color:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}}
.hex i{{display:inline-block;width:13px;height:13px;border-radius:50%;vertical-align:-2px;margin:0 5px 0 0;border:1px solid rgba(0,0,0,.16)}}
.hex i:nth-of-type(2){{margin-left:14px}}
.opis{{margin:0 0 8px;color:var(--muted);font-size:13px}}
.band{{padding:22px 18px 24px;border-radius:10px}}
.band h4{{font-family:'Tenor Sans',Georgia,serif;font-weight:400;font-size:18px;text-align:center;margin:0 0 12px;padding-bottom:10px;border-bottom:1px solid rgba(43,39,36,.25);color:#2b2724}}
.grid{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}}
.tile{{margin:0;border-radius:8px;overflow:hidden;display:flex;flex-direction:column;color:#2b2724;height:100%}}
.ph{{aspect-ratio:4/5}}
.ph img{{width:100%;height:100%;object-fit:cover;mix-blend-mode:multiply;display:block}}
figcaption{{padding:8px 9px 10px;display:flex;flex-direction:column;gap:2px}}
.nm{{font-family:'Tenor Sans',Georgia,serif;font-size:9.5px;line-height:1.25;letter-spacing:.06em;text-transform:uppercase;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.5em}}
.sku{{font-size:8px;letter-spacing:.08em;color:#6f6a66}}
.pr{{font-size:10.5px;margin-top:2px}}
@media print{{@page{{size:A4;margin:10mm}}body{{background:#fff;font-size:10pt}}.wrap{{padding:0;max-width:none}}
  h1{{font-size:24pt}}h2{{font-size:14pt;margin-top:16px;padding-top:10px}}
  .wariant{{margin-top:10px}}.wariant h3{{font-size:12pt}}.nr{{font-size:13pt}}.opis{{margin-bottom:5px}}
  .band{{padding:10px 9px 11px;border-radius:7px}}.band h4{{font-size:11pt;margin-bottom:8px;padding-bottom:6px}}
  .grid{{gap:5px}}figcaption{{padding:5px 6px 6px}}.nm{{font-size:6pt}}.sku{{font-size:5pt}}.pr{{font-size:6.5pt}}}}
</style>
<div class="wrap"><h1>Kolory sekcji „Nowości" — warianty do wyboru</h1>
<p class="lead">Wszystkie warianty pokazują to samo: pas sekcji i sześć kafelków z prawdziwymi czapkami z kolekcji Nowości.
Zdjęcia są przezroczyste względem tła kafelka, tak jak działa to na sklepie, więc obraz jest wierny.
Punkt wyjścia (wariant 1) to obecne ustawienie. Odeślij numer, zmiana zajmuje kilka minut.</p>
{''.join(sekcje)}</div>'''
    open(os.path.join(HERE, '..', 'docs', 'warianty-kolorow.html'), 'w', encoding='utf-8').write(html)
    print('wariantów:', ile)

if __name__ == '__main__':
    build()
