#!/usr/bin/env python3
"""Generuje tłumaczenia EN/FR/DE dla katalogu (tytuły, opisy, metapola) z tego samego szablonu,
z którego powstały polskie opisy (generate_catalog.py), plus kolekcje, menu i teksty motywu.
Wynik: tools/translations/<locale>.json. Wgrywanie: tools/set_translations.py (wymaga scope write_translations)."""
import json, os, re

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, 'achti-produkty.json')
OUT = os.path.join(HERE, 'translations')
os.makedirs(OUT, exist_ok=True)

MATERIALS = {
    'Akryl': {'en': 'Acrylic', 'fr': 'Acrylique', 'de': 'Acryl'},
    'Sztuczne futro': {'en': 'Faux fur', 'fr': 'Fausse fourrure', 'de': 'Kunstfell'},
}
def mat(m, loc):
    return MATERIALS.get(m, {}).get(loc, m)

SEG = {  # segword -> (title prefix, "who" phrase)
    'en': {'Damska': ("Women's Winter Beanie", 'a women’s model'), 'Dziecięca': ("Kids' Winter Beanie", 'a children’s model'),
           'Męska': ("Men's Winter Beanie", 'a men’s model'), 'Unisex': ('Unisex Winter Beanie', 'a unisex model'),
           'Chłopięca': ("Boys' Winter Beanie", 'a boys’ model'), 'Dziewczęca': ("Girls' Winter Beanie", 'a girls’ model')},
    'fr': {'Damska': ("Bonnet d'hiver femme", 'un modèle femme'), 'Dziecięca': ("Bonnet d'hiver enfant", 'un modèle enfant'),
           'Męska': ("Bonnet d'hiver homme", 'un modèle homme'), 'Unisex': ("Bonnet d'hiver unisexe", 'un modèle unisexe'),
           'Chłopięca': ("Bonnet d'hiver garçon", 'un modèle garçon'), 'Dziewczęca': ("Bonnet d'hiver fille", 'un modèle fille')},
    'de': {'Damska': ('Damen-Wintermütze', 'ein Damenmodell'), 'Dziecięca': ('Kinder-Wintermütze', 'ein Kindermodell'),
           'Męska': ('Herren-Wintermütze', 'ein Herrenmodell'), 'Unisex': ('Unisex-Wintermütze', 'ein Unisex-Modell'),
           'Chłopięca': ('Jungen-Wintermütze', 'ein Jungenmodell'), 'Dziewczęca': ('Mädchen-Wintermütze', 'ein Mädchenmodell')},
}
KOMIN = {'en': "Women's Winter Snood", 'fr': "Snood d'hiver femme", 'de': 'Damen-Winterloop'}
SUFFIX = {'z Cekinami': {'en': 'with Sequins', 'fr': 'à sequins', 'de': 'mit Pailletten'},
          'Multikolor': {'en': 'Multicolour', 'fr': 'multicolore', 'de': 'mehrfarbig'}}

