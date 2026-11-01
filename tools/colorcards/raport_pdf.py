"""Raport PDF dla Adriana: kolory z kolorników na stronie (14.10.2026).

  ~/Claude/achti-foto/venv/bin/python3 tools/colorcards/raport_pdf.py CROPS PALETY OUT.pdf [PRZED]

CROPS = kółka kart modeli (np. out9), PALETY = kółka palet przędzy (np. out4), PRZED = wersja przed poprawką
(strona „przed / po”). Na każdej karcie: nazwy i kody czapek, packshot pierwszej czapki i wszystkie kółka.
"""
import glob
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, M = 1240, 1754, 70  # A4 w 150 dpi
F = '/System/Library/Fonts/Supplemental/Arial.ttf'
FB = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
font = lambda s, b=False: ImageFont.truetype(FB if b else F, s)  # noqa: E731
PACK = os.path.expanduser('~/Claude/achti-foto/wyrownane')
nat = lambda s: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]  # noqa: E731


def circle(path, d):
    im = Image.open(path).convert('RGB').resize((d, d), Image.LANCZOS)
    m = Image.new('L', (d * 4, d * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    out = Image.new('RGB', (d, d), 'white')
    out.paste(im, (0, 0), m.resize((d, d), Image.LANCZOS))
    return out


class Doc:
    def __init__(self):
        self.pages, self.page, self.y = [], None, 0

    def new(self):
        self.page = Image.new('RGB', (W, H), 'white')
        self.d = ImageDraw.Draw(self.page)
        self.pages.append(self.page)
        self.y = M
        self.d.text((W - M, H - 40), str(len(self.pages)), font=font(18), fill='#999', anchor='rs')

    def need(self, h):
        if self.page is None or self.y + h > H - M:
            self.new()

    def text(self, t, size=22, bold=False, color='#222', gap=8):
        self.need(size + gap)
        self.d.text((M, self.y), t, font=font(size, bold), fill=color)
        self.y += size + gap


def wrap(t, size, width):
    f, out, line = font(size), [], ''
    for w in t.split():
        if f.getlength(line + ' ' + w) > width and line:
            out.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    return out + [line]


def main(crops, palety, out_pdf, przed=None):
    mapa = json.load(open(os.path.join(HERE, 'mapa.json')))
    prods = {p['code']: p['title'] for p in json.load(open(os.path.join(HERE, '..', 'achti-produkty.json')))}
    cards = {}
    for code, card in mapa.items():
        if card and card != '?':
            cards.setdefault(card, []).append(code)

    def folder(card):
        for base in (crops, palety):
            for name in (card, card.replace('%', '_')):
                if os.path.isdir(os.path.join(base, name)):
                    return os.path.join(base, name)

    used = [(c, codes) for c, codes in cards.items() if folder(c)]
    used.sort(key=lambda kv: (0 if 'AZ-' in kv[0] else 1, nat(kv[0])))
    n_circ = sum(len(glob.glob(folder(c) + '/*.jpg')) for c, _ in used)
    n_prod = sum(len(v) for _, v in used)

    doc = Doc()
    doc.new()
    doc.text('Achti — kolory czapek na stronie', 44, True, gap=18)
    doc.text('Stan na 14.10.2026 · kółka z kart kolorów Adriana', 24, color='#666', gap=34)
    for line in [
        f'• {n_prod} czapek ma kolory jako warianty, {len(used)} kart, {n_circ} kółek.',
        '• Kółko = prawdziwy wycinek dzianiny z karty kolorów (cała szerokość próbki: wszystkie pasy',
        '  i ściągacz), bez metek i tła — wg wzoru Adriana (AZ-1748PC SET 7).',
        '• Kierunek: dzianina od góry do dołu, tak jak na czapce — pasy kolorów poziomo, ściągacz na dole,',
        '  oczka (warkocze, prążki) pionowo, motywy (serca, kwiaty, napisy) prosto.',
        '• Poprawka 14.10: każde kółko obrócone o 90° względem wersji z 13.10, potem przegląd wszystkich',
        '  ~1000 kółek i ręczna korekta 308 z nich (do góry nogami, bokiem). Karta AZ-1356PC to lewa strona',
        '  dzianiny — jej prążki są poziomo, tak jak na czapce.',
        '• Palety przędzy (ACRYLIC 100%, AUSTRALIA, VEZUV…) — jedno kółko na kolor przędzy, nitki pionowo.',
        '• Na karcie produktu: kółko powiększa się po najechaniu (telefon: po dotknięciu), pod nim pole',
        '  ilości; jeden przycisk „Dodaj do koszyka” dla wszystkich kolorów.',
        '',
        'Do uzupełnienia przez Adriana:',
        '• AZ-2349PC SET 17 i 18 — nowe zdjęcie (metka zasłania ściągacz, widać 2 z 3 kolorów).',
        '• 17 kolorów bez kółka (metka zasłania całą próbkę): 1748 S5; 2539PK S8; 2540PK S1, S2, S4, S5;',
        '  2543PK S3–S5; 2808 S10; 2912 S9; 2943 S2, S7, S15; 3038 S8; 3070PK S7.',
        '• 44 czapki bez karty kolorów — arkusz na Drive.',
        '• AUSTRALIA: do decyzji — zostawić tylko kolory „Stock Service” (77 ze 170).',
    ]:
        doc.text(line, 22, bold=line.endswith(':'), gap=10)

    if przed:
        doc.new()
        doc.text('Przed i po poprawce (14.10.2026)', 34, True, gap=24)
        for card, sets in [('COLORCARD AZ-2349PC', ['SET 1', 'SET 9', 'SET 13', 'SET 17']),
                           ('COLORCARD AZ-1876PC', ['SET 3', 'SET 10', 'SET 13', 'SET 21']),
                           ('COLORCARD AZ-2941PC', ['SET 1', 'SET 9', 'SET 16', 'SET 18']),
                           ('COLORCARD AZ-2912PC', ['SET 2', 'SET 4', 'SET 7', 'SET 12'])]:
            doc.need(230)
            doc.d.text((M, doc.y), card.replace('COLORCARD ', ''), font=font(22, True), fill='#222')
            doc.d.text((M + 30, doc.y + 40), 'przed', font=font(18), fill='#a00')
            doc.d.text((M + 30 + 4 * 130 + 40, doc.y + 40), 'po', font=font(18), fill='#070')
            for i, s in enumerate(sets):
                for k, base in enumerate((przed, crops)):
                    p = os.path.join(base, card, s + '.jpg')
                    if os.path.exists(p):
                        x = M + i * 130 + k * (4 * 130 + 40)
                        doc.page.paste(circle(p, 120), (x, doc.y + 70))
                        doc.d.text((x + 60, doc.y + 196), s.replace('SET ', 'S'), font=font(16), fill='#555', anchor='ma')
            doc.y += 240

    D, GAP, COLS = 112, 14, 9
    for card, codes in used:
        fs = sorted(glob.glob(folder(card) + '/*.jpg'), key=lambda p: nat(os.path.basename(p)))
        names = [f'{prods.get(c, c)} ({c})' for c in sorted(codes, key=nat)]
        title_lines = []
        for n in names:
            title_lines += wrap(n, 20, W - 2 * M - 230)
        rows = (len(fs) + COLS - 1) // COLS
        head = max(40 + 26 * len(title_lines), 230)
        doc.need(head + min(rows, 3) * (D + 34))
        y0 = doc.y
        doc.d.line((M, y0 - 14, W - M, y0 - 14), fill='#ddd', width=2)
        doc.d.text((M, y0), card.replace('COLORCARD ', 'Karta ').replace('_', '%') + f' · {len(fs)} kolorów',
                   font=font(26, True), fill='#222')
        for i, ln in enumerate(title_lines):
            doc.d.text((M, y0 + 40 + 26 * i), ln, font=font(20), fill='#444')
        pk = next((p for c in sorted(codes, key=nat) for p in [os.path.join(PACK, f'{c}-wyrownane.jpg')]
                   if os.path.exists(p)), None)
        if pk:
            im = Image.open(pk).convert('RGB')
            im.thumbnail((180, 210))
            doc.page.paste(im, (W - M - im.width, y0))
        doc.y = y0 + head
        for i, f in enumerate(fs):
            r, c = divmod(i, COLS)
            if c == 0 and i:
                doc.y += D + 34
            if c == 0:
                doc.need(D + 34)
            x = M + c * (D + GAP + 6)
            doc.page.paste(circle(f, D), (x, doc.y))
            doc.d.text((x + D // 2, doc.y + D + 4), os.path.basename(f)[:-4], font=font(16), fill='#333', anchor='ma')
        doc.y += D + 60

    doc.pages[0].save(out_pdf, save_all=True, append_images=doc.pages[1:], resolution=150, quality=82)
    print(len(doc.pages), 'stron', out_pdf)


if __name__ == '__main__':
    main(*sys.argv[1:5])
