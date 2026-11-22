#!/usr/bin/env python3
"""Strona /pages/black-week (Black Week 23–27.11.2026) w 4 językach — wersja procentowa od liczby sztuk (22.11.2026, Adrian).
Wynik: tools/translations/pages-src/black-week.html (PL) + pages/<en|de|fr>/black-week.html; potem pageUpdate PL + set_page_translations.py."""
import os
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translations')
TIERS = [(100, 4), (200, 7), (350, 10), (500, 15)]
ORG = {'pl': 'ACHTI Sp. z o.o. Sp.k., Bieńkowice 152, 32-410 Dobczyce, NIP PL6812081859',
       'en': 'ACHTI Sp. z o.o. Sp.k., Bieńkowice 152, 32-410 Dobczyce, Poland, VAT PL6812081859',
       'de': 'ACHTI Sp. z o.o. Sp.k., Bieńkowice 152, 32-410 Dobczyce, Polen, USt-IdNr. PL6812081859',
       'fr': 'ACHTI Sp. z o.o. Sp.k., Bieńkowice 152, 32-410 Dobczyce, Pologne, TVA PL6812081859'}
T = {
 'pl': dict(pre='', lead='Do −15% na całe zamówienie!', when='Tylko 23–27 listopada 2026 r.', sub='Zamawiasz więcej sztuk? Dostajesz większy rabat!',
   th=('Liczba sztuk w zamówieniu', 'Rabat na całe zamówienie'), row=lambda n, nxt: f'od {n} szt.' if nxt is None else f'{n}–{nxt - 1} szt.', pct=lambda p: f'−{p}%',
   howh='Jak odebrać rabat?', how=['Zaloguj się na platformie ACHTI B2B.', 'Wybierz produkty i dodaj je do koszyka.', 'Osiągnij odpowiedni próg liczby sztuk — koszyk pokazuje, ile sztuk brakuje do kolejnego rabatu.', 'Rabat nalicza się automatycznie w koszyku i przy kasie, bez wpisywania kodu.', 'Złóż zamówienie najpóźniej 27 listopada o godz. 23:59.'],
   cta='Zamów teraz', note='Promocja dotyczy zamówień B2B. Rabaty nie łączą się z innymi promocjami. Maksymalny rabat wynosi 15% wartości netto produktów.',
   regh='Regulamin promocji „Black Week ACHTI B2B 2026”',
   reg=['Organizatorem promocji jest {org}.', 'Promocja obowiązuje od 23 listopada 2026 r. od godz. 00:00 do 27 listopada 2026 r. do godz. 23:59 czasu polskiego.', 'Promocja jest dostępna wyłącznie dla zarejestrowanych i zaakceptowanych klientów biznesowych platformy b2b.achti.com.',
        'Wysokość rabatu zależy od łącznej liczby sztuk produktów w zamówieniu. Rabat jest procentem od wartości netto produktów, z wyłączeniem kosztów dostawy i opłat dodatkowych.',
        'Progi rabatowe wynoszą: od 100 do 199 szt. — 4%; od 200 do 349 szt. — 7%; od 350 do 499 szt. — 10%; od 500 szt. — 15%.',
        'Na jedno zamówienie może zostać naliczony wyłącznie jeden rabat Black Week, zgodny z osiągniętym progiem. Rabat nalicza się automatycznie.',
        'Rabaty nie sumują się i nie łączą z innymi kodami rabatowymi, rabatami automatycznymi (w tym rabatami ilościowymi), promocjami specjalnymi ani indywidualnymi ofertami cenowymi. Jeżeli zamówienie kwalifikuje się do kilku rabatów, naliczany jest rabat korzystniejszy dla klienta.',
        'Maksymalny rabat Black Week wynosi 15% wartości netto produktów w zamówieniu.', 'Promocja obejmuje wyłącznie nowe zamówienia złożone na platformie w czasie jej trwania. Nie działa wstecz.',
        'Rabat nie podlega wypłacie w gotówce, wymianie ani przeniesieniu na kolejne zamówienie.', 'Próg darmowej dostawy liczony jest od wartości zamówienia po rabacie.',
        'W przypadku anulowania części zamówienia lub zmiany liczby sztuk poniżej progu uprawniającego do rabatu ACHTI może odpowiednio przeliczyć rabat zgodnie z ostatecznym zamówieniem.',
        'Promocja nie oznacza przyspieszonego terminu produkcji ani dostawy. Terminy realizacji ustalane są według standardowych zasad ACHTI.', 'W sprawach nieuregulowanych zastosowanie mają warunki sprzedaży ACHTI (Regulamin B2B) oraz obowiązujące przepisy prawa.']),
 'en': dict(pre='/en', lead='Up to 15% off your whole order!', when='23–27 November 2026 only.', sub='Order more pieces — get a bigger discount!',
   th=('Pieces in your order', 'Discount on the whole order'), row=lambda n, nxt: f'from {n} pcs' if nxt is None else f'{n}–{nxt - 1} pcs', pct=lambda p: f'{p}% off',
   howh='How to get the discount', how=['Log in to the ACHTI B2B platform.', 'Choose your products and add them to the cart.', 'Reach the quantity threshold — the cart shows how many pieces are missing to the next discount.', 'The discount is applied automatically in the cart and at checkout, no code needed.', 'Place your order by 27 November, 23:59 (Polish time).'],
   cta='Order now', note='The promotion applies to B2B orders. Discounts cannot be combined with other promotions. The maximum discount is 15% of the net product value.',
   regh='Terms of the “Black Week ACHTI B2B 2026” promotion',
   reg=['The promotion is organised by {org}.', 'The promotion runs from 23 November 2026, 00:00, until 27 November 2026, 23:59 Polish time (CET).', 'The promotion is available only to registered and approved business customers of b2b.achti.com.',
        'The discount depends on the total number of product pieces in the order. It is a percentage of the net product value, excluding shipping and additional fees.',
        'Discount thresholds: 100–199 pcs — 4%; 200–349 pcs — 7%; 350–499 pcs — 10%; from 500 pcs — 15%.',
        'Only one Black Week discount, matching the threshold reached, can be applied per order. The discount is applied automatically.',
        'Discounts do not add up and cannot be combined with other discount codes, automatic discounts (including volume discounts), special promotions or individual price offers. If an order qualifies for several discounts, the one more favourable to the customer is applied.',
        'The maximum Black Week discount is 15% of the net product value of the order.', 'The promotion covers only new orders placed on the platform during the promotion period. It does not apply retroactively.',
        'The discount cannot be paid out in cash, exchanged or transferred to a future order.', 'The free shipping threshold is calculated on the order value after discount.',
        'If part of an order is cancelled or the number of pieces falls below the qualifying threshold, ACHTI may recalculate the discount based on the final order.',
        'The promotion does not mean faster production or delivery. Lead times follow ACHTI’s standard terms.', 'Matters not covered here are governed by ACHTI’s terms of sale (B2B Terms) and applicable law.']),
 'de': dict(pre='/de', lead='Bis zu 15 % Rabatt auf die gesamte Bestellung!', when='Nur vom 23. bis 27. November 2026.', sub='Mehr Stück bestellen — mehr Rabatt erhalten!',
   th=('Stückzahl der Bestellung', 'Rabatt auf die gesamte Bestellung'), row=lambda n, nxt: f'ab {n} Stück' if nxt is None else f'{n}–{nxt - 1} Stück', pct=lambda p: f'{p} %',
   howh='So erhalten Sie den Rabatt', how=['Melden Sie sich auf der ACHTI-B2B-Plattform an.', 'Wählen Sie Produkte aus und legen Sie sie in den Warenkorb.', 'Erreichen Sie die gewünschte Stückzahl — der Warenkorb zeigt, wie viele Stück bis zum nächsten Rabatt fehlen.', 'Der Rabatt wird automatisch im Warenkorb und an der Kasse abgezogen, ohne Code.', 'Bestellen Sie bis spätestens 27. November, 23:59 Uhr (polnische Zeit).'],
   cta='Jetzt bestellen', note='Die Aktion gilt für B2B-Bestellungen. Rabatte sind nicht mit anderen Aktionen kombinierbar. Der maximale Rabatt beträgt 15 % des Netto-Warenwerts.',
   regh='Teilnahmebedingungen der Aktion „Black Week ACHTI B2B 2026“',
   reg=['Veranstalter der Aktion ist {org}.', 'Die Aktion gilt vom 23. November 2026, 00:00 Uhr, bis zum 27. November 2026, 23:59 Uhr polnischer Zeit (MEZ).', 'Die Aktion steht ausschließlich registrierten und freigeschalteten Geschäftskunden von b2b.achti.com offen.',
        'Die Höhe des Rabatts hängt von der Gesamtstückzahl der Produkte in der Bestellung ab. Der Rabatt ist ein Prozentsatz des Netto-Warenwerts, ohne Versandkosten und Zusatzgebühren.',
        'Rabattstufen: 100–199 Stück — 4 %; 200–349 Stück — 7 %; 350–499 Stück — 10 %; ab 500 Stück — 15 %.',
        'Pro Bestellung kann nur ein Black-Week-Rabatt entsprechend der erreichten Stufe gewährt werden. Der Rabatt wird automatisch abgezogen.',
        'Rabatte sind nicht kumulierbar und nicht mit anderen Rabattcodes, automatischen Rabatten (einschließlich Mengenrabatten), Sonderaktionen oder individuellen Preisangeboten kombinierbar. Erfüllt eine Bestellung die Bedingungen mehrerer Rabatte, wird der für den Kunden günstigere gewährt.',
        'Der maximale Black-Week-Rabatt beträgt 15 % des Netto-Warenwerts der Bestellung.', 'Die Aktion gilt nur für neue Bestellungen, die während der Aktionszeit auf der Plattform aufgegeben werden. Sie gilt nicht rückwirkend.',
        'Der Rabatt kann nicht bar ausgezahlt, getauscht oder auf eine spätere Bestellung übertragen werden.', 'Die Schwelle für den kostenlosen Versand wird auf Basis des Bestellwerts nach Rabatt berechnet.',
        'Wird ein Teil der Bestellung storniert oder sinkt die Stückzahl unter die maßgebliche Stufe, kann ACHTI den Rabatt anhand der endgültigen Bestellung neu berechnen.',
        'Die Aktion bedeutet keine schnellere Produktion oder Lieferung. Es gelten die üblichen Lieferzeiten von ACHTI.', 'Im Übrigen gelten die Verkaufsbedingungen von ACHTI (B2B-AGB) und das geltende Recht.']),
 'fr': dict(pre='/fr', lead='Jusqu’à −15 % sur toute la commande !', when='Du 23 au 27 novembre 2026 uniquement.', sub='Plus de pièces commandées, plus de remise !',
   th=('Nombre de pièces commandées', 'Remise sur toute la commande'), row=lambda n, nxt: f'à partir de {n} pièces' if nxt is None else f'{n}–{nxt - 1} pièces', pct=lambda p: f'−{p} %',
   howh='Comment obtenir la remise ?', how=['Connectez-vous à la plateforme ACHTI B2B.', 'Choisissez vos produits et ajoutez-les au panier.', 'Atteignez le palier de quantité — le panier indique combien de pièces il manque pour la remise suivante.', 'La remise s’applique automatiquement dans le panier et au paiement, sans code.', 'Passez commande au plus tard le 27 novembre à 23h59 (heure polonaise).'],
   cta='Commander maintenant', note='L’offre concerne les commandes B2B. Les remises ne sont pas cumulables avec d’autres promotions. La remise maximale est de 15 % de la valeur HT des produits.',
   regh='Règlement de l’offre « Black Week ACHTI B2B 2026 »',
   reg=['L’organisateur de l’offre est {org}.', 'L’offre est valable du 23 novembre 2026 à 00h00 au 27 novembre 2026 à 23h59, heure polonaise (CET).', 'L’offre est réservée aux clients professionnels inscrits et validés de b2b.achti.com.',
        'Le montant de la remise dépend du nombre total de pièces commandées. La remise est un pourcentage de la valeur HT des produits, hors frais de livraison et frais supplémentaires.',
        'Paliers de remise : 100–199 pièces — 4 % ; 200–349 pièces — 7 % ; 350–499 pièces — 10 % ; à partir de 500 pièces — 15 %.',
        'Une seule remise Black Week, correspondant au palier atteint, peut être appliquée par commande. La remise s’applique automatiquement.',
        'Les remises ne se cumulent pas et ne sont pas combinables avec d’autres codes de réduction, remises automatiques (y compris les remises sur quantité), promotions spéciales ou offres de prix individuelles. Si une commande donne droit à plusieurs remises, la plus avantageuse pour le client est appliquée.',
        'La remise Black Week maximale est de 15 % de la valeur HT des produits de la commande.', 'L’offre concerne uniquement les nouvelles commandes passées sur la plateforme pendant sa durée. Elle n’est pas rétroactive.',
        'La remise ne peut être ni remboursée en espèces, ni échangée, ni reportée sur une commande ultérieure.', 'Le seuil de livraison gratuite est calculé sur le montant de la commande après remise.',
        'En cas d’annulation partielle de la commande ou de baisse du nombre de pièces sous le palier, ACHTI peut recalculer la remise en fonction de la commande finale.',
        'L’offre n’implique pas de délai de production ou de livraison plus court. Les délais habituels d’ACHTI s’appliquent.', 'Pour tout point non prévu, les conditions de vente d’ACHTI (conditions B2B) et la loi applicable s’appliquent.']),
}
for loc, t in T.items():
    rows = []
    for i, (n, p) in enumerate(TIERS):
        nxt = TIERS[i + 1][0] if i + 1 < len(TIERS) else None
        rows.append(f'<tr>\n<td>{t["row"](n, nxt)}</td>\n<td><strong>{t["pct"](p)}</strong></td>\n</tr>')
    how = '\n'.join(f'<li>{x}</li>' for x in t['how'])
    reg = '\n'.join(f'<li>{x.replace("{org}", ORG[loc])}</li>' for x in t['reg'])
    html = f'''<h2>{t["lead"]}</h2>
<p><strong>{t["when"]}</strong> {t["sub"]}</p>
<table class="b2b-table">
<thead><tr>
<th>{t["th"][0]}</th>
<th>{t["th"][1]}</th>
</tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody>
</table>
<h3>{t["howh"]}</h3>
<ol>
{how}
</ol>
<p><a class="button" href="{t["pre"]}/collections/all">{t["cta"]}</a></p>
<p><small>{t["note"]}</small></p>
<h3>{t["regh"]}</h3>
<ol>
{reg}
</ol>'''
    out = os.path.join(HERE, 'pages-src', 'black-week.html') if loc == 'pl' else os.path.join(HERE, 'pages', loc, 'black-week.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(out)
