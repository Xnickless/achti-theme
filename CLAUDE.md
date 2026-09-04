# Achti B2B — motyw Shopify (Trade + modyfikacje B2B)

Ten folder to repozytorium `Xnickless/achti-theme` dla sklepu Shopify `ccucsr-si.myshopify.com`.

**Wdrażanie (stan na 04.09.2026):** integracja GitHub → Shopify **nie działa** (sprawdzone: motyw live „Trade” #201190474070 to stockowy Trade z 8 lipca, żaden motyw nie dostaje pushy z `main`). Kod wdrażamy ręcznie do wersji roboczej:
```
shopify theme push --store ccucsr-si.myshopify.com --theme 206234878294   # „achti-trade-b2b-v4”, niepublikowany
```
Motyw live zmienia się dopiero po publikacji tej wersji roboczej w panelu (Sklep online → Motywy → Publikuj). Do czasu publikacji strona rejestracji nie ma przypisanego szablonu „rejestracja” (szablon jest tylko w wersji roboczej). Jeśli klient edytuje motyw w „Dostosuj”, zmiany są w Shopify, nie w repo — przed pracą `shopify theme pull --theme 206234878294 --only "templates/*.json" --only "sections/*-group.json" --only config/settings_data.json` i porównaj.

## Kontekst projektu
- Klient: Adrian (marka Achti, polski producent czapek, kominów, kominiarek). Platforma hurtowa B2B: ceny tylko dla zaakceptowanych firm, rejestracja po NIP/VAT UE z ręczną akceptacją.
- Języki: PL (domyślny), EN, DE, FR. Termin startu: koniec września 2026.
- Baza: oficjalny motyw Shopify **Trade** (architektura Dawn). Nie przepisujemy motywu — dokładamy minimalne, punktowe zmiany.
- Odłożone decyzje klienta: sposób pokazywania dostępności, kolory jako warianty, rozmiary jako warianty, polityka cenowa per klient.

## Co już jest dodane (nie duplikuj)
- Ukrywanie cen/zakupu dla gości: ustawienia `settings.b2b_hide_prices`, `settings.b2b_require_company`, `settings.b2b_register_page` (config/settings_schema.json, grupa „B2B — dostęp do cen”).
- Wzorzec dostępu (wklejany na początku plików, które go potrzebują):
  ```liquid
  {%- liquid
    assign b2b_access = true
    if settings.b2b_hide_prices
      if customer == nil
        assign b2b_access = false
      elsif settings.b2b_require_company and customer.b2b? != true
        assign b2b_access = false
      endif
    endif
  -%}
  ```
  Użyty w: snippets/price.liquid, snippets/buy-buttons.liquid, snippets/card-product.liquid, sections/main-product.liquid (bloki inventory, quantity_selector, text z „VAT”), sections/quick-order-list.liquid, sections/bulk-quick-order-list.liquid.
- `snippets/b2b-gate.liquid` — komunikat zamiast ceny (`style: 'inline'`) lub panel z przyciskami (`style: 'box'`).
- `sections/b2b-register.liquid` + `templates/page.rejestracja.json` — formularz rejestracji firmy (contact form, walidacja NIP w JS).
- `assets/b2b.css` — style B2B, przekreślone niedostępne swatche, „load more”. Style nagłówka są w `{% style %}` w sections/header.liquid.
- Nagłówek: `logo_position: top-left`, pole wyszukiwania inline (`section.settings.inline_search`), klasa `header--inline-search`.
- Listing: 4 kolumny, ciągłe doładowywanie (skrypt na końcu sections/main-collection-product-grid.liquid).
- Karta produktu (templates/product.json): title, sku, price, tekst „Cena netto — VAT naliczany w koszyku”, variant_picker (swatche), inventory, quantity, buy_buttons, description (blok ma ustawienia `collapsible`/`show_intro`/`heading`/`icon`: pierwszy akapit widoczny, reszta w rozwijanej sekcji „Opis i specyfikacja”), zakładki Rozmiar/Skład/Kolor z metapól `custom.rozmiar`, `custom.sklad`, `custom.kolory`.
- Tłumaczenia B2B: klucze `b2b.*` w locales/pl.json, en.default.json, de.json, fr.json.
- Stopka bez „Powered by Shopify”. Jedna czcionka (DM Sans) w config/settings_data.json.

## Zasady pracy
- Przed commitem: `shopify theme check` (0 błędów) **i** ręczna kontrola, że żaden `{% if %}` nie przecina granic `{% when %}` w `case` — theme check tego nie wykrywa, a Shopify odrzuca cały motyw.
- Podgląd na żywo: `shopify theme dev --store ccucsr-si.myshopify.com` (loguje przez przeglądarkę, nie publikuje).
- Nie zmieniaj plików JSON w `templates/` i `sections/*-group.json`, jeśli klient mógł je edytować w edytorze — najpierw `git pull` i sprawdź diff.
- Teksty widoczne dla klienta: po polsku; nowe stringi zawsze dodawaj do wszystkich czterech plików locales.
- Commity po polsku, krótko, np. `Nagłówek: pole wyszukiwania w jednej linii`.

## Skonfigurowane w panelu 04.09.2026
- Strona `rejestracja` (tytuł „Rejestracja firmy”), bez szablonu — przypisać „rejestracja” po publikacji motywu.
- Kolekcje automatyczne po tagach produktu: Damska = `damskie`, Męska = `meskie`, Dla dzieci = `dzieci`, Premium = `premium`, Nowości = `nowosc`, Wyprzedaż = cena porównawcza > 0. Ręczne (klient dodaje produkty): Bestsellery, Czapki reklamowe, Private Label. Klient przy dodawaniu produktu wpisuje tagi — bez tagu produkt nie pojawi się w żadnej kategorii menu.
- Menu główne podpięte pod kolekcje; menu stopki: Szukaj, Kontakt, Rejestracja firmy.
- Feed XML produktów: `/collections/all?view=feed` (templates/collection.feed.liquid), ceny tylko gdy widoczne.
- W sklepie jest zainstalowana aplikacja „SP Hide Price & Access” — dubluje ukrywanie cen z motywu; do decyzji klienta, czy zostaje.

## Do zrobienia (stan na 04.09.2026)
1. Weryfikacja w sklepie: nagłówek, karta produktu i katalog jako gość / jako firma B2B.
2. Konfiguracja panelu (klient/Kamil): metapola produktu, kolekcje Nowości/Bestsellery, filtry w Search & Discovery, konta firm i katalogi B2B, języki + Translate & Adapt, Klaviyo.
3. Aplikacje: ulubione, powiadomienie o dostępności, katalog PDF z cenami po zalogowaniu.
4. Faza 2: Baselinker, feed XML, cross-sell w koszyku, szablon potwierdzenia zamówienia.
