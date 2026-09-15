"""Obrazek do udostępniania w social (Open Graph, 1200×630) z hasłem z hero.
  python3 tools/build_social_image.py [--lang=pl|en|de|fr] [--out=ścieżka]
Źródło: ~/Downloads/achti-hero/hero-para.png (to samo zdjęcie co baner). Uruchamiać pythonem z Pillow (Xcode)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HOME = os.path.expanduser('~')
SRC = os.path.join(HOME, 'Downloads/achti-hero/hero-para.png')
FONTS = '/private/tmp/claude-501/-Users-kamil-dziedzic-Claude-Projects-achti-theme/efb5996b-30d9-4ec1-a415-d95714452b6b/scratchpad/fonts'
LANG = next((a[7:] for a in sys.argv if a.startswith('--lang=')), 'pl')
TEXT = {
    'pl': ('Rozwijaj swój biznes z Achti', 'Czapki, kominy i opaski · hurt B2B'),
    'en': ('Grow your business with Achti', 'Hats, snoods and headbands · B2B wholesale'),
    'de': ('Lassen Sie Ihr Geschäft mit Achti wachsen', 'Mützen, Loops und Stirnbänder · B2B-Großhandel'),
    'fr': ('Développez votre activité avec Achti', "Bonnets, snoods et bandeaux · vente en gros B2B"),
}[LANG]
OUT = next((a[6:] for a in sys.argv if a.startswith('--out=')), os.path.join(HOME, f'Downloads/achti-social{"" if LANG == "pl" else "-" + LANG}.jpg'))
W, H = 1200, 630

im = Image.open(SRC).convert('RGB')
sw, sh = im.size
scale = max(W / sw, H / sh)
im = im.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
# kadr: ludzie w lewej połowie, więc trzymamy lewą część i górę (twarze)
im = im.crop((0, 0, W, H))

# przyciemnienie od dołu, żeby biały tekst był czytelny na żwirze i płaszczach
grad = Image.new('L', (1, H))
for y in range(H):
    t = max(0.0, (y - H * 0.34) / (H * 0.66))
    grad.putpixel((0, y), int(165 * (t ** 1.35)))
veil = Image.new('RGB', (W, H), (26, 22, 19))
im = Image.composite(veil, im, grad.resize((W, H)))

d = ImageDraw.Draw(im)
title_f = ImageFont.truetype(os.path.join(FONTS, 'TenorSans.ttf'), 62)
sub_f = ImageFont.truetype(os.path.join(FONTS, 'Jost.ttf'), 27)

# tytuł łamiemy na maks. 2 linie, jeśli nie mieści się w szerokości
margin = 64
maxw = W - 2 * margin
def lines_for(text, font):
    if d.textlength(text, font=font) <= maxw: return [text]
    words, out, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: out.append(cur); cur = w
    out.append(cur); return out

lines = lines_for(TEXT[0], title_f)
while len(lines) > 2 and title_f.size > 40:
    title_f = ImageFont.truetype(os.path.join(FONTS, 'TenorSans.ttf'), title_f.size - 4)
    lines = lines_for(TEXT[0], title_f)

lh = title_f.size * 1.18
y = H - margin - 34 - len(lines) * lh
for ln in lines:
    d.text((margin + 2, y + 2), ln, font=title_f, fill=(0, 0, 0, 90))  # delikatny cień
    d.text((margin, y), ln, font=title_f, fill=(255, 255, 255))
    y += lh
d.text((margin, y + 6), TEXT[1], font=sub_f, fill=(236, 230, 222))

im.save(OUT, quality=88, optimize=True)
print(OUT, im.size, f'{os.path.getsize(OUT) / 1024:.0f} kB')