T = {
 'en': dict(
    intro_hat="Winter beanie {city} is {who} knitted from {mat}{lining}, combining a classic shape with everyday comfort. It keeps its shape, is warm and light, and its timeless look goes easily with winter outfits.",
    intro_snood="Winter snood {city} is a versatile accessory knitted from {mat}{lining} that replaces a scarf and protects the neck from wind. Its classic form works in everyday outfits and complements a beanie range well.",
    range_="Model {city} is a good addition to the range of clothing stores, boutiques and winter accessories retailers.",
    features="Product features:", spec="Specification:", model="Model", code="Code", material="Material", size="Size", season="Season", season_v="autumn / winter",
    f_hat=['Soft, comfortable knit', 'Stretchy shape that adapts to the head', 'One size fits all', 'Perfect for the autumn–winter season'],
    f_snood=['Soft, stretchy knit', 'No pressure, no restriction of movement', 'One size fits all', 'Perfect for the autumn–winter season'],
    intro_headband="Winter headband {city} is a women’s model knitted from {mat}{lining} that keeps ears and forehead warm without flattening the hair. It works for walks, running and everyday wear, and its classic look goes easily with winter outfits.",
    f_headband=['Soft, stretchy knit', 'Covers the ears without flattening the hair', 'One size fits all', 'Perfect for the autumn–winter season'],
    composition='Composition', lining='Lining',
    f_size='Size {size}', f_sequins='Sequin embellishment', f_multi='Multicolour pattern', one_size='One Size', one_size_feat='One size fits all', soft='soft knit', and_=' and ',
 ),
 'fr': dict(
    intro_hat="Le bonnet d'hiver {city} est {who} en maille {mat}{lining}, qui allie une coupe classique au confort au quotidien. Il garde bien sa forme, il est chaud et léger, et son style intemporel s'accorde facilement aux tenues d'hiver.",
    intro_snood="Le snood d'hiver {city} est un accessoire polyvalent en maille {mat}{lining} qui remplace l'écharpe et protège le cou du vent. Sa forme classique convient aux tenues de tous les jours et complète bien une gamme de bonnets.",
    range_="Le modèle {city} complète bien l'offre des magasins de vêtements, des boutiques et des points de vente d'accessoires d'hiver.",
    features="Caractéristiques du produit :", spec="Spécifications :", model="Modèle", code="Code", material="Matière", size="Taille", season="Saison", season_v="automne / hiver",
    f_hat=['Maille douce et confortable', 'Coupe élastique qui s\'adapte à la tête', 'Taille unique', 'Idéal pour la saison automne–hiver'],
    f_snood=['Maille douce et élastique', 'Ne serre pas et ne gêne pas les mouvements', 'Taille unique', 'Idéal pour la saison automne–hiver'],
    intro_headband="Le bandeau d'hiver {city} est un modèle femme en maille {mat}{lining} qui protège les oreilles et le front du froid sans aplatir la coiffure. Il convient à la promenade, à la course et au quotidien, et son style classique s'accorde facilement aux tenues d'hiver.",
    f_headband=['Maille douce et élastique', 'Couvre les oreilles sans aplatir la coiffure', 'Taille unique', 'Idéal pour la saison automne–hiver'],
    composition='Composition', lining='Doublure',
    f_size='Taille {size}', f_sequins='Décor à sequins', f_multi='Motif multicolore', one_size='Taille unique', one_size_feat='Taille unique', soft='maille douce', and_=' et ',
 ),
 'de': dict(
    intro_hat="Die Wintermütze {city} ist {who} aus {mat}-Strick{lining}, das eine klassische Form mit hohem Tragekomfort verbindet. Sie behält ihre Form, ist warm und leicht, und ihr zeitloses Aussehen lässt sich leicht mit Winteroutfits kombinieren.",
    intro_snood="Der Winterloop {city} ist ein vielseitiges Accessoire aus {mat}-Strick{lining}, das den Schal ersetzt und den Hals vor Wind schützt. Die klassische Form passt zu Alltagsoutfits und ergänzt ein Mützensortiment gut.",
    range_="Das Modell {city} ist eine gute Ergänzung des Sortiments von Bekleidungsgeschäften, Boutiquen und Verkaufsstellen für Winteraccessoires.",
    features="Produktmerkmale:", spec="Spezifikation:", model="Modell", code="Artikelnummer", material="Material", size="Größe", season="Saison", season_v="Herbst / Winter",
    f_hat=['Weicher, angenehmer Strick', 'Elastische Form, die sich dem Kopf anpasst', 'Einheitsgröße', 'Ideal für die Herbst-Winter-Saison'],
    f_snood=['Weicher, elastischer Strick', 'Drückt nicht und schränkt die Bewegung nicht ein', 'Einheitsgröße', 'Ideal für die Herbst-Winter-Saison'],
    intro_headband="Das Winterstirnband {city} ist ein Damenmodell aus {mat}-Strick{lining}, das Ohren und Stirn warm hält, ohne die Frisur plattzudrücken. Es eignet sich für Spaziergänge, zum Laufen und für den Alltag, und sein klassischer Look lässt sich leicht mit Winteroutfits kombinieren.",
    f_headband=['Weicher, elastischer Strick', 'Bedeckt die Ohren, ohne die Frisur plattzudrücken', 'Einheitsgröße', 'Ideal für die Herbst-Winter-Saison'],
    composition='Zusammensetzung', lining='Futter',
    f_size='Größe {size}', f_sequins='Paillettenverzierung', f_multi='Mehrfarbiges Muster', one_size='Einheitsgröße', one_size_feat='Einheitsgröße', soft='weichem Strick', and_=' und ',
 ),
}

