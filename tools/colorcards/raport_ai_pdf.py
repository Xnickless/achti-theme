"""PDF z kółkami kolorów z AI (Nano Banana Pro) — podsumowanie dla Kamila/Adriana (20.10.2026).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/raport_ai_pdf.py OUTAI OUT.pdf [--wejscie]

OUTAI = katalog z kolka_ai.py (<karta>/SET n.jpg + _wejscie/). Strona 1: podsumowanie, potem każda karta:
nazwy i kody czapek, packshot i wszystkie kółka (z --wejscie także zdjęcie próbki nad każdym kółkiem).
"""
import glob
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raport_pdf import HERE, PACK, W, H, M, Doc, circle, font, nat, wrap  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out, pdf = args
    pary = '--wejscie' in sys.argv
    mapa = json.load(open(os.path.join(HERE, 'mapa.json')))
    prods = {p['code']: p['title'] for p in json.load(open(os.path.join(HERE, '..', 'achti-produkty.json')))}
    man = json.load(open(os.path.join(HERE, 'manifest.json')))
    cards = sorted((c for c in os.listdir(out) if glob.glob(os.path.join(out, c, 'SET *.jpg'))), key=nat)
    total = sum(len(glob.glob(os.path.join(out, c, 'SET *.jpg'))) for c in cards)

    doc = Doc()
    doc.new()
    doc.text('Achti — kółka kolorów z AI', 44, True, gap=18)
    doc.text('Stan na 20.10.2026 · model Gemini Nano Banana Pro · wgrane na stronę', 24, color='#666', gap=34)
    lines = [f'• {total} kółek na {len(cards)} kartach kolorów (czapek: '
             f'{sum(len([k for k, v in mapa.items() if v == c]) for c in cards)}).',
             '• Wzór Kamila (AZ-2344PC): w kółku cały obszar czapki — dzianina z pasami u góry, ściągacz przez',
             '  całą szerokość na dole, bez metek, sznurków i tła. Kolory, kolejność pasów i splot jak na próbce.',
             '• Próbki bez ściągacza (karta AZ-1356PC — małe kwadraty lewej strony dzianiny): ściągacz dorysowany',
             '  z tej samej przędzy, tak jak na gotowej czapce (zdjęcie produktu było wzorem budowy).',
             '• Każde kółko porównane ze zdjęciem próbki; nieudane (zgubiona faktura, dorobione smugi, ściągacz',
             '  w kolorze obszycia, ścięte rogi) wygenerowane ponownie.',
             '• Wszystkie kółka kart używanych w sklepie są wgrane na stronę (20.10.2026).', '']
    for c in cards:
        n, m = len(glob.glob(os.path.join(out, c, 'SET *.jpg'))), len(man.get(c, []))
        lines.append(f'  {c.replace("COLORCARD ", "").split()[0]}: {n} z {m} kolorów' + ('' if n >= m else ' (w toku)'))
    lines += ['', '• Pominięte (bez zmian): karty z listy Kamila „OK” (1356, 1876, 2539–2556, 2612, 2814), palety przędzy,',
              '  karty z motywami oraz 2707 i 2753 (czekają na kierunek od Adriana).']
    for ln in lines:
        doc.text(ln, 22, gap=10)
    doc.y += 50

    D, GAP, COLS = (150, 24, 6) if pary else (112, 20, 8)
    for card in cards:
        fs = sorted(glob.glob(os.path.join(out, card, 'SET *.jpg')), key=lambda p: nat(os.path.basename(p)))
        codes = sorted([k for k, v in mapa.items() if v == card], key=nat)
        title = []
        for n in [f'{prods.get(c, c)} ({c})' for c in codes]:
            title += wrap(n, 20, W - 2 * M - 230)
        head = max(40 + 26 * len(title), 230)
        cell = (2 * D + 50) if pary else (D + 34)
        doc.need(head + cell)
        y0 = doc.y
        doc.d.line((M, y0 - 14, W - M, y0 - 14), fill='#ddd', width=2)
        doc.d.text((M, y0), card.replace('COLORCARD ', 'Karta ') + f' · {len(fs)} kolorów', font=font(26, True), fill='#222')
        for i, ln in enumerate(title):
            doc.d.text((M, y0 + 40 + 26 * i), ln, font=font(20), fill='#444')
        pk = next((p for c in codes for p in [os.path.join(PACK, f'{c}-wyrownane.jpg')] if os.path.exists(p)), None)
        if pk:
            im = Image.open(pk).convert('RGB')
            im.thumbnail((180, 210))
            doc.page.paste(im, (W - M - im.width, y0))
        doc.y = y0 + head
        for i, f in enumerate(fs):
            c = i % COLS
            if c == 0 and i:
                doc.y += cell
            if c == 0:
                doc.need(cell)
            x = M + c * (D + GAP)
            y = doc.y
            name = os.path.basename(f)[:-4]
            if pary:
                src = os.path.join(out, card, '_wejscie', name + '.jpg')
                if os.path.exists(src):
                    im = Image.open(src).convert('RGB')
                    im.thumbnail((D, D))
                    doc.page.paste(im, (x + (D - im.width) // 2, y + (D - im.height) // 2))
                y += D + 8
            doc.page.paste(circle(f, D), (x, y))
            doc.d.text((x + D // 2, y + D + 4), name, font=font(16), fill='#333', anchor='ma')
        doc.y += cell + 26

    doc.pages[0].save(pdf, save_all=True, append_images=doc.pages[1:], resolution=150, quality=82)
    print(len(doc.pages), 'stron', pdf)


if __name__ == '__main__':
    main()
