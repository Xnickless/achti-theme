# Achti B2B — motyw Shopify (Trade + modyfikacje B2B)

Ten folder to repozytorium `Xnickless/achti-theme` dla sklepu Shopify `ccucsr-si.myshopify.com`.

**Wdrażanie (stan na 04.09.2026):** integracja GitHub → Shopify **nie działa** (sprawdzone: motyw live „Trade” #201190474070 to stockowy Trade z 8 lipca, żaden motyw nie dostaje pushy z `main`). Kod wdrażamy ręcznie do wersji roboczej:
```
shopify theme push --store ccucsr-si.myshopify.com --theme 206234878294 --allow-live   # „achti-trade-b2b-v4”, od 07.09.2026 LIVE (flaga --allow-live wymagana)
```
**07.09.2026: motyw #206234878294 opublikowany jako live** (stary Trade #201190474070 został jako wersja robocza). Push do tego samego ID aktualizuje teraz motyw live. Strona /pages/rejestracja ma przypisany szablon „rejestracja”. Jeśli klient edytuje motyw w „Dostosuj”, zmiany są w Shopify, nie w repo — przed pracą `shopify theme pull --theme 206234878294 --only "templates/*.json" --only "sections/*-group.json" --only config/settings_data.json` i porównaj.

## Kontekst projektu
- Klient: Adrian (marka Achti, polski producent czapek, kominów, kominiarek). Platforma hurtowa B2B: ceny tylko dla zaakceptowanych firm, rejestracja po NIP/VAT UE z ręczną akceptacją.
- Języki: PL (domyślny), EN, DE, FR. Termin startu: koniec września 2026.
- Baza: oficjalny motyw Shopify **Trade** (architektura Dawn). Nie przepisujemy motywu — dokładamy minimalne, punktowe zmiany.
- Decyzje klienta (dokument „PLATFORMA ACHTI B2B”, Google Docs, 07.09.2026):
  - **Dostępność:** cała oferta „Na zamówienie” bez stanów; wybrane modele oznaczane „Dostępny od ręki” (włączone śledzenie stanów + ilość > 0). Zrobione w bloku inventory main-product (stany: on_order / in_stock / unavailable, klucze `b2b.availability.*`, dopisek czasu realizacji w ustawieniach bloku).
  - **Kolory = warianty** z własnymi stanami; nazwy kolorów numerami lub zestawami (np. „120 - Czarny”, „SET 5”). Swatche z nazw nie zadziałają — docelowo zdjęcia wariantów jako miniatury.
  - **Rozmiary:** One Size; dzieci 50-52 i 52-54 (jako warianty rozmiaru w dziecięcych).
  - **Katalog PDF:** dynamiczny z cenami klienta tylko jeśli ceny per klient (Shopify: katalogi B2B per firma — możliwe); inaczej bez cen.
  - **Polityka cenowa:** kilka progów zależnych od ilości sztuk lub kwoty (Shopify B2B: progi ilościowe w katalogu; motyw Trade pokazuje „Ceny zależne od wolumenu”).
  - Nowe punkty z dokumentu: zdjęcia każdej czapki na modelce, waga brutto w CSV/produkcie, integracja z kurierem, Klaviyo, XML z ofertą (zrobiony: `/collections/all?view=feed`).

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
- `snippets/b2b-gate.liquid` — komunikat zamiast ceny (`style: 'inline'`) lub panel z przyciskami (`style: 'box'`). Koszyk (main-cart-items, main-cart-footer, cart-drawer) pokazuje gościom bramę zamiast pozycji i cen (07.09.2026). Filtr „Dostępność” ukryty w snippets/facets.liquid (cała oferta jest „na zamówienie”). Formularz kontaktowy ma pole „Nazwa firmy” (`templates.contact.form.company`).
- `docs/strony/` — projekty regulaminu B2B, polityki prywatności, cookies, wysyłki, zwrotów, FAQ i warunków współpracy + README z instrukcją wklejenia i decyzjami klienta (07.09.2026). Podgląd: https://claude.ai/code/artifact/dfddfe42-5561-49c0-9abb-642afa7c33ba
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
- Kolekcje automatyczne po tagach produktu: Damska = `damskie`, Męska = `meskie`, Dla dzieci = `dzieci`, Premium = `premium`, Nowości = `nowosc`, Wyprzedaż = cena porównawcza > 0, Najpopularniejsze (`najpopularniejsze`, cena > 0, sortowanie „najlepiej sprzedające się”). Ręczne (klient dodaje produkty): Bestsellery, Czapki reklamowe, Private Label. Kolekcje kategorii sortują od najnowszych (CREATED_DESC), tag `nowosc` ma 12 najnowszych SKU (AZ-3090…AZ-3102PC). Klient przy dodawaniu produktu wpisuje tagi — bez tagu produkt nie pojawi się w żadnej kategorii menu.
- Menu główne podpięte pod kolekcje. Stopka (wg projektu klienta z docx „PLATFORMA ACHTI B2B”): kolumny Kolekcje = `main-menu`, Informacje = menu `informacje` (O nas, Produkcja, Materiały, Jakość, Zrównoważony rozwój, Blog, Kontakt — strony `/pages/o-nas`, `/pages/produkcja`, `/pages/materialy`, `/pages/jakosc`, `/pages/zrownowazony-rozwoj` **jeszcze nie istnieją**), Obsługa klienta = menu `obsluga-klienta` (Logowanie B2B, Rejestracja firmy, Warunki współpracy `/pages/warunki-wspolpracy` (brak), Wysyłka i dostawa `/policies/shipping-policy`, Zwroty i reklamacje `/policies/refund-policy`, FAQ `/pages/faq` (brak)). Polityki (regulamin, wysyłka, zwroty) do uzupełnienia w Ustawienia → Polityki. Linki social (Instagram, Facebook, LinkedIn) do wpisania w Ustawienia motywu → Media społecznościowe.
- Popup newslettera na stronie głównej: sections/newsletter-popup.liquid (opóźnienie, localStorage na X dni, nie dla klientów z accepts_marketing; w edytorze otwiera się po zaznaczeniu sekcji).
- Feed XML produktów: `/collections/all?view=feed` (templates/collection.feed.liquid), ceny tylko gdy widoczne.
- W sklepie jest zainstalowana aplikacja „SP Hide Price & Access” — dubluje ukrywanie cen z motywu; do decyzji klienta, czy zostaje.

## Test jako firma B2B (07.09.2026)
Firma testowa „Firma Testowa Achti” (klient Kamil Test, e-mail Kamila) — zatwierdzona, bez katalogu. Ceny, szybkie zamawianie, koszyk i checkout z danymi firmy działają. Do decyzji/konfiguracji klienta:
- **Podatki:** Shopify dopisuje „Z wliczonymi podatkami”, a motyw mówi „Cena netto”. Dla hurtu netto wyłączyć Ustawienia → Podatki i cła → „Uwzględnij podatek w cenach” i ustawić VAT 23% PL. Wtedy dopisek zniknie sam.
- **Płatności:** w checkout tylko PayPal. B2B potrzebuje przelewu/faktury: Ustawienia → Płatności → Ręczne metody płatności („Przelew bankowy”) i/lub warunki płatności per firma (Klienci → Firmy → Warunki płatności).
- **Katalog B2B:** Markets → Katalogi → katalog z cenami hurtowymi przypisany do firm; bez niego firmy widzą ceny domyślne.
- **Panel konta klienta** (po zalogowaniu) to hostowana strona Shopify: wygląd w Ustawienia → Konta klientów → Personalizacja; menu w Treść → Menu → „Menu główne konta klienta”.
- Sekcje z pustą kolekcją (Nowości, Bestsellery, cross-sell w koszyku) są ukryte w sklepie do czasu dodania produktów (widoczne tylko w edytorze). Zachęta do rejestracji i drugi przycisk hero są ukryte dla zalogowanych firm (ustawienia `hide_for_b2b` / `button_2_hide_b2b`).

## Katalog produktów (import 07.09.2026)
- 362 produkty zaimportowane skryptem `tools/shopify_import.py` (Admin API, poświadczenia aplikacji „Import Katalogu” z Dev Dashboard w `~/.config/achti/client_id` + `client_secret`, poza repo). Dane: `tools/achti-produkty.json` wygenerowane przez `tools/generate_catalog.py` z arkusza `~/Downloads/achti-katalog-do-uzupelnienia.csv` (z nazw zdjęć). Zdjęcia po obróbce (białe tło, 4:5): `~/Downloads/ACHTI COLLECTION 2026-2027 - biale tlo`.
- **Nazwy robocze** (miasta, np. „Czapka Zimowa Damska Beanie Milano”), **ceny przykładowe** wg tagu grupy: G3=39, G5=49, G7=59, G10=69, G12=79 zł (`tools/set_prices.py`), tag `cena-do-uzupelnienia` na wszystkich. Kolory wariantów puste — klient uzupełnia.
- Skrypt importu pomija istniejące SKU, można uruchamiać ponownie; `--publish-only` publikuje nieopublikowane w Sklepie online.

## Inne kolory modelu (kółka na karcie produktu, 07.09.2026)
- Metapole `custom.inne_kolory` (list.product_reference, dostęp storefront PUBLIC_READ) = produkty tego samego modelu w innych kolorach. Blok `model_colors` w main-product renderuje bieżący + powiązane jako okrągłe miniatury (CSS `.model-colors` w b2b.css). Tabela szybkiego zamawiania (snippets/quick-order-list.liquid) pokazuje wiersze wszystkich produktów grupy z sumą dla grupy (przy produktach z wariantami dodaje wiersz nagłówkowy z nazwą). Kliknięcie w kółko podmienia produkt bez przeładowania (assets/model-colors.js: Section Rendering API dla sekcji `__main` i `__quick-order-list`, history.pushState; wstecz = reload). Klient edytuje listę w panelu przy produkcie. Demo: Milano ↔ Warmia ↔ Kujawy. Grupowanie zrobione 07.09.2026: CLIP ViT-B/32 (obrazy w skali szarości) + klasteryzacja aglomeracyjna (cosinus, próg 0.06) → 59 grup, 147 produktów; zapisane skryptem `tools/set_model_groups.py` z `tools/model-groups.json`. Podgląd dla klienta: `~/Downloads/achti-grupy-modeli.html` (+CSV). Poprawki: w panelu przy produkcie albo edycja JSON i ponowne uruchomienie skryptu (`--clear` czyści).

## Audyt 07.09.2026 — otwarte rekomendacje
- Strona główna: Nowości = kolekcja `nowosci`, Bestsellery = `najpopularniejsze` (automatyczna, wg sprzedaży). Karta produktu na dole: „Inni klienci też kupili” (related-products) + „Najbardziej popularne” (featured-collection `najpopularniejsze`). Animacja reveal-on-scroll wyłączona (`animations_reveal_on_scroll: false`) — wyglądała jak migotanie przy ładowaniu siatki.
- 9 linków ze stopki prowadzi do nieistniejących stron/polityk (O nas, Produkcja, Materiały, Jakość, Zrównoważony rozwój, Warunki współpracy, FAQ, Wysyłka, Zwroty) — treści klienta.
- Zdjęcia 1024 px w źródle: na karcie produktu (kolumna ~430 px) OK, w lightboxie miękkie; przy nowych zdjęciach z aparatu przepuścić przez `tools`/obróbkę tła.
- Animacja „reveal on scroll” (ustawienie motywu) opóźnia pokazanie sekcji przy szybkim przewijaniu — rozważyć wyłączenie.
- Certyfikaty (multicolumn) bez tekstów alt — uzupełnić alt w Treść → Pliki.

## Do zrobienia (stan na 04.09.2026)
1. Weryfikacja w sklepie: nagłówek, karta produktu i katalog jako gość / jako firma B2B.
2. Konfiguracja panelu (klient/Kamil): metapola produktu, kolekcje Nowości/Bestsellery, filtry w Search & Discovery, konta firm i katalogi B2B, języki + Translate & Adapt, Klaviyo.
3. Aplikacje: ulubione, powiadomienie o dostępności, katalog PDF z cenami po zalogowaniu.
4. Faza 2: Baselinker, feed XML, cross-sell w koszyku, szablon potwierdzenia zamówienia.
