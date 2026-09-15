"""Propozycja nowych nazw modeli — jedno źródło: imiona międzynarodowe, mitologia, astronomia, botanika łacińska.
Kryteria (wymagania Kamila 15.09.2026): łatwe do wymówienia (2–3 sylaby, ≤8 znaków, bez trudnych zbitek),
działają w PL/EN/DE/FR (bez polskich znaków, bez cj/sz/cz/rz), odmieniają się w polskim (-a = deklinacja żeńska,
spółgłoska = męska), brzmią premium. Gdzie się dało, zachowana pierwsza litera obecnej nazwy.
  python3 tools/nazwy_premium.py   -> tools/nazwy-propozycja.json
Naniesienie na sklep to osobny krok (apply_nazwy.py) — dopiero po akceptacji klienta."""
import re, json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ZLE = ('x', 'ph', 'th', 'sch', 'tz', 'ps', 'cj', 'sz', 'cz', 'rz', 'dz', 'ck')

def sylaby(n): return len(re.findall(r'[aeiouy]+', n.lower()))

def wymawialna(n, zenska=True, maxlen=8):
    l = n.lower()
    if zenska and not n.endswith('a'): return False
    if len(n) > maxlen or not 2 <= sylaby(n) <= 3: return False
    if any(t in l for t in ZLE) or any(c in l for c in 'ąćęłńóśźż'): return False
    return not re.search(r'[bcdfghjklmnpqrstvwz]{3}', l)

ZENSKIE = """Adela Adria Agata Alba Alina Alma Amara Amelia Amira Aniela Anita Anna Antonia Aria Arla Asta Aura
Aurora Beata Bella Berta Bianca Blanka Bona Bruna Cala Calla Camila Capella Cara Carina Carla Carmela Celia
Celina Chiara Cira Clara Cora Corina Dalia Dana Daniela Daria Delia Diana Dina Dione Donata Dora Edda Elana
Elara Elba Elena Elina Elisa Elma Elora Elsa Elvina Elvira Emilia Emira Emma Enola Enrica Erica Erina Estela
Europa Eva Evita Fabia Fabiana Felia Felina Fiona Fiora Flora Florina Fortuna Freja Gaia Gala Gemma Genova
Gianna Gilda Giulia Greta Halina Hanna Hela Helia Hera Hilda Ida Idalia Ilaria Ilona Inga Iona Irena Irina
Irma Isa Isla Isolda Ivana Ivona Iwona Jana Janina Jolena Juna Junona Kalia Kalina Kalisto Kamila Kara Karina
Karola Kira Klara Kora Lana Lara Larisa Larissa Laura Laurena Lavinia Leda Leila Lena Leona Liana Lidia Ligia
Lila Liliana Lina Liora Livia Lora Lorella Lorena Luca Lucia Lucila Lucina Luisa Luna Lyra Maia Malena Malina
Malva Malwina Manuela Mara Marcela Marena Maria Mariana Marika Marina Marisa Marla Marta Martina Melania
Melina Melisa Mila Milena Minerva Mira Mirela Mona Monika Morena Nadia Nadina Nara Nela Nerea Nerina Nicola
Nika Nikola Nilda Nina Noelia Nora Norna Nova Oda Odalia Odetta Ofelia Olena Olga Olimpia Olivia Oria Oriana
Orsola Otylia Palmira Paloma Pamela Patrycja Paula Paulina Pelagia Perina Perla Petra Polana Pomona Primula
Rafaela Ramona Rana Rebeca Regina Rena Renata Ricarda Rita Roma Romana Romina Rosa Rosalba Rosana Rosaria
Rosella Rosina Rosita Rozalia Rubina Ruta Sabina Sabrina Salina Salma Salvia Samanta Samira Sara Savina Sawa
Sela Selena Sena Sera Serafina Serena Silvana Silvia Simona Sofia Sola Solana Sonia Soraya Stella Susana
Sylvana Tala Tamara Tania Tara Tatiana Teodora Tessa Tina Titania Tiziana Tora Vala Valentina Valeria Vanda
Vanesa Vanina Vega Vela Venera Vera Verbena Verona Vesta Vida Vilma Viola Violeta Vita Vittoria Viviana Wanda
Wenera Wera Wilma Wiola Yolanda Zaira Zara Zaria Zelia Zenobia Zita Zoja Zora""".split()
KWIATY = """Azalea Begonia Calla Camelia Dalia Erica Freesia Gerbera Lantana Lavanda Linaria Lobelia Lunaria
Malva Mimosa Nemesia Nerina Nigella Peonia Petunia Primula Salvia Scilla Tulipa Vinca Viola Yucca Zinnia
Anemona Bellis Campanula Celosia Clivia Fuchsia Gloriosa Iberis Kalmia Nolina Portulaka Protea Rudbekia
Statice Tagetes Verbena Lilia Mirta Akacja Bergenia Hosta Kamelia Melisa Oliwa Rezeda""".split()
MINERALY = """Opal Topaz Agat Beryl Granat Rubin Nefryt Lazuryt Malachit Ametyst Cytryn Cyrkon Hematyt Larimar
Morganit Obsydian Peryd Prehnit Selenit Sodalit Rodonit Diopsyd Fluoryt Kunzyt Chalcedon Tanzanit Turmalin
Unakit Wariscyt Akwamaryn Bursztyn Karneol Koral Kwarc Perydot Piryt Rutyl Spinel Sylwin""".split()
DZIEWCZECE = """Mila Lena Nina Luna Maja Nela Lola Zoja Tola Kaja Lina Mira Nora Vita Sara Emma Alba Aria Cora
Dora Elsa Gala Hanna Ida Isa Juna Kara Kira Lara Leda Nika Nova Perla Rita Tara Tina Vera Zara Ania Iga Ina
Lia Mia Ewa Ola Bella Bruna Celia Dana Elena Fiona Gemma Hela Irena Jana Klara Lidia Marta Olga Rosa""".split()
CHLOPIECE = """Leo Milo Enzo Otto Aron Nico Remo Vito Hugo Bruno Elio Fabio Gino Ivo Lars Mateo Oskar Paolo
Silvio Tobia Ugo Dante Karol Marco Alan Emil Ivan Kamil Lukas Oliwer Rafal Tomas Viktor""".split()

