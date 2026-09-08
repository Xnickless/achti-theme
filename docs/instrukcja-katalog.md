# Jak uzupełnić katalog produktów Achti

Plik: `achti-katalog-do-uzupelnienia.csv` (363 wiersze, jeden wiersz = jeden kod produktu). Otwórz go w Excelu, Numbers albo Google Sheets. Separator kolumn to średnik. Po uzupełnieniu zapisz jako CSV (UTF-8, średnik) albo odeślij zwykły plik Excel. Nie zmieniaj kolejności kolumn i nie usuwaj wierszy.

## Kolumny, których nie ruszamy

Są wypełnione z nazw zdjęć i służą do dopasowania wiersza do produktu w sklepie.

| Kolumna | Co zawiera |
|---|---|
| `kod` | kod produktu, np. AZ-1145PC. Klucz do wszystkiego, nie zmieniać |
| `typ` | Czapka / Komin |
| `material` | nazwa przędzy z pliku zdjęcia (AKRYL, VEZUV, VERONA…) |
| `rozmiar` | One Size, 50-52, 52-54, 56-62 albo wymiar komina |
| `grupa_cenowa` | G3, G5, G7, G10, G12 z nazwy zdjęcia |
| `flagi`, `segment` | dodatkowe oznaczenia z nazw zdjęć (CEKIN, MULTI, KOMIN, Dziecięce…) |
| `plik` | nazwa zdjęcia |

Jeśli coś w tych kolumnach jest błędne (np. zły rozmiar), popraw wartość, ale nie zmieniaj kodu.

## Kolumny do uzupełnienia

### `nazwa_produktu`

Docelowa nazwa handlowa. Dziś w sklepie są nazwy robocze z miastami („Czapka Zimowa Damska Beanie Milano”). Zasady:

- Ta sama nazwa modelu dla wszystkich jego kolorów. Po nazwie łączymy kolory w grupę „inne kolory tego modelu”, więc pisownia musi być identyczna w każdym wierszu tego modelu.
- Wzór: `Czapka zimowa damska <nazwa modelu>`, np. `Czapka zimowa damska Aurora`. Dla dzieci `Czapka zimowa dziecięca …`, dla kominów `Komin zimowy damski …`.
- Bez koloru w nazwie. Kolor idzie do kolumny `kolory`.
- Do 60 znaków.

Jeśli zostawisz puste, zostaje nazwa robocza.

### `kolory (po przecinku)`

Kolory tego kodu, które klient ma wybrać na karcie produktu. Format numer lub zestaw, myślnik, nazwa, po przecinku:

```
120 - Czarny, 245 - Beż, SET 5
```

Jeśli kod ma jeden kolor, wpisz jeden. Jeśli kolory to osobne kody (osobne zdjęcia), zostaw puste, a wpisz tę samą nazwę modelu w `nazwa_produktu`.

### `cena netto PLN`

Wpisuj tylko wtedy, gdy model ma cenę inną niż jego grupa cenowa. Dla reszty wystarczy tabela grup (poniżej). Cena netto, bez VAT, w złotych, z kropką lub przecinkiem, np. `49,90`.

### `cena promocyjna`

Tylko dla modeli na wyprzedaży. Wpisz cenę obniżoną. W sklepie cena z kolumny `cena netto PLN` (lub z grupy) będzie przekreślona, a produkt trafi automatycznie do kolekcji Wyprzedaż.

### `sklad`

Skład surowcowy w procentach i nazwach włókien, tak jak na wszywce:

```
80% akryl, 20% wełna
100% akryl
50% wełna merino, 50% akryl
```

To wymóg prawny (rozporządzenie UE 1007/2011) dla etykiet i ofert online. Nazwa przędzy (Vezuv, Verona) nie wystarczy. Ta kolumna jest najważniejsza obok cen.

### `opis`

Opcjonalnie: jedno, dwa zdania o modelu (fason, ozdoby, dla kogo). Puste = zostaje opis z szablonu. Nie wklejaj składu ani rozmiaru, te są osobno.

### `tagi (damskie/meskie/dzieci/premium/nowosc)`

Decydują, w których kategoriach menu produkt się pokaże. Wpisz jeden lub kilka po przecinku:

| Tag | Kategoria w sklepie |
|---|---|
| `damskie` | Ona |
| `meskie` | On |
| `dzieci` | Dla dzieci |
| `premium` | Premium Merino |
| `nowosc` | Nowości na stronie głównej |

Dziś wszystkie produkty mają `damskie` (dzieci `dzieci`), a 12 najnowszych `nowosc`. Produkt bez tagu nie pokaże się w żadnej kategorii, tylko w wyszukiwarce.

## Informacje poza arkuszem

Te rzeczy wystarczy podać raz, nie przy każdym produkcie.

1. **Ceny grup**: G3, G5, G7, G10, G12, po jednej cenie netto w PLN. Osobno ceny dla 8 kodów bez grupy: AZ-1378PC, AZ-2257LPC, AZ-2258LPC, AZ-2263LPC, AZ-2270LPC, AZ-2300LPC, AZ-2930PC, AZ-2931.
2. **Ceny w euro dla UE**: osobna tabela grup w EUR albo zasada przeliczenia (np. kurs stały).
3. **Progi ilościowe**: np. od 100 szt. −5%, od 300 szt. −10%. Dotyczą sztuk łącznie w zamówieniu czy jednego modelu?
4. **Minimum zamówienia** w złotych lub sztukach, albo brak.
5. **Waga brutto** jednej czapki i jednego komina w gramach (do obliczania wysyłki). Jeśli różnią się między modelami, dodaj kolumnę `waga_g` do arkusza.
6. **Cennik kuriera**: paczka w Polsce, próg darmowej dostawy, stawki do krajów UE, paleta.

## Zdjęcia

- Nowe zdjęcia: nazwa pliku zaczyna się od kodu produktu, np. `AZ-1145PC front.jpg`. Reszta nazwy dowolna.
- Zdjęcia na modelce: `AZ-1145PC modelka.jpg`. Zostaną dodane jako drugie zdjęcie.
- Białe tło i kadr 4:5 robimy po naszej stronie.

## Grupy kolorów

W sklepie kółka „inne kolory tego modelu” zostały dobrane automatycznie po podobieństwie zdjęć. Podgląd wszystkich grup jest w pliku `achti-grupy-modeli.html`. Poprawki:

- Najprościej: ta sama `nazwa_produktu` dla wszystkich kolorów modelu. Po imporcie grupy zostaną przeliczone według nazw.
- Alternatywnie: w panelu Shopify przy produkcie, pole „Inne kolory”.

## Czego nie trzeba robić

- Nie wpisuj cen z VAT. Wszystko netto, VAT liczy sklep.
- Nie tłumacz nazw ani opisów. Tłumaczenia na angielski, niemiecki i francuski generujemy automatycznie z polskiego.
- Nie usuwaj kolumn ani wierszy, nawet dla produktów wycofanych. Zamiast tego wpisz w `tagi` słowo `wycofany`, a my ukryjemy produkt.
