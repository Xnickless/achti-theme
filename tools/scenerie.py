"""Scenerie sesji zdjęciowych wg podziału Adriana (folder na Drive „SESJE SCENERIA WYBÓR NA MODELE”, 14.09.2026).
Każdy podfolder = grupa modeli, które mają być sfotografowane w tym samym klimacie.
Tu: mapowanie SKU -> sceneria + prompty dla generatora AI (gen_model_photos.py).
  python3 tools/scenerie.py            -> podsumowanie pokrycia
  python3 tools/scenerie.py --json     -> tools/scenerie.json (SKU -> sceneria)
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))

# --- podział Adriana: kody odczytane z nazw plików w podfolderach ---
GRUPY = {
 'meskie_miasto': """AZ-3072PK AZ-3070PK AZ-3071PK AZ-2551PK AZ-2549PK AZ-2548PK AZ-2555PK AZ-2608PK AZ-2539PK
    AZ-2554PK AZ-2541PK AZ-2538PK AZ-2543PK AZ-1575PK AZ-1430PC AZ-2553PK AZ-2636PK AZ-1609PK AZ-2612PK
    AZ-2542PK AZ-2544""",
 'sport_narty': "AZ-1531PK",
 'unisex': "AZ-3087D",
 'glamour': """AZ-2957D AZ-2663D AZ-2893PC AZ-2742D AZ-2956D AZ-2984D AZ-2981D AZ-2980D AZ-2665D AZ-3014D
    AZ-2932D AZ-2667D AZ-2955D AZ-3021PC AZ-910PC-BP AZ-2661D AZ-2773D AZ-2982PC""",
 'dzieci': """AZ-2718PC AZ-2719PC AZ-2843PC-BOY AZ-2720PC AZ-2202PC AZ-2887PCE AZ-2713PC AZ-2842PC-GIRL
    AZ-2349PC AZ-2712PC AZ-2888PCE AZ-2371PC AZ-2920PC AZ-2515PC AZ-2851PC AZ-2490PK AZ-2884PC AZ-2844PC
    AZ-2842PC-BOY AZ-2926PC AZ-2716PC AZ-1476PC AZ-2876PC AZ-2716PCE AZ-2712PCE AZ-2719PCE AZ-2849PC-BOY
    AZ-2364PC AZ-2921PC""",
 'skandynawski': "AZ-2651PC AZ-2681PC AZ-2650PC AZ-2680PC",
 'premium_miasto': """AZ-2937 AZ-2934 AZ-2938 AZ-3053PC AZ-3054 AZ-3056PC AZ-2928 AZ-3055PC AZ-2936 AZ-2935""",
 'naoko': """AZ-3100PC AZ-3099PC AZ-3097PC AZ-3095 AZ-3096PC AZ-3098PC AZ-3092PC AZ-3102PC AZ-3094PC AZ-3101PC
    AZ-3091PC AZ-3086PC AZ-3085PC AZ-3081PC AZ-3084PC AZ-3083PC AZ-3080PC AZ-3079PC AZ-3073PC AZ-3075PC
    AZ-3074PC AZ-3067PC AZ-3064PC AZ-3065PC AZ-3062PC AZ-3063PC AZ-3066PC AZ-3023PC AZ-2907PC AZ-2947PC
    AZ-3020PC AZ-2033PC-TURBO AZ-2911PC AZ-2965PK AZ-2897PC AZ-2942 AZ-2088PC AZ-2218PC AZ-2963PC AZ-2964PC
    AZ-2813D AZ-2973 AZ-2805 AZ-2917PC AZ-1356PC AZ-2943PC AZ-2925PC AZ-2827PC AZ-2812PC AZ-2915PC AZ-3019PC
    AZ-2808PC AZ-2688PC AZ-2902PC AZ-2940 AZ-2685PC AZ-2829PC AZ-2837PC AZ-2670PC AZ-2922PC""",
 'old_money': """AZ-3069PC AZ-3082PC AZ-3060PC AZ-3057PC AZ-3059PC AZ-3061PC AZ-2951PC AZ-3040PC AZ-2865PC
    AZ-2653PC AZ-2567PC AZ-2991PC AZ-3028PC AZ-2834PC AZ-1918PC AZ-2466PC AZ-2734PC AZ-2441PC AZ-3010PC
    AZ-1719PC AZ-1145PC AZ-3051PC AZ-1378PC AZ-2875PC AZ-3035PC AZ-2872PK AZ-2194PC AZ-3018 AZ-2656PC
    AZ-2752PC AZ-2983PC AZ-2561PC AZ-2995PC AZ-2953 AZ-2992PC AZ-3012PC AZ-2990PC AZ-1874PC AZ-3015PC
    AZ-3013PC AZ-3025PC AZ-2566PC AZ-2939 AZ-2999PC AZ-2697PC AZ-2703PC AZ-2797PC AZ-2613 AZ-3002PC
    AZ-2993PC AZ-3038PC AZ-3027 AZ-2743PC AZ-3007PC AZ-2996PC AZ-2747PC AZ-2737PC AZ-1708PC AZ-2873PK
    AZ-2788PC AZ-2676PC AZ-2866PC AZ-3005PC AZ-3030PC AZ-3036PC AZ-2735PC AZ-2989PC AZ-3003PC AZ-2033PC
    AZ-2440PC AZ-2501PC AZ-2588PC AZ-3011PC AZ-2658PC AZ-2874PC AZ-1909 AZ-2560PC AZ-2819PC AZ-2906PC
    AZ-1800PC AZ-2949PC AZ-2723PC AZ-2739PC AZ-2998PC AZ-3008PC AZ-3031 AZ-2701PC AZ-2784PC AZ-2954PC
    AZ-2905PC AZ-2504PC AZ-2704PC AZ-3000PC AZ-2782PC AZ-3001PC AZ-3029PC AZ-3016PC AZ-3039PC AZ-2820PC
    AZ-2852PC""",
}

# --- prompty: format zgodny z OLD_MONEY w gen_model_photos.py (scena/poza/stylizacja/swiatlo, po angielsku) ---
# OBSADA: która twarz z castingu pasuje do scenerii (pliki ~/Claude/achti-foto/modelki/casting/<osoba>_*.png), osobno dla kobiet i mężczyzn;
#   płeć wynika z segmentu produktu (Damska → kobieta, Męska → mężczyzna, Unisex → kobieta, chyba że sceneria ma unisex='mezczyzna').
#   Dobór 25.09.2026 (Kamil): każda sceneria ma inną twarz, bez osób 50+ (sceneria „glamour” zamiast „glamour_50”).
#   Lista twarzy = rotacja w obrębie scenerii. k2-blond odrzucona przez Kamila (Naoko → b6-mixed / b3-latina z castingu „beauty”).
SCENERIE = {
 'meskie_miasto': dict(nazwa='Męskie: klasyka, miasto, jesień/zima', obsada=dict(mezczyzna=['m1', 'bm1-afro', 'bm3-euro'], kobieta='k5-braz'), sceny={
   'stare_miasto': dict(
     scena='on a cobbled old-town street at dawn, tenement facades and wet cobbles softly blurred behind',
     poza='standing three-quarter to the camera, hands in coat pockets, calm confident expression, upper body in frame',
     stylizacja='a navy wool overcoat over a charcoal roll-neck, dark jeans, no logos',
     swiatlo='cool blue morning light, muted urban palette, gentle contrast'),
   'nabrzeze': dict(
     scena='on a city river embankment in winter, concrete balustrade and mist over the water blurred behind',
     poza='leaning against the balustrade, one shoulder to the camera, head turned to the lens, upper body in frame',
     stylizacja='a graphite wool coat over a cream fisherman sweater, leather gloves, no logos',
     swiatlo='flat overcast winter light, desaturated cool grading'),
   'brama': dict(
     scena='in the doorway of an old tenement house, dark joinery and fallen leaves on the pavement blurred behind',
     poza='standing straight, one hand adjusting the hat, looking into the lens, upper body and hands in frame',
     stylizacja='a black wool coat over a grey merino sweater, dark scarf, no logos',
     swiatlo='soft directional daylight from the side, warm-neutral grading'),
   'park_listopad': dict(
     scena='on a chestnut-tree avenue in a city park in November, bare branches and benches blurred behind',
     poza='mid-step towards the camera, head turned slightly to the lens, relaxed expression, upper body in frame',
     stylizacja='a camel wool coat over a navy roll-neck, no logos',
     swiatlo='soft overcast light, muted autumn palette'),
 }),
 'sport_narty': dict(nazwa='Sport i narty', obsada=dict(mezczyzna='m3', kobieta='k6-braz', unisex='mezczyzna'), sceny={
   'stok': dict(
     scena='on a sunlit ski slope, snow-covered spruces and a chairlift softly blurred behind',
     poza='standing three-quarter to the camera, goggles pushed up on the forehead, energetic natural smile, upper body in frame',
     stylizacja='a technical ski jacket in a muted colour, gloves in hand, no logos',
     swiatlo='bright alpine sunlight, crisp clean whites, high clarity'),
   'schronisko': dict(
     scena='on the terrace of a mountain lodge, snow on the wooden balustrade and peaks blurred behind',
     poza='leaning on the railing with a mug in both hands, looking into the lens, upper body in frame',
     stylizacja='a padded jacket over a fleece, no logos',
     swiatlo='warm low winter sun, soft shadows on snow'),
   'szczyt': dict(
     scena='on a mountain summit with a panorama of snow-covered ranges behind, wind in the air',
     poza='standing with the body slightly turned, chin up, confident calm expression, upper body in frame',
     stylizacja='a shell jacket in a muted colour, no logos',
     swiatlo='clear high-altitude light, deep blue sky, strong but natural contrast'),
 }),
 'unisex': dict(nazwa='Unisex, miejski minimalizm', obsada=dict(kobieta='k6-braz', mezczyzna='m3'), sceny={
   'beton': dict(
     scena='against a plain concrete wall in the city, nothing else in the frame',
     poza='standing straight facing the camera, neutral calm expression, upper body in frame',
     stylizacja='a simple ecru shell jacket, no patterns, no logos',
     swiatlo='soft diffused daylight, neutral grading, minimal shadows'),
   'przystanek': dict(
     scena='at a tram stop in winter, glass shelter and blurred city traffic behind',
     poza='standing sideways, head turned to the lens, hands in pockets, upper body in frame',
     stylizacja='a black technical coat over a grey sweatshirt, no logos',
     swiatlo='cool overcast light, urban desaturated palette'),
   'ulica_zmierzch': dict(
     scena='on an empty street at dusk, street lamps and shop lights softly blurred behind',
     poza='walking towards the camera, head slightly turned, calm expression, upper body in frame',
     stylizacja='a stone-coloured padded jacket, no logos',
     swiatlo='blue hour with warm lamp accents, cinematic but natural'),
 }),
 'glamour': dict(nazwa='Glamour: elegancja, park i góry', obsada=dict(kobieta=['k1-blond', 'b2-afro'], mezczyzna='m2'), sceny={
   'park_aleja': dict(
     scena='on a park avenue in golden autumn, tall trees and fallen leaves softly blurred behind',
     poza='standing three-quarter to the camera, one gloved hand lightly touching the coat collar, chin slightly raised, confident subtle smile, upper body in frame',
     stylizacja='a cream wool coat with a voluminous faux-fur collar, sleek glossy hair, soft red lipstick, small gold hoop earrings, black leather gloves, no logos',
     swiatlo='warm golden late-afternoon light, glossy refined grading, soft glow on the skin'),
   'gory_taras': dict(
     scena='on the terrace of a luxury mountain hotel, snow-covered peaks and a pale blue sky softly blurred behind',
     poza='leaning on a wooden balustrade, body turned to the view, head turned to the lens, radiant confident smile, upper body in frame',
     stylizacja='a white quilted down coat with a faux-fur trim, tinted aviator sunglasses held in one hand, polished nails, gold jewellery, no logos',
     swiatlo='bright alpine sunlight, crisp whites, luminous high-end grading'),
   'kawiarnia_park': dict(
     scena='at an elegant cafe terrace in a park, marble table and blurred greenery behind',
     poza='seated at a small table, a cup in one hand, body angled, looking into the lens with a composed glamorous expression, upper body in frame',
     stylizacja='a black wool coat over a black roll-neck, red lipstick, pearl earrings, no logos',
     swiatlo='soft diffused afternoon light, rich contrast, cinematic tone'),
   'jezioro': dict(
     scena='on a wooden jetty on a mountain lake, mist over the water and dark pines softly blurred behind',
     poza='standing three-quarter to the camera, hands in the pockets of a belted coat, serene confident expression, upper body in frame',
     stylizacja='a camel belted wrap coat, a silk scarf in warm tones, fine gold jewellery, no logos',
     swiatlo='pale morning light with a soft glow, muted luxurious palette'),
 }),
 'dzieci': dict(nazwa='Dzieci: park zabaw, las, góry', obsada=dict(dziewczynka='d1', chlopiec='c1'), sceny={
   'plac_zabaw': dict(
     scena='at a playground in winter, a wooden slide and snow-dusted railings softly blurred behind',
     poza='standing and looking straight into the camera with a bright natural smile, upper body in frame',
     stylizacja='a colourful padded jacket, a chunky scarf and mittens, age-appropriate, no adult styling, no logos',
     swiatlo='bright soft winter daylight, cheerful clean palette'),
   'las': dict(
     scena='on a forest path, snow on the branches and sunbeams between the trees blurred behind',
     poza='mid-step towards the camera, head slightly tilted, curious happy expression, upper body in frame',
     stylizacja='a red or mustard padded jacket, a soft scarf, age-appropriate, no logos',
     swiatlo='warm low sun through the trees, gentle contrast'),
   'miasto_spacer': dict(
     scena='on a city walk, colourful townhouses softly blurred behind',
     poza='standing with hands in pockets, smiling at the camera, upper body in frame',
     stylizacja='a navy or teal padded jacket, knitted scarf, age-appropriate, no logos',
     swiatlo='soft overcast daylight, clean bright grading'),
   'gory_dzieci': dict(
     scena='on a gentle mountain slope with snow, distant peaks softly blurred behind',
     poza='standing turned slightly, laughing at the camera, upper body in frame',
     stylizacja='a colourful ski jacket, mittens, age-appropriate, no logos',
     swiatlo='bright mountain sunlight, crisp whites'),
 }),
 'skandynawski': dict(nazwa='Styl skandynawski', obsada=dict(kobieta=['k3-blond', 'b4-nordic'], mezczyzna='m1'), sceny={
   'wnetrze_jasne': dict(
     scena='in a bright minimal interior with a large window, a white wall and pale wooden floor behind',
     poza='standing near the window, three-quarter to the camera, quiet composed expression, upper body in frame',
     stylizacja='a chunky ivory wool sweater, simple lines, no jewellery, no logos',
     swiatlo='soft cool window light, pale airy grading, low contrast'),
   'brzozy': dict(
     scena='in a birch grove covered in snow, thin white trunks blurred behind',
     poza='standing straight, hands in sweater sleeves, calm expression, looking into the lens, upper body in frame',
     stylizacja='a grey marl wool sweater, a plain scarf, no logos',
     swiatlo='cold blue-grey daylight, desaturated Nordic palette'),
   'pomost': dict(
     scena='on a wooden jetty over a frozen lake, pale sky and distant shoreline blurred behind',
     poza='standing sideways, head turned to the camera, serene expression, upper body in frame',
     stylizacja='a cream padded vest over a fine knit, no logos',
     swiatlo='flat pale winter light, minimal shadows'),
   'weranda': dict(
     scena='on the veranda of a white wooden house, simple railing and grey sky behind',
     poza='leaning lightly on the railing, looking into the lens, upper body in frame',
     stylizacja='an oatmeal wool coat over a white knit, no logos',
     swiatlo='soft overcast light, muted cool grading'),
 }),
 'premium_miasto': dict(nazwa='Premium merino, miasto (Varlesca / Chicaca)', obsada=dict(kobieta=['k5-braz', 'b1-korea'], mezczyzna=['m4', 'bm2-azja']), sceny={
   'witryna': dict(
     scena='beside a boutique window in the city centre, reflections in the glass and evening lights blurred behind',
     poza='standing three-quarter to the camera, chin level, composed confident expression, upper body in frame',
     stylizacja='an ivory cashmere coat over a fine merino roll-neck, a silk scarf, minimal gold jewellery, no logos',
     swiatlo='warm evening city light with soft bokeh, refined grading'),
   'schody': dict(
     scena='on the stone steps of an elegant tenement, a carved balustrade softly blurred behind',
     poza='standing on the steps, one hand on the balustrade, head turned to the lens, upper body in frame',
     stylizacja='a black cashmere coat over a cream merino sweater, leather gloves, no logos',
     swiatlo='soft directional daylight, elegant restrained palette'),
   'kawiarnia_premium': dict(
     scena='inside a premium cafe, a marble counter and warm lamps softly blurred behind',
     poza='seated at the counter, turned to the camera, hand resting near a cup, calm smile, upper body in frame',
     stylizacja='a camel merino coat over a silk blouse, delicate jewellery, no logos',
     swiatlo='warm interior light, shallow depth, cinematic natural tone'),
   'ulica_butiki': dict(
     scena='on a street of boutiques after dusk, shop lights forming soft bokeh behind',
     poza='walking towards the camera, head slightly turned, self-assured expression, upper body in frame',
     stylizacja='a charcoal cashmere coat over an ivory knit, a fine scarf, no logos',
     swiatlo='evening lights, warm highlights against cool shadows'),
 }),
 'naoko': dict(nazwa='Lifestyle w stylu sklepu Naoko', obsada=dict(kobieta=['b6-mixed', 'b3-latina', 'b1-korea'], mezczyzna='m1'), sceny={
   'studio_ecru': dict(
     scena='in a bright studio against a plain ecru backdrop, nothing else in the frame',
     poza='standing relaxed, slight natural smile, looking into the lens, upper body in frame',
     stylizacja='an oversized ecru knit sweater, soft and casual, no logos',
     swiatlo='soft large-source studio light, warm clean grading, minimal shadows'),
   'wnetrze_przytulne': dict(
     scena='in a cosy interior with a plant and wooden furniture, a large window softly blurred behind',
     poza='seated on a sofa arm, hands in the lap, warm natural smile, upper body in frame',
     stylizacja='a beige oversized cardigan over a white tee, casual, no logos',
     swiatlo='soft daylight from the window, warm homely palette'),
   'spacer_slonce': dict(
     scena='on a city walk on a sunny winter day, blurred street and bare trees behind',
     poza='walking towards the camera, laughing naturally, hair moving slightly, upper body in frame',
     stylizacja='a wide camel coat over a cream knit, casual and comfortable, no logos',
     swiatlo='low winter sun, warm golden highlights, natural contrast'),
   'kawiarnia_okno': dict(
     scena='in a cafe by a large window, blurred street outside',
     poza='seated at the table, cup in both hands, head tilted, relaxed smile, upper body in frame',
     stylizacja='a soft oatmeal sweater, simple and cosy, no logos',
     swiatlo='soft window light, warm inviting tone'),
 }),
 'old_money': dict(nazwa='Old money (klimat już wypracowany)', obsada=dict(kobieta=['k4-braz', 'b5-slavic', 'b4-nordic'], mezczyzna=['m2', 'bm3-euro']), sceny={}),  # sceny w OLD_MONEY w gen_model_photos.py
}

# modele, których Adrian nie zdążył przypisać — reguła po segmencie
DOMYSLNE = {'Męska': 'meskie_miasto', 'Dziewczęca': 'dzieci', 'Chłopięca': 'dzieci', 'Dziecięca': 'dzieci',
            'Unisex': 'unisex', 'Damska': 'old_money'}

def mapowanie(uzupelnij=True):
    """SKU -> sceneria. Z folderów Adriana, a brakujące (nie zdążył) z reguły po segmencie."""
    out = {}
    for g, kody in GRUPY.items():
        for k in kody.split():
            out.setdefault(k.upper(), g)
    if not uzupelnij: return out
    prods = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
    znane = {k: g for k, g in out.items()}
    for p in prods:
        kod = p['code'].upper()
        if kod in znane: continue
        # wariant kodu bez/z sufiksem PC też się liczy jako przypisany
        baza = re.sub(r'(PC|LPC|PK|D)$', '', kod)
        trafiony = next((g for k, g in znane.items() if re.sub(r'(PC|LPC|PK|D)$', '', k) == baza), None)
        if trafiony: out[kod] = trafiony; continue
        if 'premium' in (p.get('tags') or []): out[kod] = 'premium_miasto'
        elif p.get('product_type') == 'Opaska': out[kod] = 'naoko'
        else: out[kod] = DOMYSLNE.get(p.get('segment'), 'old_money')
    return out

if __name__ == '__main__':
    m = mapowanie()
    surowe = mapowanie(uzupelnij=False)
    prods = json.load(open(os.path.join(HERE, 'achti-produkty.json'), encoding='utf-8'))
    sklep = {p['code'].upper(): p for p in prods}
    def dopasuj(k):
        for kand in (k, k + 'PC', k + 'LPC', re.sub(r'PC$', '', k)):
            if kand in sklep: return kand
        return None
    przypisane, nieznane = {}, []
    for k, g in m.items():
        kk = dopasuj(k)
        if kk: przypisane[kk] = g
        else: nieznane.append(k)
    brak = [c for c in sklep if c not in przypisane]
    print('scenerii:', len(GRUPY), '| kodów u Adriana:', len(m), '| dopasowanych do sklepu:', len(przypisane))
    print(collections.Counter(przypisane.values()).most_common())
    if nieznane: print('kody spoza sklepu:', nieznane[:8], '…' if len(nieznane) > 8 else '')
    print('od Adriana:', len([k for k in przypisane if k in surowe or re.sub(r'(PC|LPC|PK|D)$','',k) in {re.sub(r'(PC|LPC|PK|D)$','',x) for x in surowe}]),
          '| uzupełnione regułą:', len(przypisane) - len([k for k in przypisane if k in surowe or re.sub(r'(PC|LPC|PK|D)$','',k) in {re.sub(r'(PC|LPC|PK|D)$','',x) for x in surowe}]))
    print('bez przypisanej scenerii:', len(brak), brak[:10], '…' if len(brak) > 10 else '')
    if '--json' in sys.argv:
        json.dump(przypisane, open(os.path.join(HERE, 'scenerie.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, sort_keys=True)
        print('zapisano tools/scenerie.json')