VARIANT = {'Turbo': {'en': 'Turbo', 'fr': 'Turbo', 'de': 'Turbo'},
           'bez pompona': {'en': 'without pompom', 'fr': 'sans pompon', 'de': 'ohne Bommel'}}
F_NOPOM = {'en': 'Version without pompom', 'fr': 'Version sans pompon', 'de': 'Version ohne Bommel'}
RX = re.compile(r'^(Czapka Zimowa (Damska|Dziecięca|Chłopięca|Dziewczęca) Beanie|Komin Zimowy Damski|Opaska Zimowa Damska) (\S+(?: \S+)*?)( z Cekinami)?( Multikolor)?(?: \((Turbo|bez pompona)\))?$')
HEADBAND = {'en': "Women's Winter Headband", 'fr': "Bandeau d'hiver femme", 'de': 'Damen-Winterstirnband'}
# kolumna „podszycie” z arkusza Adriana (10.09.2026) -> (fraza w intro, cecha, wiersz specyfikacji)
LINING = {
 'Pełne podszycie polarowe 100% poliester': {
    'en': (' with a full fleece lining', 'Full fleece lining (100% polyester)', 'Full fleece lining, 100% polyester'),
    'fr': (' entièrement doublé polaire', 'Doublure polaire intégrale (100 % polyester)', 'Doublure polaire intégrale, 100 % polyester'),
    'de': (' mit durchgehendem Fleecefutter', 'Durchgehendes Fleecefutter (100 % Polyester)', 'Durchgehendes Fleecefutter, 100 % Polyester')},
 'Opaska polarowa 100% poliester': {
    'en': (' with an inner fleece band', 'Inner fleece band (100% polyester)', 'Inner fleece band, 100% polyester'),
    'fr': (' avec bandeau intérieur en polaire', 'Bandeau intérieur en polaire (100 % polyester)', 'Bandeau intérieur en polaire, 100 % polyester'),
    'de': (' mit Fleece-Innenband', 'Fleece-Innenband (100 % Polyester)', 'Fleece-Innenband, 100 % Polyester')},
 'Podwójna dzianina': {
    'en': (' in a double-layer knit', 'Double-layer knit — warm without lining', 'Double-layer knit, unlined'),
    'fr': (' en maille double épaisseur', 'Maille double épaisseur — chaude sans doublure', 'Maille double épaisseur, sans doublure'),
    'de': (' in doppellagigem Strick', 'Doppellagiger Strick — warm ohne Futter', 'Doppellagiger Strick, ungefüttert')},
 'Bez podszycia': {
    'en': ('', 'Single-layer knit, unlined', 'None (single-layer knit)'),
    'fr': ('', 'Maille simple, sans doublure', 'Sans doublure (maille simple)'),
    'de': ('', 'Einlagiger Strick, ungefüttert', 'Ohne Futter (einlagiger Strick)')},
}
FIBRES = {  # skład surowcowy: nazwy włókien PL -> EN/FR/DE (dłuższe frazy pierwsze)
 'wełna merino': {'en': 'merino wool', 'fr': 'laine mérinos', 'de': 'Merinowolle'},
 'wełna': {'en': 'wool', 'fr': 'laine', 'de': 'Wolle'},
 'akryl': {'en': 'acrylic', 'fr': 'acrylique', 'de': 'Acryl'},
 'poliamid': {'en': 'polyamide', 'fr': 'polyamide', 'de': 'Polyamid'},
 'poliester': {'en': 'polyester', 'fr': 'polyester', 'de': 'Polyester'},
 'wiskoza': {'en': 'viscose', 'fr': 'viscose', 'de': 'Viskose'},
 'nylon': {'en': 'nylon', 'fr': 'nylon', 'de': 'Nylon'},
 'elastan': {'en': 'elastane', 'fr': 'élasthanne', 'de': 'Elasthan'},
 'bawełna': {'en': 'cotton', 'fr': 'coton', 'de': 'Baumwolle'},
}
def comp(sklad, loc):
    """'85% akryl, 15% poliamid' -> '85% acrylic, 15% polyamide' (FR/DE: spacja przed %, przecinek dziesiętny zostaje)."""
    if not sklad: return ''
    out = sklad
    for pl, tr in FIBRES.items():
        out = re.sub(r'\b' + pl + r'\b', tr[loc], out, flags=re.I)
    if loc == 'en': out = re.sub(r'(\d),(\d)', r'\1.\2', out)
    else: out = re.sub(r'(\d)%', r'\1 %', out)
    return out

