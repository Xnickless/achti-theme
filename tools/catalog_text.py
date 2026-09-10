#!/usr/bin/env python3
"""Polskie tytuły i opisy produktów z danych arkusza Adriana (od 10.09.2026, arkusz „achti-katalog-v2 (2).xlsx”).
Tytuł: „Czapka zimowa damska Adela”, „Czapka zimowa męska Adam”, „Czapka zimowa dziewczęca Annie Mini”, „Opaska zimowa damska Sabine”.
Opis: własny tekst Adriana (kolumna opis) albo szablon; zawsze z listą cech i specyfikacją (kod, materiał, skład, podszycie, rozmiar)."""
import re

SEGMENTS = {  # segment -> (przymiotnik w tytule, fraza „model …” w opisie, tagi płci)
    'Damska': ('damska', 'damski', ['damskie']),
    'Męska': ('męska', 'męski', ['meskie']),
    'Unisex': ('unisex', 'unisex', ['damskie', 'meskie']),
    'Dziecięca': ('dziecięca', 'dla dzieci', ['dzieci']),
    'Chłopięca': ('chłopięca', 'dla chłopców', ['dzieci']),
    'Dziewczęca': ('dziewczęca', 'dla dziewczynek', ['dzieci']),
}
GENDER_TAGS = {'damskie', 'meskie', 'dzieci'}
LINING = {  # kolumna „podszycie” -> (fraza w opisie, cecha w liście)
    'Pełne podszycie polarowe 100% poliester': (' z pełnym podszyciem polarowym', 'Pełne podszycie polarowe (100% poliester)'),
    'Opaska polarowa 100% poliester': (' z polarową opaską w środku', 'Wewnętrzna opaska polarowa (100% poliester)'),
    'Podwójna dzianina': (' o podwójnej dzianinie', 'Podwójna dzianina — ciepła bez podszycia'),
    'Bez podszycia': ('', 'Pojedyncza dzianina, bez podszycia'),
}

def segment_from(plec, size, flags=()):
    """Kolumna Płeć („Ona”, „On”, „Unisex”, „Dla dzieci Dziewczynka/Chłopczyk/Unisex”) + rozmiar + flagi BOY/GIRL -> segment."""
    p = (plec or '').strip().lower()
    kids_size = bool(re.fullmatch(r'\d{2}-\d{2}', size or '')) and int(size[:2]) < 56
    if 'BOY' in flags or 'chłopczyk' in p or 'chłopiec' in p: return 'Chłopięca'
    if 'GIRL' in flags or 'dziewczynka' in p: return 'Dziewczęca'
    if 'dzieci' in p or 'dziecko' in p or kids_size: return 'Dziecięca'
    if p == 'on' or p.startswith('męs') or p.startswith('mes'): return 'Męska'
    if p == 'unisex': return 'Unisex'
    return 'Damska'

def product_kind(typ):
    t = (typ or '').lower()
    if t.startswith('opaska'): return 'Opaska'
    if t.startswith('komin'): return 'Komin'
    return 'Czapka'

def title_for(name, segment, kind):
    adj = SEGMENTS[segment][0]
    if kind == 'Komin': return f"Komin zimowy {adj.replace('ska', 'ski').replace('ęca', 'ęcy')} {name}"
    if kind == 'Opaska': return f"Opaska zimowa {adj} {name}"
    return f"Czapka zimowa {adj} {name}"

def body_for(name, segment, kind, mats, size, flags, code, sklad=None, podszycie=None, opis=None):
    who = SEGMENTS[segment][1]
    mat_txt = ' i '.join(mats) if mats else 'miękkiej dzianiny'
    lining_phrase, lining_feat = LINING.get(podszycie or '', ('', None))
    size_feat = 'Uniwersalny rozmiar' if size == 'One Size' else f'Rozmiar {size}'
    if kind == 'Komin':
        intro = f"Komin zimowy {name} to uniwersalny dodatek z dzianiny {mat_txt}{lining_phrase}, który zastępuje szalik i chroni szyję przed wiatrem. Klasyczna forma sprawdza się w codziennych stylizacjach i dobrze uzupełnia ofertę czapek."
        feats = ['Miękka, elastyczna dzianina', 'Nie uciska i nie krępuje ruchów', size_feat, 'Idealny na sezon jesień–zima']
    elif kind == 'Opaska':
        intro = f"Opaska zimowa {name} to model {who} z dzianiny {mat_txt}{lining_phrase}, który chroni uszy i czoło przed zimnem, nie spłaszczając fryzury. Sprawdza się na spacer, do biegania i na co dzień, a jej klasyczny wygląd łatwo łączy się z zimowymi stylizacjami."
        feats = ['Miękka, elastyczna dzianina', 'Zakrywa uszy, nie spłaszcza fryzury', size_feat, 'Idealna na sezon jesień–zima']
    else:
        intro = f"Czapka zimowa {name} to model {who} z dzianiny {mat_txt}{lining_phrase}, łączący klasyczny fason z wygodą noszenia. Dobrze trzyma kształt, jest ciepła i lekka, a jej ponadczasowy wygląd sprawia, że łatwo komponuje się z zimowymi stylizacjami."
        feats = ['Miękka i komfortowa dzianina', 'Elastyczny fason dopasowujący się do głowy', size_feat, 'Idealna na sezon jesień–zima']
        if 'CEKIN' in flags: feats.insert(1, 'Zdobienie cekinami')
        if 'MULTI' in flags: feats.insert(1, 'Wielokolorowy wzór')
        if 'BEZ POMPONA' in flags: feats.insert(1, 'Wersja bez pompona')
    if lining_feat: feats.insert(-2, lining_feat)
    if opis:
        # własny opis Adriana: pierwsze zdanie jako akapit wstępny (motyw pokazuje pierwszy akapit nad „Opis i specyfikacja”)
        txt = ' '.join(str(opis).split())
        m = re.match(r'(.+?[.!?])\s+(.+)$', txt)
        paras = [m.group(1), m.group(2)] if m else [txt]
        head = ''.join(f'<p>{x}</p>' for x in paras)
    else:
        head = f"<p>{intro}</p><p>Model {name} stanowi dobre uzupełnienie oferty sklepów odzieżowych, butików oraz punktów sprzedaży akcesoriów zimowych.</p>"
    spec = [f"Model: {name}", f"Kod: {code}", "Materiał: " + (', '.join(mats) or 'do uzupełnienia')]
    if sklad: spec.append("Skład: " + sklad)
    if podszycie: spec.append("Podszycie: " + podszycie)
    spec += ["Rozmiar: " + size, "Sezon: jesień / zima"]
    return (head + "<p><strong>Cechy produktu:</strong><br>" + "<br>".join('✔ ' + f for f in feats)
            + "</p><p><strong>Specyfikacja:</strong></p><ul>" + ''.join(f'<li>{x}</li>' for x in spec) + "</ul>")

def flags_from_old_title(title):
    """Flagi z dotychczasowego tytułu roboczego („… z Cekinami”, „… Multikolor”, „(bez pompona)”)."""
    f = []
    if 'z Cekinami' in title: f.append('CEKIN')
    if 'Multikolor' in title: f.append('MULTI')
    if '(bez pompona)' in title: f.append('BEZ POMPONA')
    return f
