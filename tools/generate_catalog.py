#!/usr/bin/env python3
"""Buduje dane produktów z arkusza achti-katalog-do-uzupelnienia.csv (nazwy robocze, opisy, tagi).
Wynik: tools/achti-produkty.json + ~/Downloads/achti-produkty-nazwy.csv (podgląd dla klienta)."""
import csv, json, os, re, sys, unicodedata
SRC=os.path.expanduser('~/Downloads/achti-katalog-do-uzupelnienia.csv')
PHOTOS=os.path.expanduser('~/Downloads/ACHTI COLLECTION 2026-2027 - biale tlo')
OUT_JSON=os.path.join(os.path.dirname(__file__),'achti-produkty.json')
OUT_CSV=os.path.expanduser('~/Downloads/achti-produkty-nazwy.csv')
SKIP_CODES={'AZ-3101PC'}  # już istnieje w sklepie (Barcelona)

CITIES="""Milano Roma Torino Verona Firenze Napoli Bologna Genova Venezia Padova Parma Modena Siena Pisa Lucca Como Bergamo Trento Bolzano Cortina Livigno Aosta Rimini Ravenna Trieste Udine Vicenza Mantova Cremona Ancona Perugia Assisi Orvieto Sorrento Amalfi Capri Positano Palermo Catania Cagliari Sassari Lecce Bari Matera Salerno Ferrara Arezzo Bergen Oslo Tromso Alta Narvik Bodo Lofoten Stavanger Trondheim Lillehammer Geilo Hemsedal Stockholm Goteborg Malmo Uppsala Lund Umea Kiruna Lulea Abisko Are Visby Helsinki Espoo Turku Tampere Oulu Rovaniemi Levi Lapland Kuopio Vaasa Kopenhaga Aarhus Odense Aalborg Roskilde Reykjavik Akureyri Wiedeń Salzburg Innsbruck Graz Linz Kitzbuhel Zell Lech Ischgl Solden Bregenz Villach Bad Gastein Zurych Genewa Bazylea Berno Lucerna Lugano Zermatt Davos Gstaad Verbier Interlaken Grindelwald Montreux Lozanna Chur Arosa Andermatt Engelberg Saas Fee Crans Paryż Lyon Nicea Cannes Antibes Annecy Chamonix Megeve Grenoble Bordeaux Tuluza Nantes Rennes Lille Strasburg Colmar Dijon Awinion Marsylia Biarritz Deauville Honfleur Courchevel Meribel Tignes Alpe Val Thorens Chambery Monaco Madryt Sewilla Walencja Malaga Granada Kordoba Bilbao Toledo Salamanca Segovia Girona Sitges Cadaques Ronda Marbella Ibiza Mallorca Menorca Lizbona Porto Sintra Cascais Faro Coimbra Braga Evora Madera Azory Londyn Oxford Cambridge Bath York Edynburg Glasgow Inverness Aberdeen Dublin Cork Galway Belfast Cardiff Brighton Bristol Chester Windsor Amsterdam Rotterdam Utrecht Haga Leiden Delft Haarlem Bruksela Brugia Gandawa Antwerpia Luksemburg Berlin Monachium Hamburg Drezno Lipsk Kolonia Heidelberg Norymberga Freiburg Garmisch Berchtesgaden Konstancja Lindau Rothenburg Bamberg Weimar Praga Brno Karlowe Wary Krumlov Bratysława Budapeszt Balaton Eger Zagrzeb Split Dubrownik Zadar Rovinj Bled Lublana Piran Ryga Tallinn Wilno Kowno Kraków Zakopane Wisła Szczyrk Karpacz Sopot Gdańsk Toruń Kazimierz Sandomierz Zamość Bukowina Krynica Szklarska Zieleniec Białka Ateny Santorini Mykonos Kreta Rodos Korfu Saloniki Nafplio Meteora Kefalonia Zakynthos Paros Naxos Malta Gozo Valletta Cypr Nikozja Pafos Limassol Istambuł Kapadocja Antalya Bodrum Marmaris Tbilisi Batumi Erywań Baku Dolomity Tatry Alpy Pireneje Riwiera Toskania Prowansja Bretania Normandia Sabaudia Tyrol Bawaria Szwabia Karyntia Styria Dalmacja Istria Kornwalia Szkocja Walia Skandynawia Islandia Laponia Sycylia Sardynia Korsyka Kreta Cyklady Andaluzja Katalonia Kastylia Galicja Nawarra Baskonia Aragonia Algarve Alentejo Riviera Ligurii Umbria Piemont Lombardia Wenecja Liguria Kalabria Apulia Marche Molise Abruzja Lacjum Kampania Toskana Emilia Friuli Trydent Sopotnia Wetlina Ustrzyki Solina Bieszczady Sudety Beskidy Pieniny Gorce Podhale Mazury Kaszuby Roztocze Podlasie Warmia Kujawy Łódź Wrocław Poznań Lublin Olsztyn Białystok Rzeszów Kielce Opole Katowice Gliwice Bielsko Cieszyn Nowy Targ Rabka Limanowa Bochnia Wieliczka Niepołomice Tarnów Jasło Krosno Sanok Przemyśl Jarosław Łańcut Leżajsk Stalowa Mielec Dębica""".split()
seen=set(); CITIES=[c for c in CITIES if not (c in seen or seen.add(c))]