OPIS_OVERRIDES_PATH = os.path.join(OUT, 'opis-overrides.json')  # ręczne tłumaczenia własnych opisów Adriana: {kod: {en: [akapity], fr: [...], de: [...]}}
OPIS_OVERRIDES = json.load(open(OPIS_OVERRIDES_PATH, encoding='utf-8')) if os.path.exists(OPIS_OVERRIDES_PATH) else {}

def translate_product(p, loc):
    t = T[loc]
    if p.get('name'):
        name, seg, kind, flags = p['name'], p.get('segment', 'Damska'), p.get('product_type', 'Czapka'), set(p.get('flags') or [])
        variant = None
    else:  # stare wpisy z tytułem roboczym „Czapka Zimowa Damska Beanie Milano (Turbo)”
        m = RX.match(p['title'])
        if not m: return None
        kind = 'Komin' if m.group(1).startswith('Komin') else 'Opaska' if m.group(1).startswith('Opaska') else 'Czapka'
        seg = m.group(2) or 'Damska'; name = m.group(3)
        flags = {f for f, g in (('CEKIN', 4), ('MULTI', 5)) if m.group(g)}
        if m.group(6) == 'bez pompona': flags.add('BEZ POMPONA')
        variant = m.group(6)
    is_snood, is_headband = kind == 'Komin', kind == 'Opaska'
    mats = [mat(x, loc) for x in p['materials']]
    mat_txt = t['and_'].join(mats) if mats else t['soft']
    size = p['size']
    lin = LINING.get(p.get('podszycie') or '', {}).get(loc)
    lining_phrase = lin[0] if lin else ''
    size_feat = t['one_size_feat'] if size == 'One Size' else t['f_size'].format(size=size)
    if is_snood:
        title = f"{KOMIN[loc]} {name}"
        intro = t['intro_snood'].format(city=name, mat=mat_txt, lining=lining_phrase)
        feats = list(t['f_snood']); feats[2] = size_feat
    elif is_headband:
        title = f"{HEADBAND[loc]} {name}"
        intro = t['intro_headband'].format(city=name, mat=mat_txt, lining=lining_phrase)
        feats = list(t['f_headband']); feats[2] = size_feat
    else:
        prefix, who = SEG[loc][seg]
        title = f"{prefix} {name}"
        intro = t['intro_hat'].format(city=name, who=who, mat=mat_txt, lining=lining_phrase)
        feats = list(t['f_hat']); feats[2] = size_feat
        if 'MULTI' in flags: feats.insert(1, t['f_multi'])
        if 'CEKIN' in flags: feats.insert(1, t['f_sequins'])
        if 'BEZ POMPONA' in flags: feats.insert(1, F_NOPOM[loc])
    if lin: feats.insert(-2, lin[1])
    if variant:  # tylko stare tytuły robocze
        sfx = [SUFFIX[k][loc] for k, f in (('z Cekinami', 'CEKIN'), ('Multikolor', 'MULTI')) if f in flags]
        if sfx: title += ' ' + ' '.join(sfx)
        title += f" ({VARIANT[variant][loc]})"
    size_txt = t['one_size'] if size == 'One Size' else size
    sklad = comp(p.get('sklad'), loc)
    spec = [f"{t['model']}: {name}", f"{t['code']}: {p['code']}", f"{t['material']}: {', '.join(mats) if mats else '—'}"]
    if sklad: spec.append(f"{t['composition']}: {sklad}")
    if lin: spec.append(f"{t['lining']}: {lin[2]}")
    spec += [f"{t['size']}: {size_txt}", f"{t['season']}: {t['season_v']}"]
    ov = OPIS_OVERRIDES.get(p['code'], {}).get(loc)
    if p.get('opis') and not ov:
        print(f"  UWAGA {loc}: brak tłumaczenia własnego opisu {p['code']} w {OPIS_OVERRIDES_PATH} — użyty szablon")
    head = ''.join(f'<p>{x}</p>' for x in ov) if ov else f"<p>{intro}</p><p>{t['range_'].format(city=name)}</p>"
    body = (head + f"<p><strong>{t['features']}</strong><br>" + '<br>'.join('✔ ' + f for f in feats)
            + f"</p><p><strong>{t['spec']}</strong></p><ul>" + ''.join(f'<li>{x}</li>' for x in spec) + "</ul>")
    return {'title': title, 'body_html': body, 'metafields': {'custom.rozmiar': size_txt, 'custom.sklad': sklad or ', '.join(mats)}}

