# Strony prawne i obsługa klienta — instrukcja wdrożenia

Stan na 07.09.2026. **Teksty są już wgrane do Shopify** (4 polityki w Ustawienia → Polityki, strony `warunki-wspolpracy`, `faq`, `polityka-cookies`; w menu stopki „Obsługa klienta” dodano „Regulamin B2B” i „Polityka cookies”). Pola `[…]` zostały w treści jako pogrubione do uzupełnienia przez Adriana — edycja bezpośrednio w panelu. Ten folder to kopia źródłowa. Dane firmy pobrane z KRS i achti.pl: ACHTI Sp. z o.o. Sp.k., ul. Urocza 39, 32-040 Wrząsowice, KRS 0000862860, NIP 6812081859, REGON 386412597, korespondencja/zakład: Bieńkowice 152, 32-410 Dobczyce — do potwierdzenia przez klienta.

## Gdzie co wkleić

| Plik | Miejsce w Shopify | Link w stopce |
|---|---|---|
| `regulamin-b2b.html` | Ustawienia → Polityki → **Regulamin świadczenia usług** | `/policies/terms-of-service` (dodać do menu `obsluga-klienta` jako „Regulamin B2B”) |
| `polityka-prywatnosci.html` | Ustawienia → Polityki → **Polityka prywatności** | `/policies/privacy-policy` (już podpięta w stopce) |
| `polityka-cookies.html` | Treść → Strony → nowa strona „Polityka cookies” | dodać do stopki obok „Preferencje dotyczące plików cookie” |
| `wysylka-i-dostawa.html` | Ustawienia → Polityki → **Zasady wysyłki** | `/policies/shipping-policy` (już w stopce) |
| `zwroty-i-reklamacje.html` | Ustawienia → Polityki → **Zasady zwrotów** | `/policies/refund-policy` (już w stopce) |
| `warunki-wspolpracy.html` | Treść → Strony → strona `warunki-wspolpracy` | już w stopce (obecnie 404) |
| `faq.html` | Treść → Strony → strona `faq` | już w stopce (obecnie 404) |

Edytor polityk w Shopify przyjmuje HTML: w edytorze tekstu kliknąć `<>` (pokaż HTML) i wkleić zawartość pliku. Tabele przechodzą poprawnie.

Po dodaniu scope `write_content` do aplikacji „Import Katalogu” (Dev Dashboard → wersja → Access scopes) strony da się wgrać skryptem zamiast ręcznie.

## Decyzje Adriana (pola `[…]`)

1. Minimalna wartość zamówienia (albo brak minimum).
2. Progi rabatowe (ilość/kwota i procenty) — muszą zgadzać się z katalogiem B2B w Shopify.
3. Cennik dostaw: przewoźnicy, koszt paczki w PL, próg darmowej dostawy, stawki UE.
4. Czas wysyłki produktów „Dostępny od ręki” (1–3 dni?) i czas aktywacji konta (1–2 dni?).
5. Płatność odroczona: po ilu zamówieniach, ile dni (14/30), kto decyduje o limicie.
6. Zwroty towaru pełnowartościowego: opłata manipulacyjna (X% albo brak).
7. Private label: minimum sztuk, tolerancja ilościowa ±X%.
8. Adres e-mail do spraw RODO, ewentualny IOD.
9. Lista narzędzi: Klaviyo, Baselinker, Google Analytics, Meta Pixel — tylko te faktycznie używane zostają w polityce prywatności i cookies.
10. Operator płatności (PayPal, Shopify Payments, PayU) — nazwa do polityki prywatności.
11. Data publikacji dokumentów.

## Ustawienia w panelu Shopify powiązane z dokumentami

- **Wymagaj logowania przed zakupem:** Ustawienia → Konta klientów → wymagane logowanie przy realizacji zakupu. Zamyka checkout dla gości niezależnie od motywu.
- **Baner cookies (PKE art. 399):** Ustawienia → Prywatność klienta → Baner plików cookie → włączyć dla „Wszystkie regiony” lub EOG, tryb „zgoda przed zbieraniem”. Link „Preferencje dotyczące plików cookie” w stopce już działa.
- **Podatki netto:** Ustawienia → Podatki i cła → wyłączyć „Uwzględnij podatek w cenach”, stawka PL 23%, dla UE B2B włączyć pobieranie numeru VAT i zwolnienie WDT (Shopify: „Zbieraj numer VAT” + status zwolnienia na koncie firmy).
- **Ręczna metoda płatności „Przelew bankowy”:** Ustawienia → Płatności → Ręczne metody → instrukcja z numerem konta. Warunki płatności per firma: Klienci → Firmy → lokalizacja → Warunki płatności (Net 14/30).
- **Zgoda marketingowa (PKE art. 398):** w formularzu newslettera i rejestracji zgoda musi być odrębna i dobrowolna. Formularz newslettera w stopce zapisuje `accepts_marketing` — treść zgody obok pola: „Chcę otrzymywać e-maile z informacjami o nowościach i ofertach Achti. Zgodę mogę wycofać w każdej chwili.” (do dodania w sekcji stopki, ustawienie `newsletter_note`).
- **E-maile transakcyjne:** Ustawienia → Powiadomienia → przetłumaczyć na polski, dodać dane do przelewu w „Potwierdzenie zamówienia”.
- **KSeF:** wystawianie faktur poza Shopify (program księgowy / Baselinker z KSeF). Shopify nie wystawia faktur VAT.

## Co wynika z prawa — notatki