def grupa(p):
    seg, typ = p.get('segment'), p.get('product_type')
    if seg == 'Dziewczęca': return 'dziewczece'
    if seg == 'Chłopięca': return 'chlopiece'
    if seg == 'Dziecięca': return 'dzieciece'
    if seg == 'Męska': return 'meskie'
    if typ == 'Opaska': return 'opaski'
    return 'damskie'

def odmiana(n):
    """Formy z rozmowy handlowej: „poproszę <biernik>", „kolory <dopełniacz>"."""
    if n.endswith('a'):
        rdz = n[:-1]
        return rdz + ('i' if n.endswith(('ia', 'ja', 'la', 'ka', 'ga')) else 'y'), rdz + 'ę'
    if n.endswith(('e', 'o', 'i', 'u')): return n, n
    return n + 'a', n

def main():
    prods = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
    Z = [n for n in dict.fromkeys(ZENSKIE) if wymawialna(n)]
    K = [n for n in dict.fromkeys(KWIATY) if wymawialna(n)]
    M = [n for n in dict.fromkeys(MINERALY) if wymawialna(n, zenska=False)]
    D = [n for n in dict.fromkeys(DZIEWCZECE) if wymawialna(n, maxlen=6)]
    C = [n for n in dict.fromkeys(CHLOPIECE) if wymawialna(n, zenska=False, maxlen=6)]
    PULE = {'damskie': Z, 'opaski': K + Z, 'meskie': M, 'dziewczece': D + Z, 'chlopiece': C + M, 'dzieciece': D + C}
    uzyte, wynik = set(), {}
    for etap in ('litera', 'reszta'):
        for p in sorted(prods, key=lambda x: x['code']):
            if p['code'] in wynik: continue
            g, stara = grupa(p), p.get('name', '')
            kand = [n for n in PULE[g] if n not in uzyte]
            if etap == 'litera':
                kand = [n for n in kand if stara[:1].upper() == n[:1].upper()]
                if not kand: continue
            if not kand: print('  BRAK NAZWY:', p['code'], g); continue
            dop, bier = odmiana(kand[0])
            wynik[p['code']] = {'stara': stara, 'nowa': kand[0], 'grupa': g, 'segment': p.get('segment'),
                                'typ': p.get('product_type'), 'dopelniacz': dop, 'biernik': bier}
            uzyte.add(kand[0])
    json.dump([dict(code=k, **v) for k, v in wynik.items()],
              open(os.path.join(HERE, 'nazwy-propozycja.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('przypisane:', len(wynik), dict(collections.Counter(v['grupa'] for v in wynik.values())))
    print('z zachowaną pierwszą literą:', sum(1 for v in wynik.values() if v['stara'][:1].upper() == v['nowa'][:1].upper()))
    return wynik

if __name__ == '__main__':
    main()