COLLECTIONS = {
 'en': {'kolekcja-damska': ('Women', "Achti women's winter hats: classic shapes, seasonal patterns, made in Poland."),
        'kolekcja-meska': ('Men', "Men's winter hats: classic shapes, muted colours, durable knit."),
        'kolekcja-dla-dzieci': ('Kids', "Children's winter hats in sizes 50–52 and 52–54: warm, soft, colourful."),
        'kolekcja-premium': ('Premium Merino', 'Merino wool hats, 100% or blended with acrylic: light, breathable, warm.'),
        'private-label': ('Private Label', 'Hat production under your brand: woven labels, tags, embroidery, custom colours.'),
        'czapki-reklamowe': ('Promotional Hats', 'Hats with your logo: embroidery, print or woven label. Choose the model, colours and branding and we will prepare a quote.'),
        'wyprzedaz': ('Sale', 'End-of-season models at reduced prices.'),
        'nowosci': ('New Arrivals', 'The newest models in the Achti range.'),
        'najpopularniejsze': ('Bestsellers', 'The most frequently ordered models.'),
        'bestsellery': ('Bestsellers', ''), 'all': ('All products', '')},
 'fr': {'kolekcja-damska': ('Femme', "Bonnets d'hiver femme Achti : coupes classiques, motifs de saison, fabriqués en Pologne."),
        'kolekcja-meska': ('Homme', "Bonnets d'hiver homme : coupes classiques, couleurs sobres, maille résistante."),
        'kolekcja-dla-dzieci': ('Enfant', "Bonnets d'hiver enfant en 50–52 et 52–54 : chauds, doux, colorés."),
        'kolekcja-premium': ('Premium Mérinos', 'Bonnets en laine mérinos, 100 % ou mélangée à l’acrylique : légers, respirants, chauds.'),
        'private-label': ('Private Label', 'Bonnets sous votre marque : étiquettes tissées, broderies, couleurs personnalisées.'),
        'czapki-reklamowe': ('Bonnets publicitaires', 'Bonnets à votre logo : broderie, impression ou étiquette tissée. Choisissez le modèle, les couleurs et le marquage, nous préparons le devis.'),
        'wyprzedaz': ('Soldes', 'Modèles de fin de saison à prix réduits.'),
        'nowosci': ('Nouveautés', "Les derniers modèles de la gamme Achti."),
        'najpopularniejsze': ('Meilleures ventes', 'Les modèles les plus commandés.'),
        'bestsellery': ('Meilleures ventes', ''), 'all': ('Tous les produits', '')},
 'de': {'kolekcja-damska': ('Damen', 'Damen-Wintermützen von Achti: klassische Formen, Saisonmuster, hergestellt in Polen.'),
        'kolekcja-meska': ('Herren', 'Herren-Wintermützen: klassische Formen, gedeckte Farben, strapazierfähiger Strick.'),
        'kolekcja-dla-dzieci': ('Kinder', 'Kinder-Wintermützen in 50–52 und 52–54: warm, weich, bunt.'),
        'kolekcja-premium': ('Premium Merino', 'Mützen aus Merinowolle, 100 % oder mit Acryl gemischt: leicht, atmungsaktiv, warm.'),
        'private-label': ('Private Label', 'Mützen unter Ihrer Marke: Webetiketten, Anhänger, Stickerei, individuelle Farben.'),
        'czapki-reklamowe': ('Werbemützen', 'Mützen mit Ihrem Logo: Stickerei, Druck oder Webetikett. Wählen Sie Modell, Farben und Veredelung, wir erstellen das Angebot.'),
        'wyprzedaz': ('Sale', 'Modelle zum Saisonende zu reduzierten Preisen.'),
        'nowosci': ('Neuheiten', 'Die neuesten Modelle im Achti-Sortiment.'),
        'najpopularniejsze': ('Bestseller', 'Die am häufigsten bestellten Modelle.'),
        'bestsellery': ('Bestseller', ''), 'all': ('Alle Produkte', '')},
}

