#!/usr/bin/env python3
"""Zdjęcia „na modelce” z packshotów (Gemini image API — „nano banana”).

Klucz: ~/.config/achti/gemini_key (projekt gen-lang-client-0310151608).
Modele: gemini-3-pro-image (Nano Banana Pro, najwierniejszy wzór dzianiny, ~0,134 $/zdj.),
        gemini-3.1-flash-image (~0,101 $/zdj. w 2K), gemini-2.5-flash-image (~0,039 $/zdj.).

  python3 tools/gen_model_photos.py refs [--only=kobieta-A,...]   # kandydatki/kandydaci na modelkę (tekst → obraz)
  python3 tools/gen_model_photos.py hat <ref.png> <packshot.jpg> <wyj.png> [--kind=hat|headband|snood]
  python3 tools/gen_model_photos.py batch [--codes=AZ-1,AZ-2] [--limit=20] [--persona=kobieta-A] [--force]
  python3 tools/gen_model_photos.py seria --damskie=A,B --meskie=C --dziewczece=D --chlopiece=E [--size=4K]
  python3 tools/gen_model_photos.py oldmoney [--code=] [--osoba=] [--styl=dwor|stajnia|auto|ogrod|aleja] [--size=4K]
  python3 tools/gen_model_photos.py styl [--code=AZ-2938] [--osoba=m2] [--styl=kanapa|mur|kawiarnia|las]
  python3 tools/gen_model_photos.py casting [--code=AZ-3101PC] [--code-dzieci=AZ-2364PC] [--only=k1-blond,...]
  python3 tools/gen_model_photos.py kandydatki [--code=AZ-3101PC] [--scena=krakow-rynek] [--only=blond-1,...]
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

# Kandydatki do testu plenerowego (11.09.2026, wytyczne Kamila: 22-25 lat, blond albo brąz).
KANDYDATKI = {
    'blond-1': 'a 23-year-old Polish woman, long straight light-blonde hair, delicate oval face, blue eyes, fresh natural makeup',
    'blond-2': 'a 22-year-old Polish woman, shoulder-length wavy golden-blonde hair, soft round face, green eyes, barely-there makeup',
    'blond-3': 'a 25-year-old Polish woman, long beachy ash-blonde waves, high cheekbones, grey-blue eyes, clean nordic look',
    'blond-4': 'a 24-year-old Polish woman, platinum blonde hair in a low ponytail with loose strands, fine features, natural makeup',
    'braz-1': 'a 23-year-old Polish woman, long straight chestnut-brown hair, warm brown eyes, light freckles, natural makeup',
    'braz-2': 'a 22-year-old Polish woman, long wavy dark-brown hair, expressive brown eyes, soft youthful face, minimal makeup',
    'braz-3': 'a 25-year-old Polish woman, medium-length light-brown hair with soft curls, hazel eyes, warm friendly face',
    'braz-4': 'a 24-year-old Polish woman, long glossy dark-brown hair, defined brows, almond eyes, editorial but natural look',
}

# Plenery — tło rozmyte, czapka zostaje bohaterem kadru.
SCENY = {
    'krakow-rynek': 'the Main Market Square in Krakow, Poland, with the Cloth Hall arcades and the towers of St Mary\'s Basilica softly blurred in the background',
    'krakow-kazimierz': 'a narrow old street in the Kazimierz district of Krakow with historic tenement houses and warm shop windows softly blurred in the background',
    'krakow-planty': 'the Planty park in Krakow on a crisp winter morning, bare trees and a historic brick wall softly blurred in the background',
    'krakow-wawel': 'the courtyard near Wawel castle in Krakow, renaissance arcades and stone walls softly blurred in the background',
    'krakow-most': 'the Bernatka footbridge over the Vistula river in Krakow at dusk, string lights and the river softly blurred in the background',
    'zakopane': 'a snowy street in Zakopane with wooden highlander architecture and the Tatra mountains softly blurred in the background',
    'gory-snieg': 'a snowy mountain meadow in the Tatras on a bright winter day, snow-covered spruces softly blurred in the background',
    'las-zima': 'a winter forest path with frost on the branches, soft morning haze blurred in the background',
    'kawiarnia': 'a warm cafe interior seen from the street side, window reflections and soft indoor lights blurred in the background',
    'nadmorze': 'a windy Baltic sea beach in winter, dunes and grey sea softly blurred in the background',
    'jesien-park': 'a city park in autumn, golden and rust coloured leaves on the trees and ground, warm low sunlight, softly blurred background',
    'jesien-las': 'an autumn forest path covered with fallen leaves, warm golden backlight through the branches, softly blurred background',
    'jesien-krakow': 'a Krakow street in autumn, golden leaves on the pavement and historic tenement houses softly blurred in the background',
}

PROMPT_PLENER = (
    'Image 1 shows the product: a knitted winter {what} photographed on white. '
    'Create a premium editorial lifestyle photograph of {desc} wearing exactly that product outdoors in {scene}. '
    'Reproduce the product with absolute fidelity: identical knit structure and stitch pattern (cables, ribs, jacquard motifs), '
    'identical colours and colour blocks, identical proportions and depth of the cuff, and the pompom at the same generous size, '
    'colour and fluffiness as in image 1 - never shrink or omit the pompom - plus the small metal brand label in the same position. '
    'Do not redesign, recolour or simplify the product, do not invent patterns. '
    'Pose: three-quarter side view, the head turned about 35 degrees away from the camera and the chin lowered slightly, '
    'eyes looking down and away with a calm natural expression, so the top, crown and side of the {what} are clearly presented to the viewer. '
    'The whole {what} including the pompom is inside the frame, nothing cropped. Hair falls naturally behind the shoulders and does not cover the {what}. '
    'She wears a simple neutral winter coat in beige or grey wool, collar down, no scarf, no jewellery. '
    'Light: soft overcast winter daylight, gentle contrast, cool natural white balance, no harsh shadows. '
    'Shot on an 85mm lens at f/2, shallow depth of field, background clearly blurred, subject tack sharp. '
    'Photorealistic fashion photography, natural skin texture, no heavy retouching, 4:5 portrait, high detail.'
)


CASTING = {
    # kobiety 22-25, blond i brąz
    'k1-blond':  dict(typ='kobieta', desc='a 23-year-old Polish woman with long straight honey-blonde hair, delicate features, blue-grey eyes, fresh natural makeup'),
    'k2-blond':  dict(typ='kobieta', desc='a 22-year-old Polish woman with shoulder-length tousled light-blonde hair, round soft face, warm smile lines, no visible makeup'),
    'k3-blond':  dict(typ='kobieta', desc='a 25-year-old Polish woman with long ash-blonde hair and a centre parting, sculpted cheekbones, calm nordic beauty'),
    'k4-braz':   dict(typ='kobieta', desc='a 23-year-old Polish woman with long chestnut-brown hair, warm brown eyes, light freckles across the nose'),
    'k5-braz':   dict(typ='kobieta', desc='a 22-year-old Polish woman with dark-brown hair in soft waves, expressive dark eyes, youthful round face'),
    'k6-braz':   dict(typ='kobieta', desc='a 24-year-old Polish woman with light-brown hair and natural curls, hazel eyes, open friendly face'),
    # mężczyźni
    'm1': dict(typ='mezczyzna', desc='a 26-year-old Polish man with short dark-blonde hair and light stubble, friendly relaxed face'),
    'm2': dict(typ='mezczyzna', desc='a 30-year-old Polish man with short brown hair and a neat short beard, calm confident face'),
    'm3': dict(typ='mezczyzna', desc='a 24-year-old Polish man with dark hair, clean shaven, slim face, casual sporty look'),
    'm4': dict(typ='mezczyzna', desc='a 34-year-old Polish man with slightly greying short hair and stubble, warm mature look'),
    # dzieci (czapki dziecięce)
    'd1': dict(typ='dziewczynka', desc='a cheerful 7-year-old Polish girl with long light-blonde hair and rosy cheeks'),
    'd2': dict(typ='dziewczynka', desc='a 6-year-old Polish girl with brown hair in two braids and big brown eyes'),
    'd3': dict(typ='dziewczynka', desc='an 8-year-old Polish girl with wavy chestnut hair and freckles, bright happy face'),
    'c1': dict(typ='chlopiec', desc='a 7-year-old Polish boy with short blonde hair and blue eyes, cheerful face'),
    'c2': dict(typ='chlopiec', desc='a 6-year-old Polish boy with short dark-brown hair and rosy cheeks, curious look'),
    'c3': dict(typ='chlopiec', desc='an 8-year-old Polish boy with light-brown messy hair, friendly grin'),
}

UBRANIE = {
    'kobieta': 'a simple neutral winter coat in beige or grey wool, collar down, no scarf, no jewellery',
    'mezczyzna': 'a plain dark winter jacket, collar down, no scarf',
    'dziewczynka': 'a simple padded winter jacket in a muted colour, zipped up, no scarf',
    'chlopiec': 'a simple padded winter jacket in a muted colour, zipped up, no scarf',
}

PROMPT_CAST = (
    'Image 1 shows the product: a knitted winter {what} photographed on white.{ref_note} '
    'Create a premium editorial lifestyle photograph of {desc}, wearing exactly that product outdoors in {scene}. '
    'Reproduce the product with absolute fidelity: identical knit structure and stitch pattern (cables, ribs, jacquard motifs), '
    'identical colours and colour blocks, identical proportions and cuff depth, and the pompom at the same generous size, colour and '
    'fluffiness as in image 1 - never shrink or omit the pompom - plus the small metal brand label in the same position. '
    'Do not redesign, recolour or simplify the product, do not invent patterns. '
    'Pose: three-quarter side view, head turned about 35 degrees away from the camera, chin lowered slightly, eyes looking down and away '
    'with a calm natural expression, so the crown, side and pattern of the {what} are clearly presented. '
    'The whole {what} including the pompom is inside the frame, nothing cropped. Hair falls naturally and does not cover the {what}. '
    'The person wears {outfit}. '
    'Light: soft natural daylight, gentle contrast, no harsh shadows. Shot on an 85mm lens at f/2, shallow depth of field, '
    'background clearly blurred, subject tack sharp. Photorealistic fashion photography, natural skin texture, no heavy retouching, '
    '4:5 portrait, high detail.'
)

REF_NOTE = (' Image 2 shows the model: use exactly the same person, the same face, the same hair colour and length, '
            'so that both photographs clearly show one and the same model.')


# Style zdjęć: „packshot w plenerze” (domyślny) i ujęcia edytorialne/lookbookowe jak u Barts.
STYLE = {
    'kanapa': dict(
        scena='seated on a vintage dark-green buttoned leather Chesterfield sofa placed outdoors among fallen autumn leaves, '
              'bare trees and a park path softly blurred behind',
        poza='seated, leaning back into the sofa, relaxed, forearms resting on the knees, upper body and hands in frame, '
             'looking straight into the camera with a calm confident expression',
        stylizacja='a navy checked wool overshirt over a rust-coloured knitted roll-neck, a large plaid wool scarf loosely around the neck',
        swiatlo='soft overcast autumn daylight, warm colour grading, deep but gentle contrast'),
    'mur': dict(
        scena='leaning against an old red brick wall in a city street, autumn leaves on the pavement, blurred background',
        poza='standing three-quarter to the camera, one shoulder against the wall, hands in coat pockets, chin slightly lifted, '
             'looking into the camera with a relaxed expression, upper body in frame',
        stylizacja='a heavy charcoal wool coat over a cream chunky knit sweater',
        swiatlo='soft directional daylight from the side, cinematic contrast'),
    'kawiarnia': dict(
        scena='sitting at a small marble cafe table by a window, a cup of coffee on the table, warm interior lights blurred behind',
        poza='seated three-quarter to the camera, hands around the cup, head slightly tilted, looking into the camera with a warm calm smile, '
             'upper body and hands in frame',
        stylizacja='a camel wool coat over a cream knitted sweater',
        swiatlo='soft warm window light, gentle shadows, cosy mood'),
    'las': dict(
        scena='walking on a forest path covered with golden autumn leaves, tall blurred trees and hazy backlight behind',
        poza='mid-step, body turned three-quarter to the camera, head turned towards the lens, natural relaxed expression, '
             'upper body and one arm in frame',
        stylizacja='a quilted olive jacket over a grey knitted sweater',
        swiatlo='warm golden backlight through the trees, soft rim light on the hair and the hat'),
}

PROMPT_STYL = (
    'Image 1 shows the product: a knitted winter {what} photographed on white. '
    'Image 2 shows the model: use exactly the same person, the same face, the same hair colour and length. '
    'Create a premium fashion lookbook photograph of that person wearing exactly that product, {scena}. '
    'Reproduce the product with absolute fidelity: identical knit structure and stitch pattern, identical colours, identical proportions '
    'and cuff depth, the pompom at the same generous size, colour and fluffiness as in image 1 if present, and the small metal brand label '
    'in the same position. Do not redesign, recolour or simplify the product, do not invent patterns. '
    'Pose: {poza}. The whole {what} is inside the frame, nothing cropped, and it stays the visual hero of the photograph. '
    'Styling: {stylizacja}. Light: {swiatlo}. '
    'Shot on an 85mm lens at f/2, shallow depth of field, background clearly blurred, subject tack sharp. '
    'Photorealistic editorial fashion photography, natural skin texture, no heavy retouching, 4:5 portrait, high detail.'
)


# Old money: cicha elegancja, wieś i posiadłość, paleta camel/granat/kość słoniowa, bez logotypów.
OLD_MONEY = {
    'dwor': dict(
        scena='on the stone terrace of an ivy-covered English country manor, tall sash windows and clipped box hedges blurred behind',
        poza='standing three-quarter to the camera, one hand in the coat pocket, chin level, looking calmly into the lens, upper body and hands in frame',
        stylizacja='a camel double-breasted cashmere coat over an ivory cable-knit sweater, brown leather gloves, a fine gold watch, no logos',
        swiatlo='soft overcast autumn daylight, muted refined colour grading, low contrast, film-like tonality'),
    'stajnia': dict(
        scena='in the cobbled yard of an old equestrian stable, a bay horse and weathered stable doors softly blurred behind',
        poza='standing three-quarter to the camera, hand resting on a leather bridle, head slightly turned to the lens, relaxed confident expression, upper body in frame',
        stylizacja='a brown herringbone tweed hacking jacket over a navy roll-neck, tan leather gloves, no logos',
        swiatlo='soft diffused morning light, earthy muted palette, gentle contrast'),
    'auto': dict(
        scena='beside a vintage dark-green Land Rover parked on a gravel driveway in front of a stone country house, autumn trees blurred behind',
        poza='leaning lightly against the car door, arms loosely crossed, looking straight into the camera with a composed expression, upper body in frame',
        stylizacja='a navy wool overcoat over an oatmeal cashmere roll-neck, a muted tartan scarf, no logos',
        swiatlo='soft late-afternoon light, warm restrained colour grading, cinematic but natural'),
    'ogrod': dict(
        scena='in a formal garden with clipped yew hedges and a stone urn, golden autumn leaves on the gravel path blurred behind',
        poza='seated on a weathered stone bench, back straight, hands resting in the lap, head turned towards the camera with a serene expression, upper body in frame',
        stylizacja='an ivory cashmere coat over a cream fine-knit sweater, a silk scarf knotted at the neck, small pearl earrings, no logos',
        swiatlo='soft overcast light, pale refined palette, delicate contrast'),
    'aleja': dict(
        scena='walking along an avenue of old oak trees on a country estate, a golden retriever walking alongside, mist and autumn leaves blurred behind',
        poza='mid-step, body turned three-quarter to the camera, head turned to the lens, calm natural expression, upper body and one arm in frame',
        stylizacja='a beige trench coat over a navy cable-knit sweater, leather gloves, no logos',
        swiatlo='soft hazy morning backlight, muted green and beige palette, gentle rim light on the hat'),
}

PROMPT_OLDMONEY = (
    'Image 1 shows the product: a knitted winter {what} photographed on white. '
    'Image 2 is a close-up of the same product showing the knit texture and the small metal brand plate in detail. '
    'Image 3 shows the model: use exactly the same person, the same face, the same hair colour and length. '
    'Create a refined old-money, quiet-luxury fashion photograph of that person wearing exactly that product, {scena}. '
    'PRODUCT FIDELITY IS THE TOP PRIORITY: reproduce the knit structure, stitch pattern, colours and proportions exactly as in images 1 and 2; '
    'the pompom keeps the same generous size, colour and fluffiness if present; '
    'THE HAT HAS NO METAL PLATE, NO LABEL, NO TAG AND NO LETTERING: if the reference photo shows a small metal brand plate on the cuff, '
    'leave it out completely and show clean uninterrupted knit in its place. '
    'Do not redesign, recolour or simplify the product, do not invent patterns, do not add any text, logo or branding anywhere in the photograph. '
    'Pose: {poza}. The whole {what} is inside the frame, nothing cropped, sharply in focus, and it stays the hero of the photograph. '
    'Styling: {stylizacja}. Understated, expensive, never flashy. Light: {swiatlo}. '
    'Shot on an 85mm lens at f/2.8, the face and the {what} tack sharp, background softly blurred. '
    'Photorealistic editorial fashion photography, natural skin texture, no heavy retouching, 4:5 portrait, maximum detail.'
)


def cuff_crop(pack, out):
    """Zbliżenie na otok czapki z metką — model dostaje wyraźniejsze piksele napisu ACHTI."""
    from PIL import Image
    im = Image.open(pack).convert('RGB')
    w, h = im.size
    box = (int(w * 0.12), int(h * 0.52), int(w * 0.88), int(h * 0.88))
    crop = im.crop(box)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop.save(out, quality=95)
    return out


PROMPT_METKA = (
    'Image 1 is a finished fashion photograph. Image 2 is a close-up of the real product showing its small metal brand plate. '
    'Return image 1 completely unchanged except for one single detail: the small metal brand plate on the knitted hat. '
    'Redraw that plate so it is perfectly sharp and reads exactly ACHTI in small clean capital letters, with the same brushed-metal look, '
    'the same size, the same position and the same perspective as in image 1, matching the real plate in image 2. '
    'Absolutely nothing else may change: identical face, identical hair, identical hat knit and colour, identical clothing, identical background, '
    'identical framing, identical lighting and identical colour grading. Do not re-render the scene, do not crop, do not add any other text.'
)


def cmd_metka():
    """Drugie przejście: poprawia wyłącznie napis ACHTI na blaszce."""
    import glob
    src = ARGS.get('--plik')
    if not src or not os.path.exists(src):
        print('podaj --plik=<sciezka do wygenerowanego zdjecia>'); return
    code = ARGS.get('--code') or os.path.basename(src).split('_')[0]
    pack = packshot(code)
    if not pack:
        print('brak packshotu', code); return
    dest = os.path.dirname(src)
    crop = cuff_crop(pack, f'{dest}/_crop_{code}.jpg')
    out = ARGS.get('--out') or src.replace('.png', '-metka.png')
    t = time.time()
    ok = generate([part_image(src), part_image(crop), {'text': PROMPT_METKA}], out)
    print(('OK  ' if ok else 'BŁĄD'), os.path.basename(out), f'{time.time()-t:.0f}s')


SERIA_OBSADA = {'damskie': 'k4-braz', 'meskie': 'm2', 'dziewczeca': 'd1', 'chlopieca': 'c1'}
SERIA_SCENY = ['dwor', 'ogrod', 'aleja', 'stajnia', 'auto']


def cmd_seria():
    """Seria old money: lista kodów po segmentach, rotacja scen, jedna twarz na segment."""
    import glob
    plan = []
    for grupa, kody in (('damskie', ARGS.get('--damskie', '')), ('meskie', ARGS.get('--meskie', '')),
                        ('dziewczeca', ARGS.get('--dziewczece', '')), ('chlopieca', ARGS.get('--chlopiece', ''))):
        for i, code in enumerate([c for c in kody.split(',') if c]):
            plan.append((grupa, code, SERIA_SCENY[i % len(SERIA_SCENY)]))
    if not plan:
        print('podaj --damskie=KOD,KOD --meskie=... --dziewczece=... --chlopiece=...'); return
    dest = f'{ROOT}/modelki/seria'
    os.makedirs(dest, exist_ok=True)
    print(f'{len(plan)} zdjęć, {MODEL} {SIZE}, ~{len(plan)*(0.24 if SIZE=="4K" else 0.134):.2f} USD')

    def one(job):
        grupa, code, styl = job
        osoba = SERIA_OBSADA[grupa]
        pack = packshot(code)
        refs = sorted(glob.glob(f'{ROOT}/modelki/casting/{osoba}_*.png'))
        out = f'{dest}/{grupa}_{code}_{styl}.png'
        if not pack or not refs:
            print('brak materiału', code, osoba); return
        if os.path.exists(out) and '--force' not in FLAGS:
            print('jest', code); return
        cfg = dict(OLD_MONEY[styl])
        if grupa == 'dziewczeca':
            cfg['stylizacja'] = ('a child-sized cream wool coat over a fine cable-knit sweater, simple and age-appropriate, '
                                 'no jewellery, no scarf, no adult styling')
        elif grupa == 'chlopieca':
            cfg['stylizacja'] = ('a child-sized navy wool duffle coat over a cream cable-knit sweater and corduroy trousers, '
                                 'clearly a boy, age-appropriate, no jewellery, no scarf, no adult styling')
        t = time.time()
        ok = generate([part_image(pack), part_image(cuff_crop(pack, f'{dest}/_crop_{code}.jpg')), part_image(refs[0]),
                       {'text': PROMPT_OLDMONEY.format(what='hat (beanie)', **cfg)}], out)
        print(('OK  ' if ok else 'BŁĄD'), grupa, code, styl, f'{time.time()-t:.0f}s')

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, plan))


def cmd_oldmoney():
    """5 ujęć w stylu old money: czapka + osoba z castingu + sceneria posiadłości."""
    import glob
    code = ARGS.get('--code', 'AZ-2938')
    osoba = ARGS.get('--osoba', 'm2')
    styl = ARGS.get('--styl', 'dwor')
    what = ARGS.get('--kind', 'hat (beanie)')
    pack = packshot(code)
    refs = sorted(glob.glob(f'{ROOT}/modelki/casting/{osoba}_*.png'))
    if not pack or not refs:
        print('brak packshotu lub wzorca osoby', code, osoba); return
    dest = f'{ROOT}/modelki/oldmoney'
    os.makedirs(dest, exist_ok=True)
    crop = cuff_crop(pack, f'{dest}/_crop_{code}.jpg')
    out = f'{dest}/{code}_{osoba}_{styl}.png'
    t = time.time()
    ok = generate([part_image(pack), part_image(crop), part_image(refs[0]),
                   {'text': PROMPT_OLDMONEY.format(what=what, **OLD_MONEY[styl])}], out)
    print(('OK  ' if ok else 'BŁĄD'), os.path.basename(out), f'{time.time()-t:.0f}s')


def cmd_styl():
    """Ujęcia edytorialne: czapka + wybrana osoba z castingu + styl (kanapa/mur/kawiarnia/las)."""
    import glob
    code = ARGS.get('--code', 'AZ-2938')
    osoba = ARGS.get('--osoba', 'm2')
    styl = ARGS.get('--styl', 'kanapa')
    what = ARGS.get('--kind', 'hat (beanie)')
    pack = packshot(code)
    refs = sorted(glob.glob(f'{ROOT}/modelki/casting/{osoba}_*.png'))
    if not pack or not refs:
        print('brak packshotu lub wzorca osoby', code, osoba); return
    dest = f'{ROOT}/modelki/styl'
    os.makedirs(dest, exist_ok=True)
    out = f'{dest}/{code}_{osoba}_{styl}.png'
    cfg = STYLE[styl]
    t = time.time()
    ok = generate([part_image(pack), part_image(refs[0]),
                   {'text': PROMPT_STYL.format(what=what, **cfg)}], out)
    print(('OK  ' if ok else 'BŁĄD'), os.path.basename(out), f'{time.time()-t:.0f}s')


def cmd_casting():
    """Nowe twarze do wyboru: po 2 zdjęcia na osobę w różnych sceneriach, ta sama twarz w obu."""
    code = ARGS.get('--code', 'AZ-3101PC')
    code_kids = ARGS.get('--code-dzieci', 'AZ-2364PC')
    scenes = (ARGS.get('--sceny') or 'krakow-rynek,gory-snieg,jesien-park,krakow-kazimierz,zakopane,jesien-las').split(',')
    only = set(ARGS.get('--only', '').split(',')) - {''}
    dest = f'{ROOT}/modelki/casting'
    os.makedirs(dest, exist_ok=True)
    people = [(k, v) for k, v in CASTING.items() if not only or k in only]
    print(f'{len(people)} osób x 2 zdjęcia = {len(people)*2}, model {MODEL}, ~{len(people)*2*0.1355:.2f} USD')

    def one(job):
        n, (key, info) = job
        kid = info['typ'] in ('dziewczynka', 'chlopiec')
        pack = packshot(code_kids if kid else code)
        what = 'hat (beanie)'
        outfit = UBRANIE[info['typ']]
        s1, s2 = scenes[(n * 2) % len(scenes)], scenes[(n * 2 + 1) % len(scenes)]
        o1, o2 = f'{dest}/{key}_1_{s1}.png', f'{dest}/{key}_2_{s2}.png'
        t = time.time()
        if not (os.path.exists(o1) and '--force' not in FLAGS):
            ok = generate([part_image(pack), {'text': PROMPT_CAST.format(what=what, desc=info['desc'], scene=SCENY[s1], outfit=outfit, ref_note='')}], o1)
            if not ok:
                print('BŁĄD', key, '1'); return
        # drugie ujęcie z pierwszym zdjęciem jako wzorcem twarzy
        if not (os.path.exists(o2) and '--force' not in FLAGS):
            generate([part_image(pack), part_image(o1),
                      {'text': PROMPT_CAST.format(what=what, desc=info['desc'], scene=SCENY[s2], outfit=outfit, ref_note=REF_NOTE)}], o2)
        print('OK  ', key, info['typ'], f'{s1}/{s2}', f'{time.time()-t:.0f}s')

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, list(enumerate(people))))


def cmd_kandydatki():
    """Jedna czapka, wiele modelek — test plenerowy do wyboru twarzy."""
    code = ARGS.get('--code', 'AZ-3101PC')
    scene_key = ARGS.get('--scena', 'krakow-rynek')
    scene = SCENY[scene_key]
    what = 'hat (beanie)'
    pack = packshot(code)
    if not pack:
        print('brak packshotu', code); return
    only = set(ARGS.get('--only', '').split(',')) - {''}
    dest = f'{ROOT}/modelki/kandydatki'
    os.makedirs(dest, exist_ok=True)
    jobs = [(k, v) for k, v in KANDYDATKI.items() if not only or k in only]
    print(f'{len(jobs)} zdjęć, {code}, scena {scene_key}, model {MODEL}')

    def one(job):
        k, desc = job
        out = f'{dest}/{code}_{scene_key}_{k}.png'
        if os.path.exists(out) and '--force' not in FLAGS:
            print('jest', k); return
        t = time.time()
        ok = generate([part_image(pack), {'text': PROMPT_PLENER.format(desc=desc, scene=scene, what=what)}], out)
        print(('OK  ' if ok else 'BŁĄD'), k, f'{time.time()-t:.0f}s')

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, jobs))


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
    elif cmd == 'metka':
        cmd_metka()
    elif cmd == 'seria':
        cmd_seria()
    elif cmd == 'oldmoney':
        cmd_oldmoney()
    elif cmd == 'styl':
        cmd_styl()
    elif cmd == 'casting':
        cmd_casting()
    elif cmd == 'kandydatki':
        cmd_kandydatki()
    elif cmd == 'preview':
        cmd_preview()
    elif cmd == 'hat':
        kind = ARGS.get('--kind', 'hat (beanie)')
        ok = generate([part_image(sys.argv[2]), part_image(sys.argv[3]), {'text': PROMPT_HAT.format(what=kind)}], sys.argv[4])
        print('OK' if ok else 'BŁĄD', sys.argv[4])
    else:
        print(__doc__)