MATERIAL_FIX={'AZ-2202PC':['Lambslook'],'AZ-2527':['Akryl'],'AZ-2930PC':['Sztuczne futro'],'AZ-2931':['Sztuczne futro'],'AZ-2937':['Amicosoft'],'AZ-559':['Akryl'],'AZ-607PCV':['Akryl'],'AZ-910PC':['Vezuv']}
def clean_material(m):
    m=re.sub(r'\bROZ\.?\s*\S+|\bONE SIE\b|\bCOL\.\S+|\d+-\d+|[()]','',m).strip(' +')
    m=m.replace('TURBI','TURBO')
    parts=[p.strip() for p in re.split(r'[+/]|\s(?=[A-Z]{3,}\b)',m) if p.strip()]
    seen=[]; 
    for p in parts:
        p=p.title().replace('Lambslook','Lambslook').replace('90.10','90/10')
        if p not in seen: seen.append(p)
    return seen

rows=list(csv.DictReader(open(SRC,encoding='utf-8-sig'),delimiter=';'))
products=[]; used=set(); ci=0
for r in rows:
    code=r['kod'].strip()
    if not code or code in SKIP_CODES: continue
    mats=MATERIAL_FIX.get(code) or clean_material(r['material'])
    size=r['rozmiar'].strip() or 'One Size'
    flags=r['flagi'].split(); seg=r['segment'].strip()
    is_komin='KOMIN' in flags or re.match(r'\d+X\d+',size,re.I) or 'KOMIN' in r['plik'].upper()
    # nazwa
    while CITIES[ci] in used: ci+=1
    city=CITIES[ci]; used.add(city); ci+=1
    if is_komin:
        title=f"Komin Zimowy Damski {city}"; ptype='Komin'; base_tag='damskie'; kind='komin'
    else:
        segword={'Dziecięce':'Dziecięca','Chłopięce':'Chłopięca','Dziewczęce':'Dziewczęca'}.get(seg,'Damska')
        title=f"Czapka Zimowa {segword} Beanie {city}"; ptype='Czapka'
        base_tag='dzieci' if seg else 'damskie'; kind='czapka'
    suffix=[]
    if 'CEKIN' in flags: suffix.append('z Cekinami')
    if 'MULTI' in flags: suffix.append('Multikolor')
    if suffix: title+=' '+' '.join(suffix)
    mat_txt=' i '.join(mats) if mats else 'miękkiej dzianiny'
    if kind=='komin':
        intro=f"Komin zimowy {city} to uniwersalny dodatek z dzianiny {mat_txt}, który zastępuje szalik i chroni szyję przed wiatrem. Klasyczna forma sprawdza się w codziennych stylizacjach i dobrze uzupełnia ofertę czapek."
        feats=['Miękka, elastyczna dzianina','Nie uciska i nie krępuje ruchów','Uniwersalny rozmiar','Idealny na sezon jesień–zima']
    else:
        who={'Dziecięca':'dla dzieci','Chłopięca':'dla chłopców','Dziewczęca':'dla dziewczynek'}.get(segword,'damska')
        intro=f"Czapka zimowa {city} to model {who} z dzianiny {mat_txt}, łączący klasyczny fason z wygodą noszenia. Dobrze trzyma kształt, jest ciepła i lekka, a jej ponadczasowy wygląd sprawia, że łatwo komponuje się z zimowymi stylizacjami."
        feats=['Miękka i komfortowa dzianina','Elastyczny fason dopasowujący się do głowy','Uniwersalny rozmiar' if size=='One Size' else f'Rozmiar {size}','Idealna na sezon jesień–zima']
        if 'CEKIN' in flags: feats.insert(1,'Zdobienie cekinami')
        if 'MULTI' in flags: feats.insert(1,'Wielokolorowy wzór')
    body=f"<p>{intro}</p><p>Model {city} stanowi dobre uzupełnienie oferty sklepów odzieżowych, butików oraz punktów sprzedaży akcesoriów zimowych.</p><p><strong>Cechy produktu:</strong><br>"+"<br>".join('✔ '+f for f in feats)+"</p><p><strong>Specyfikacja:</strong></p><ul><li>Model: "+city+"</li><li>Kod: "+code+"</li><li>Materiał: "+(', '.join(mats) or 'do uzupełnienia')+"</li><li>Rozmiar: "+size+"</li><li>Sezon: jesień / zima</li></ul>"
    tags=[base_tag,'cena-do-uzupelnienia']
    if r['grupa_cenowa']: tags.append('grupa-'+r['grupa_cenowa'].lower())
    tags+=[re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',m).encode('ascii','ignore').decode().lower()).strip('-') for m in mats]
    if kind=='komin': tags.append('kominy')
    photo=os.path.join(PHOTOS,os.path.splitext(r['plik'])[0]+'.jpg')
    products.append(dict(code=code,title=title,body_html=body,product_type=ptype,vendor='Achti',tags=sorted(set(tags)),
        size=size,materials=mats,photo=photo if os.path.exists(photo) else None,price='0.00'))
json.dump(products,open(OUT_JSON,'w'),ensure_ascii=False,indent=1)
with open(OUT_CSV,'w',newline='',encoding='utf-8-sig') as fh:
    w=csv.writer(fh,delimiter=';'); w.writerow(['kod','nazwa robocza','typ','materiał','rozmiar','tagi','zdjęcie'])
    for p in products: w.writerow([p['code'],p['title'],p['product_type'],', '.join(p['materials']),p['size'],' '.join(p['tags']),'tak' if p['photo'] else 'BRAK'])
print(len(products),'produktów; bez zdjęcia:',sum(1 for p in products if not p['photo']))
print('->',OUT_JSON); print('->',OUT_CSV)