MENU = {  # tytuł PL -> tłumaczenie
 'en': {'Ona': 'Women', 'On': 'Men', 'Dla dzieci': 'Kids', 'Premium Merino': 'Premium Merino', 'Private Label': 'Private Label', 'Czapki Reklamowe': 'Promotional Hats', 'Wyprzedaż': 'Sale',
        'O nas': 'About us', 'Produkcja': 'Production', 'Materiały': 'Materials', 'Jakość': 'Quality', 'Zrównoważony rozwój': 'Sustainability', 'Blog': 'Blog', 'Kontakt': 'Contact',
        'Logowanie B2B': 'B2B login', 'Rejestracja firmy': 'Company registration', 'Warunki współpracy': 'Terms of cooperation', 'Wysyłka i dostawa': 'Shipping & delivery', 'Zwroty i reklamacje': 'Returns & claims', 'FAQ': 'FAQ', 'Regulamin B2B': 'B2B Terms of Service', 'Polityka cookies': 'Cookie policy',
        'Szukaj': 'Search', 'Kolekcje': 'Collections', 'Informacje': 'Information', 'Obsługa klienta': 'Customer service'},
 'fr': {'Ona': 'Femme', 'On': 'Homme', 'Dla dzieci': 'Enfant', 'Premium Merino': 'Premium Mérinos', 'Private Label': 'Private Label', 'Czapki Reklamowe': 'Bonnets publicitaires', 'Wyprzedaż': 'Soldes',
        'O nas': 'À propos', 'Produkcja': 'Production', 'Materiały': 'Matières', 'Jakość': 'Qualité', 'Zrównoważony rozwój': 'Développement durable', 'Blog': 'Blog', 'Kontakt': 'Contact',
        'Logowanie B2B': 'Connexion B2B', 'Rejestracja firmy': "Inscription de l'entreprise", 'Warunki współpracy': 'Conditions de coopération', 'Wysyłka i dostawa': 'Expédition et livraison', 'Zwroty i reklamacje': 'Retours et réclamations', 'FAQ': 'FAQ', 'Regulamin B2B': 'CGV B2B', 'Polityka cookies': 'Politique de cookies',
        'Szukaj': 'Rechercher', 'Kolekcje': 'Collections', 'Informacje': 'Informations', 'Obsługa klienta': 'Service client'},
 'de': {'Ona': 'Damen', 'On': 'Herren', 'Dla dzieci': 'Kinder', 'Premium Merino': 'Premium Merino', 'Private Label': 'Private Label', 'Czapki Reklamowe': 'Werbemützen', 'Wyprzedaż': 'Sale',
        'O nas': 'Über uns', 'Produkcja': 'Produktion', 'Materiały': 'Materialien', 'Jakość': 'Qualität', 'Zrównoważony rozwój': 'Nachhaltigkeit', 'Blog': 'Blog', 'Kontakt': 'Kontakt',
        'Logowanie B2B': 'B2B-Login', 'Rejestracja firmy': 'Firmenregistrierung', 'Warunki współpracy': 'Kooperationsbedingungen', 'Wysyłka i dostawa': 'Versand und Lieferung', 'Zwroty i reklamacje': 'Rücksendungen und Reklamationen', 'FAQ': 'FAQ', 'Regulamin B2B': 'B2B-AGB', 'Polityka cookies': 'Cookie-Richtlinie',
        'Szukaj': 'Suchen', 'Kolekcje': 'Kollektionen', 'Informacje': 'Informationen', 'Obsługa klienta': 'Kundenservice'},
}