- **B2B tylko:** Regulamin § 2 wyłącza konsumentów i „przedsiębiorców na prawach konsumenta” (art. 7aa ustawy o prawach konsumenta) — zakup czapek do odsprzedaży ma charakter zawodowy, więc 14-dniowe odstąpienie nie przysługuje. Gdyby Achti kiedyś sprzedawało też detalicznie, potrzebny osobny regulamin B2C (Omnibus, odstąpienie, rękojmia konsumencka).
- **Regulamin usług elektronicznych** (art. 8 ustawy o świadczeniu usług drogą elektroniczną): rodzaj usługi (konto), wymagania techniczne, zakaz treści bezprawnych, tryb reklamacji — § 3, 4, 14.
- **Rękojmia B2B:** Kodeks cywilny pozwala ją ograniczyć między przedsiębiorcami (art. 558 § 1). Projekt ogranicza do 12 miesięcy, z obowiązkiem zbadania towaru i zgłoszenia wad (art. 563). Zamiast całkowitego wyłączenia, bo Achti jest producentem i chce budować zaufanie.
- **Terminy płatności:** ustawa o przeciwdziałaniu nadmiernym opóźnieniom w transakcjach handlowych — max 60 dni, odsetki ustawowe za opóźnienie w transakcjach handlowych, rekompensata 40/70/100 EUR. Zastrzeżenie własności do zapłaty: art. 589 KC.
- **Ryzyko w transporcie:** art. 544 KC — przechodzi na kupującego z chwilą wydania przewoźnikowi; art. 76 Prawa przewozowego — szkody niewidoczne zgłaszać do 7 dni.
- **KSeF:** obowiązkowy dla wszystkich podatników od 1.04.2026 (duzi od 1.02.2026), najmniejsze firmy od 1.01.2027. Faktury B2B Achti muszą iść przez KSeF.
- **Cookies i marketing:** Prawo komunikacji elektronicznej (od 10.11.2024) — art. 399 zgoda na cookies inne niż niezbędne, art. 398 odrębna zgoda na każdy kanał marketingu (e-mail, telefon). Zgody newslettera muszą być odrębne od akceptacji regulaminu.
- **RODO:** polityka realizuje art. 13/14 (administrator, cele, podstawy, odbiorcy, transfery, okresy, prawa, PUODO). Shopify International Ltd (Irlandia) jako procesor; transfer do Kanady (decyzja adekwatności) i USA (DPF / SCC). Weryfikacja NIP w rejestrach — art. 6 ust. 1 lit. b i f.
- **Platforma ODR:** zlikwidowana 20.07.2025, link i wzmianka o ODR nie mogą być w regulaminie. W projekcie ich nie ma.
- **GPSR (rozporządzenie 2023/988, od 13.12.2024):** dotyczy produktów konsumenckich. Achti jako producent musi mieć na produkcie/opakowaniu nazwę, adres pocztowy i e-mail oraz identyfikator (model/partia). W ofercie online skierowanej do konsumentów (sklepy klientów Achti!) te dane muszą być widoczne przed zakupem. Rekomendacja: dodać w karcie produktu blok „Producent: ACHTI Sp. z o.o. Sp.k., Bieńkowice 152, 32-410 Dobczyce, biuro@achti.pl” i udostępniać go klientom w feedzie — zrobię jako blok w main-product po decyzji.
- **Skład surowcowy (rozporządzenie UE 1007/2011):** etykieta i oferta muszą podawać skład w nazwach włókien z załącznika I i procentach („80% akryl, 20% wełna”), nie nazwy handlowe przędzy („Vezuv”). Obecne metapole „Skład” zawiera nazwy przędz z nazw plików — klient musi uzupełnić prawdziwy skład procentowy. To ważne także dla sklepów, które kupują od Achti.
- **Oznaczenie kraju pochodzenia** nie jest obowiązkowe w UE, ale „Wyprodukowano w Polsce” to atut — w opisach już jest.

## Źródła

- Prawo komunikacji elektronicznej: https://www.prawo.pl/biznes/prawo-komunikacji-elektronicznej-zgoda-na-dzialania-marketingowe,534839.html, https://www.lex.pl/pke-a-rodo-zgoda-na-marketing-i-zglaszanie-naruszen-danych-osobowych,38233.html
- KSeF harmonogram: https://www.mbank.pl/artykuly/ksef-harmonogram/, https://www.infakt.pl/blog/wdrozenie-ksef-harmonogram-2026-r/
- GPSR: https://www.prawo.pl/biznes/rozporzadzenie-gpsr-obowiazki-dla-firm-i-sklepow-internetowych,530380.html, https://mdl-kancelariaprawna.pl/porady-prawne/sprzedaz-online-w-2025-roku-w-kontekscie-art-19-gpsr-poradnik/
- Likwidacja ODR: https://www.prawo.pl/biznes/uokik-e-sklepy-musza-zmienic-zapisy-o-platformie-odr,531199.html
- Regulamin B2B/hurtowni: https://www.cstore.pl/blog/sklep-internetowy-b2b-a-regulamin/, https://artgroup.com.pl/2026/06/11/regulamin-hurtowni-internetowej/
- Rozporządzenie 1007/2011 (skład włókien): https://eur-lex.europa.eu/legal-content/PL/TXT/?uri=celex:32011R1007
- Prawo przewozowe art. 76: https://rpms.pl/reklamacja-w-prawie-transportowym/
- Shopify a RODO/transfery: https://creativa.legal/rodo-dla-sklepu-internetowego-poradnik/
- Dane firmy: https://krs-pobierz.pl/achti-spolka-z-ograniczona-odpowiedzialnoscia-spolka-komandytowa-i7083153, http://achti.pl/kontakt/

Teksty przygotowane na podstawie przepisów i praktyki rynkowej; przed publikacją warto, żeby przejrzał je radca prawny klienta, zwłaszcza § 9–10 regulaminu (ograniczenie rękojmi i odpowiedzialności).
