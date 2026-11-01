"""Zestawienie wyciętych próbek (kółka z podpisami) do przeglądu: arkusz.py OUT [folder…] → OUT/_arkusze/<folder>.jpg"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFont

def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', s)]

out = sys.argv[1]
folders = sys.argv[2:] or sorted(d for d in os.listdir(out) if os.path.isdir(os.path.join(out, d)) and not d.startswith('_'))
os.makedirs(os.path.join(out, '_arkusze'), exist_ok=True)
font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
for f in folders:
    names = sorted((n[:-4] for n in os.listdir(os.path.join(out, f)) if n.endswith('.jpg')), key=natural)
    if not names:
        continue
    cols, cell = 8, 150
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * (cell + 26) + 40), 'white')
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), f, fill='black', font=font)
    for i, n in enumerate(names):
        im = Image.open(os.path.join(out, f, n + '.jpg')).resize((130, 130))
        m = Image.new('L', (130, 130), 0); ImageDraw.Draw(m).ellipse((0, 0, 129, 129), fill=255)
        x, y = (i % cols) * cell + 10, (i // cols) * (cell + 26) + 40
        sheet.paste(im, (x, y), m)
        d.text((x, y + 132), n, fill='black', font=font)
    sheet.save(os.path.join(out, '_arkusze', f + '.jpg'), quality=82)
    print(os.path.join(out, '_arkusze', f + '.jpg'))