THEME = {  # teksty z ustawień motywu (klucz = tekst PL)
 'en': { "Zapisz się do newslettera i odbierz −15% na pierwsze zamówienie": "Join our newsletter and get −15% on your first order",
        "−15% na pierwsze zamówienie": "−15% on your first order",
        "Zapisz się, a wyślemy Ci kod rabatowy na pierwsze zamówienie hurtowe. Do tego jako pierwszy dostaniesz informacje o nowych kolekcjach i ofertach dla partnerów.": "Sign up and we will send you a discount code for your first wholesale order. You will also be the first to hear about new collections and partner offers.",
        "Odbieram rabat": "Get my discount",
        "Zapisz się i odbierz −15% na pierwsze zamówienie.": "Sign up and get −15% on your first order.",
        "Newsletter B2B": "B2B newsletter",
       'Witamy na naszej platformie B2B': 'Welcome to our B2B platform', 'Inne kolory tego modelu': 'Other colours of this model', 'realizacja 7–14 dni roboczych': 'lead time 7–14 business days',
        'Opis i specyfikacja': 'Description and specification', 'Rozmiar': 'Size', 'Skład': 'Composition', 'Kolor': 'Colour', 'Cena netto — VAT naliczany w koszyku': 'Net price — VAT added in the cart',
        'Czapki, kominy i kominiarki dla Twojego sklepu': 'Hats, snoods and balaclavas for your store', 'Czapki reklamowe': 'Promotional hats', 'Ceny hurtowe dla firm — produkcja w Polsce, także private label.': 'Wholesale prices for companies — made in Poland, private label available.',
        'Sprawdź ofertę': 'See the range', 'Załóż konto firmowe': 'Open a company account', 'Nowości': 'New arrivals', 'Bestsellery': 'Bestsellers', 'Inni klienci też kupili': 'Customers also bought', 'Najbardziej popularne': 'Most popular',
        'Newsletter': 'Newsletter', 'Zapisz się, aby otrzymywać informacje o nowościach i kolekcjach.': 'Sign up to receive news about new models and collections.', 'Tylko dla klientów B2B': 'B2B customers only',
        'Tworzymy czapki z pasją od ponad 30 lat. Wysoka jakość, naturalne materiały i ponadczasowy design.': 'We have been making hats with passion for over 30 years. High quality, natural materials and timeless design.',
        'Ceny dostępne po zalogowaniu': 'Prices available after login', 'Masz pytania? Napisz do nas.': 'Questions? Write to us.', 'Producent': 'Manufacturer', 'Szybkie zamawianie': 'Quick order'},
 'fr': { "Zapisz się do newslettera i odbierz −15% na pierwsze zamówienie": "Inscrivez-vous à la newsletter et recevez −15 % sur votre première commande",
        "−15% na pierwsze zamówienie": "−15 % sur votre première commande",
        "Zapisz się, a wyślemy Ci kod rabatowy na pierwsze zamówienie hurtowe. Do tego jako pierwszy dostaniesz informacje o nowych kolekcjach i ofertach dla partnerów.": "Inscrivez-vous et nous vous enverrons un code de réduction pour votre première commande en gros. Vous serez aussi informé en premier des nouvelles collections et des offres partenaires.",
        "Odbieram rabat": "Je profite de la remise",
        "Zapisz się i odbierz −15% na pierwsze zamówienie.": "Inscrivez-vous et recevez −15 % sur votre première commande.",
        "Newsletter B2B": "Newsletter B2B",
       'Witamy na naszej platformie B2B': 'Bienvenue sur notre plateforme B2B', 'Inne kolory tego modelu': 'Autres couleurs de ce modèle', 'realizacja 7–14 dni roboczych': 'délai 7 à 14 jours ouvrés',
        'Opis i specyfikacja': 'Description et spécifications', 'Rozmiar': 'Taille', 'Skład': 'Composition', 'Kolor': 'Couleur', 'Cena netto — VAT naliczany w koszyku': 'Prix HT — TVA ajoutée dans le panier',
        'Czapki, kominy i kominiarki dla Twojego sklepu': 'Bonnets, snoods et cagoules pour votre boutique', 'Czapki reklamowe': 'Bonnets publicitaires', 'Ceny hurtowe dla firm — produkcja w Polsce, także private label.': 'Prix de gros pour les professionnels — fabrication en Pologne, private label possible.',
        'Sprawdź ofertę': "Voir l'offre", 'Załóż konto firmowe': 'Créer un compte professionnel', 'Nowości': 'Nouveautés', 'Bestsellery': 'Meilleures ventes', 'Inni klienci też kupili': 'Les clients ont aussi acheté', 'Najbardziej popularne': 'Les plus populaires',
        'Newsletter': 'Newsletter', 'Zapisz się, aby otrzymywać informacje o nowościach i kolekcjach.': 'Inscrivez-vous pour recevoir les nouveautés et les collections.', 'Tylko dla klientów B2B': 'Réservé aux clients B2B',
        'Tworzymy czapki z pasją od ponad 30 lat. Wysoka jakość, naturalne materiały i ponadczasowy design.': 'Nous fabriquons des bonnets avec passion depuis plus de 30 ans. Haute qualité, matières naturelles et design intemporel.',
        'Ceny dostępne po zalogowaniu': 'Prix visibles après connexion', 'Masz pytania? Napisz do nas.': 'Des questions ? Écrivez-nous.', 'Producent': 'Fabricant', 'Szybkie zamawianie': 'Commande rapide'},
 'de': { "Zapisz się do newslettera i odbierz −15% na pierwsze zamówienie": "Newsletter abonnieren und −15 % auf die erste Bestellung sichern",
        "−15% na pierwsze zamówienie": "−15 % auf die erste Bestellung",
        "Zapisz się, a wyślemy Ci kod rabatowy na pierwsze zamówienie hurtowe. Do tego jako pierwszy dostaniesz informacje o nowych kolekcjach i ofertach dla partnerów.": "Melden Sie sich an und wir senden Ihnen einen Rabattcode für Ihre erste Großhandelsbestellung. Außerdem erfahren Sie als Erste von neuen Kollektionen und Partnerangeboten.",
        "Odbieram rabat": "Rabatt sichern",
        "Zapisz się i odbierz −15% na pierwsze zamówienie.": "Anmelden und −15 % auf die erste Bestellung sichern.",
        "Newsletter B2B": "B2B-Newsletter",
       'Witamy na naszej platformie B2B': 'Willkommen auf unserer B2B-Plattform', 'Inne kolory tego modelu': 'Weitere Farben dieses Modells', 'realizacja 7–14 dni roboczych': 'Lieferzeit 7–14 Werktage',
        'Opis i specyfikacja': 'Beschreibung und Spezifikation', 'Rozmiar': 'Größe', 'Skład': 'Zusammensetzung', 'Kolor': 'Farbe', 'Cena netto — VAT naliczany w koszyku': 'Nettopreis — MwSt. wird im Warenkorb berechnet',
        'Czapki, kominy i kominiarki dla Twojego sklepu': 'Mützen, Loops und Sturmhauben für Ihr Geschäft', 'Czapki reklamowe': 'Werbemützen', 'Ceny hurtowe dla firm — produkcja w Polsce, także private label.': 'Großhandelspreise für Firmen — Produktion in Polen, auch Private Label.',
        'Sprawdź ofertę': 'Sortiment ansehen', 'Załóż konto firmowe': 'Firmenkonto anlegen', 'Nowości': 'Neuheiten', 'Bestsellery': 'Bestseller', 'Inni klienci też kupili': 'Andere Kunden kauften auch', 'Najbardziej popularne': 'Am beliebtesten',
        'Newsletter': 'Newsletter', 'Zapisz się, aby otrzymywać informacje o nowościach i kolekcjach.': 'Melden Sie sich an, um Neuheiten und Kollektionen zu erhalten.', 'Tylko dla klientów B2B': 'Nur für B2B-Kunden',
        'Tworzymy czapki z pasją od ponad 30 lat. Wysoka jakość, naturalne materiały i ponadczasowy design.': 'Seit über 30 Jahren fertigen wir Mützen mit Leidenschaft. Hohe Qualität, natürliche Materialien und zeitloses Design.',
        'Ceny dostępne po zalogowaniu': 'Preise nach Anmeldung sichtbar', 'Masz pytania? Napisz do nas.': 'Fragen? Schreiben Sie uns.', 'Producent': 'Hersteller', 'Szybkie zamawianie': 'Schnellbestellung'},
}

if __name__ == '__main__':
    products = json.load(open(SRC, encoding='utf-8'))
    for loc in ('en', 'fr', 'de'):
        out = {'products': {}, 'collections': COLLECTIONS[loc], 'menu': MENU[loc], 'theme': THEME[loc]}
        missed = []
        for p in products:
            tr = translate_product(p, loc)
            if tr: out['products'][p['code']] = tr
            else: missed.append(p['title'])
        json.dump(out, open(os.path.join(OUT, f'{loc}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(loc, 'produkty:', len(out['products']), 'pominięte:', missed[:5])
