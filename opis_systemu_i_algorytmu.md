# Opis systemu i algorytmu heurystycznego

## Zautomatyzowany system generowania harmonogramów pracy dla personelu medycznego

---

## 1. Cel dokumentu

Niniejszy dokument opisuje architekturę, funkcjonalność oraz algorytm heurystyczny zastosowany w systemie automatycznego generowania miesięcznych harmonogramów pracy dla personelu medycznego (pielęgniarek i opiekunek) trzech oddziałów szpitalnych. Dokument jest przeznaczony do wykorzystania w pracy dyplomowej licencjackiej i zawiera:

- opis problemu harmonogramowania i uzasadnienie wyboru heurystyki,
- klasyfikację zastosowanego algorytmu,
- szczegółowy opis architektury modułowej systemu,
- pełną dokumentację algorytmu krok po kroku,
- opis funkcji oceny (scoring) z wyjaśnieniem wag,
- analizę złożoności obliczeniowej.

---

## 2. Opis problemu harmonogramowania

### 2.1. Kontekst szpitalny

System obsługuje **trzy oddziały szpitalne**: gastrologiczny, wewnętrzny oraz OIOK (Oddział Intensywnej Opieki Kardiologicznej). Dla każdego oddziału generowane są oddzielne harmonogramy dla pielęgniarek i opiekunek. Opiekunki oddziałów wewnętrznego i OIOK prowadzą wspólny harmonogram. Łącznie w ramach jednego miesiąca powstaje **5 harmonogramów**:

| Klucz harmonogramu | Oddział | Rola | Minimalna obsada na dobę |
|--------------------|---------|------|--------------------------|
| `gastro_piel` | Gastrologiczny | Pielęgniarki | 2D + 2N + 1R |
| `gastro_opiek` | Gastrologiczny | Opiekunki | 1–2D + 1N |
| `wew_piel` | Wewnętrzny | Pielęgniarki | 2D + 2N |
| `oiok_piel` | OIOK | Pielęgniarki | 1D + 1N + 1R |
| `wew_oiok_opiek` | Wewnętrzny + OIOK | Opiekunki wspólnie | 2D + 2N |

### 2.2. Formalizacja

Problem generowania harmonogramów pracy należy do klasy problemów NP-trudnych. Formalizując: mamy zbiór pracowników `P`, zbiór dni `D` (np. 31 dni miesiąca), zbiór typów zmian `S = {D, N, DN, R, DK}` oraz zbiór ograniczeń `C`. Szukamy funkcji przydziału:

```
f: P × D → S ∪ {∅}
```

takiej, że:

- każdego dnia spełnione są normy obsady dla danego oddziału,
- dla każdego pracownika spełnione są wszystkie ograniczenia `C`,
- normatyw godzin każdego pracownika jest osiągnięty lub przekroczony (dla kontraktów: minimum).

Przestrzeń możliwych przydziałów rośnie wykładniczo:

```
|rozwiązań| = |S|^(|P| × |D|)
```

Dla 15 pracowników i 31 dni: ok. 5^465 możliwości — przeszukanie metodą siłową jest niemożliwe obliczeniowo.

### 2.3. Typy zmian

| Kod | Nazwa | Czas trwania | Godziny |
|-----|-------|-------------|---------|
| D | Dyżur dzienny | 12h (720 min) | 7:00–19:00 |
| N | Dyżur nocny | 12h (720 min) | 19:00–7:00 |
| DN | Dyżur całodobowy | 24h (1440 min) | 7:00–7:00 (dnia następnego) |
| R | Zmiana robocza | 7h35min (455 min) | 7:00–14:35 |
| DK | Końcówka | indywidualna | 7:00–… |
| U | Urlop wypoczynkowy | 0h | — |
| W | Wolne za niedzielę/święto | 0h | — |

---

## 3. Klasyfikacja zastosowanej heurystyki

Zastosowany algorytm jest **konstruktywną, wielofazową heurystyką zachłanną**.

### 3.1. Charakterystyka

| Cecha | Wartość |
|-------|---------|
| Typ | Heurystyka konstruktywna (ang. *constructive heuristic*) |
| Strategia | Zachłanna (ang. *greedy*) — w każdym kroku lokalnie optymalna decyzja |
| Liczba faz | 5 głównych faz (+ faza 0: przygotowanie) |
| Deterministyczność | Deterministyczny (dla tych samych danych — ten sam wynik) |
| Cofanie decyzji | Brak (ang. *no backtracking*) |
| Ograniczenia twarde | Egzekwowane przed każdym przydziałem (hard constraint filtering) |
| Ograniczenia miękkie | Optymalizowane przez funkcję oceny (scoring function) |

### 3.2. Uzasadnienie wyboru

1. **Szybkość działania** — złożoność wielomianowa O(P · D · S) zamiast wykładniczej; generowanie harmonogramu trwa poniżej 1 sekundy nawet dla ~50 pracowników i 31 dni.
2. **Interpretowalność** — wynikowy harmonogram jest łatwy do wyjaśnienia i modyfikacji przez człowieka (pielęgniarka oddziałowa może go edytować ręcznie w interfejsie).
3. **Wystarczająca jakość** — w praktycznych systemach harmonogramowania szpitalnego wyniki heurystyk zachłannych z odpowiednio zaprojektowaną funkcją oceny są akceptowalne i zbliżone do rozwiązań optymalnych.
4. **Wielofazowość** — podział na fazy pozwala najpierw zaspokoić bezwzględne priorytety (zmiany R, kontrakty), a dopiero potem wypełnić pozostałe miejsca etatowcami, co naśladuje ręczny proces układania grafiku.

---

## 4. Architektura systemu — moduły

System zbudowany jest w architekturze modułowej. Każdy plik odpowiada za ściśle określoną odpowiedzialność (ang. *single responsibility principle*).

```
praca-dyplomowa-harmonogram-cursor/
├── app.py                  ← punkt wejścia Streamlit
├── config.py               ← centralna konfiguracja
├── requirements.txt        ← zależności Python
├── modules/
│   ├── __init__.py
│   ├── data_loader.py      ← wczytywanie CSV personelu
│   ├── holidays.py         ← polskie święta (algorytm Gaussa)
│   ├── normative.py        ← obliczanie normatywów godzin
│   ├── constraints.py      ← walidacja ograniczeń twardych
│   ├── scheduler.py        ← algorytm heurystyczny (rdzeń)
│   └── ui_components.py    ← interfejs Streamlit + Pandas Styler
```

### 4.1. `app.py` — punkt wejścia aplikacji

Główny plik uruchamiany komendą `streamlit run app.py`. Odpowiada za:

- konfigurację strony Streamlit (tytuł, układ dwukolumnowy, pasek boczny),
- obsługę uploadu plików CSV (personel, niedyspozycje) przez `st.file_uploader`,
- wybór miesiąca i roku za pomocą selektorów w pasku bocznym,
- wywołanie funkcji `generuj_wszystkie_harmonogramy()` po kliknięciu przycisku,
- wyświetlenie wyników w 5 zakładkach (`st.tabs`) — po jednej na harmonogram,
- wyświetlenie nagłówka z informacją o normatywie (liczba dni roboczych, minuty, podział na zmiany 12h + końcówka).

Plik nie zawiera logiki biznesowej — jedynie koordynuje przepływ danych między modułami.

### 4.2. `config.py` — centralna konfiguracja

Przechowuje wszystkie stałe i reguły domenowe jako **jedyne źródło prawdy** (ang. *single source of truth*). Dzięki temu zmiana np. minimalnej normy obsady wymaga edycji tylko jednego miejsca. Zawiera:

- `SHIFT_DURATIONS` — słownik: kod zmiany → czas trwania w minutach (D=720, N=720, DN=1440, R=455, DK=None)
- `SHIFT_START_HOUR`, `SHIFT_END_HOUR` — godziny początku i końca każdej zmiany (używane do obliczania 12h przerwy)
- `WORKING_SHIFTS = {"D", "N", "DN", "R", "DK"}` — kody liczące się jako czas pracy
- `NIGHT_SHIFTS = {"N", "DN"}` — kody dyżurów nocnych (do statystyk)
- `WORK_MINUTES_PER_DAY_STANDARD = 455` (7h35min), `WORK_MINUTES_PER_DAY_DISABILITY = 420` (7h00min)
- `MIN_HOURS_DUZY_KONTRAKT = 9600` (160h), `MIN_HOURS_MALY_KONTRAKT = 7200` (120h)
- `MAX_WEEKLY_MINUTES_ETAT = 2160` (36h tygodniowo)
- `FULL_SHIFT_MINUTES = 720` (12h — jednostka podstawowa dyżuru)
- Klasa `DailyStaffingNorm` — wymagana i maksymalna obsada D/N/R per harmonogram
- Słownik `STAFFING_NORMS` — normy obsady dla każdego z 5 harmonogramów
- Funkcja `get_schedule_key(oddzial, rola)` — mapowanie oddział + rola → klucz harmonogramu

### 4.3. `modules/data_loader.py` — wczytywanie danych wejściowych

Odpowiedzialny za parsowanie i walidację plików CSV:

**Klasa `Pracownik` (dataclass)** — reprezentuje jednego pracownika:
- `imie_nazwisko: str` — klucz identyfikacyjny
- `oddzial: str`, `rola: str` — przynależność do harmonogramu
- `typ_umowy: str` — `"etat"`, `"duzy_kontrakt"` lub `"maly_kontrakt"`
- `orzeczenie: bool` — pracownik z orzeczeniem o niepełnosprawności (skrócony czas pracy)
- `tylko_7h: bool` — pracownik wyłącznie na zmianach R (7h35min)
- `pracuje_w_weekendy: bool` — flaga zgody na pracę w weekend
- `niedyspozycje: set[date]` — zbiór dat, w których pracownik jest niedostępny

**Funkcje modułu:**
- `wczytaj_personel(source)` — wczytuje CSV personelu, waliduje kolumny i typy wartości, zwraca listę obiektów `Pracownik`
- `wczytaj_niedyspozycje(source, pracownicy)` — wczytuje CSV niedyspozycji (format: `imie_nazwisko, data`), przypisuje daty do odpowiednich pracowników
- `grupuj_wg_harmonogramu(pracownicy)` — zwraca słownik `{schedule_key: [Pracownik]}` dzielący personel na 5 grup

### 4.4. `modules/holidays.py` — polskie święta ustawowe

Moduł oblicza wszystkie 13 ustawowych dni wolnych od pracy w Polsce:

**Funkcja `_oblicz_wielkanoc(rok)`** — implementuje **Gaussowską Formułę Wielkanocną** (niem. *Gaußsche Osterformel*, C.F. Gauss, ok. 1800 r.):

```python
a = rok % 19          # pozycja roku w cyklu Metona (19 lat)
b = rok % 4           # cykl korekcyjny
c = rok % 7           # cykl tygodniowy
k = rok // 100        # numer stulecia
p = (13 + 8*k) // 25  # korekta stulecia dla epakty
q = k // 4            # korekta przestępna stulecia
M = (15 - p + k - q) % 30   # epakta stulecia (dni do pełni)
N = (4 + k - q) % 7         # korekta dnia tygodnia stulecia
d = (19*a + M) % 30          # liczba dni od 21 marca do pełni
e = (2*b + 4*c + 6*d + N) % 7  # korekta do najbliższej niedzieli
```

Wynik: data Niedzieli Wielkanocnej (marzec lub kwiecień). Dwa szczególne przypadki korygowane: 26 kwietnia → 19 kwietnia, 25 kwietnia (przy d=28, e=6, a>10) → 18 kwietnia.

Zalety algorytmu Gaussa nad innymi metodami: jawne zmienne astronomiczne (epakta `M`, pełnia `d`, korekta niedzieli `e`), krótszy kod (10 zmiennych), powszechne cytowanie w podręcznikach algorytmów i matematyki.

**Funkcja `pobierz_swieta(rok)`** — zwraca zbiór dat: 9 świąt stałych (Nowy Rok, Trzech Króli, 1 i 3 maja, 15 sierpnia, 1 i 11 listopada, 25–26 grudnia) + 4 ruchome (Wielkanoc, Poniedziałek Wielkanocny, Zielone Świątki +49 dni, Boże Ciało +60 dni).

**Funkcja `get_month_info(rok, miesiac)`** — agreguje: lista wszystkich dni, dni robocze (bez weekendów i świąt), liczniki. Używana przez `app.py` i `scheduler.py`.

### 4.5. `modules/normative.py` — obliczanie normatywów

Oblicza miesięczny wymiar czasu pracy każdego pracownika.

**Klasa `Normatyw` (dataclass)** — przechowuje wynik:
- `minuty: int` — łączny normatyw w minutach
- `pelne_dyzury_12h: int` — liczba pełnych dyżurów 12h (`minuty // 720`)
- `koncowka_minuty: int` — reszta po pełnych dyżurach (`minuty % 720`)
- `typ_umowy: str`, `dni_robocze: int`

**Funkcja `oblicz_normatyw(pracownik, liczba_dni_roboczych)`** — logika:

```
Etat zwykły:
    minuty = liczba_dni_roboczych × 455 min (7h35min)

Etat z orzeczeniem o niepełnosprawności:
    minuty = liczba_dni_roboczych × 420 min (7h00min)

Rozkład na zmiany 12h (tylko dla pracowników zmianowych, nie tylko_7h):
    pelne_12h = minuty // 720
    koncowka  = minuty % 720

Duży kontrakt:
    minuty = 9600 min (minimum 160h)

Mały kontrakt:
    minuty = 7200 min (minimum 120h)
```

Przykład dla marca 2026 (22 dni robocze, etat zwykły):
```
minuty   = 22 × 455 = 10010 min = 166h50min
pelne_12h = 10010 // 720 = 13 dyżurów × 12h
koncowka  = 10010 % 720  = 650 min = 10h50min
```

### 4.6. `modules/constraints.py` — walidacja ograniczeń twardych

Zawiera funkcje sprawdzające ograniczenia C1–C7 **przed każdym przydzieleniem**. Naruszenie choćby jednego ograniczenia twardego wyklucza pracownika z kandydatów na dany dzień.

| Funkcja | Ograniczenie |
|---------|-------------|
| `sprawdz_niedyspozycje(p, data)` | C1: pracownik niedyspozycyjny w danym dniu |
| `sprawdz_weekendy(p, data, kod)` | C3: zakaz pracy w weekend przy fladze `pracuje_w_weekendy=False` |
| `sprawdz_przerwe_12h(przydzial, data, kod)` | C4: minimalna przerwa 12h od końca **poprzedniej** zmiany (wstecz) |
| `sprawdz_przerwe_12h_nastepna(przydzial, data, kod)` | C4: minimalna przerwa 12h do początku **następnej** już przydzielonej zmiany (wprzód) |
| `sprawdz_max_36h_tydzien(przydzial, data, kod, p)` | C5: max 36h w tygodniu dla etatowców zmianowych |
| `sprawdz_bilans_bez_nadgodzin(przepracowane, normatyw, kod)` | C6: zakaz nadgodzin dla etatowców |
| `sprawdz_co_4_niedziela(przydzial, data, kod, rok, miesiac)` | C7: bidirectionalna kontrola serii roboczych niedziel |

**Funkcja `czy_mozna_przydzielic(...)`** — centralna bramka: agreguje wszystkie powyższe funkcje i zwraca `True` tylko gdy **każde** ograniczenie jest spełnione. Wywołana przed przydzieleniem zmiany w każdej z 5 faz algorytmu. Ograniczenie C4 sprawdzane jest dwukrotnie: najpierw wstecz (`sprawdz_przerwe_12h`), a następnie wprzód (`sprawdz_przerwe_12h_nastepna`).

**Szczegóły C4 — dwukierunkowa kontrola przerwy 12h:**

Klasyczne sprawdzenie wstecz (czy poprzednia zmiana skończyła się ≥12h przed nową) nie wystarcza, gdy algorytm przydziela zmiany w kolejności niechronologicznej (np. Faza 3b może przydzielić zmianę N we wtorek, gdy środowe D zostało przydzielone wcześniej). Dlatego każdorazowo sprawdzane jest również, czy nowa zmiana kończy się co najmniej 12h przed początkiem następnej już przydzielonej zmiany roboczej (sprawdzane wprzód do 2 dni).

**Szczegóły C7 — bidirectionalna kontrola niedziel:**

Funkcja `sprawdz_co_4_niedziela` sprawdza nie tylko historię wstecz, ale również niedziele **już przydzielone w przyszłości** (w tym samym miesiącu). Zapobiega to tworzeniu niedozwolonych serii przez fazy uzupełniające, które mogą przydzielać zmiany w innej kolejności niż chronologiczna.

```
seria = niedziele_robocze_przed_datą + 1 + niedziele_robocze_po_dacie
Dozwolone: seria ≤ 3
```

### 4.7. `modules/scheduler.py` — algorytm heurystyczny (rdzeń systemu)

Najważniejszy moduł — implementuje wielofazowy algorytm zachłanny. Szczegółowy opis faz zawiera Sekcja 8 niniejszego dokumentu.

**Klasa `HarmonogramState`** — bieżący stan harmonogramu jednej grupy:
- `przydzial: dict[str, dict[date, str]]` — słownik `{imie: {data: kod}}`
- `przepracowane: dict[str, int]` — przepracowane minuty per pracownik
- liczniki: `liczba_nocnych`, `liczba_weekendowych`, `liczba_swiatecznych`, `liczba_dziennych`
- metoda `przydziel(imie, data, kod)` — przydziela zmianę i aktualizuje wszystkie liczniki
- metoda `liczba_na_dzien(data, typ)` — zwraca liczbę osób pracujących danego dnia na danym typie

**Funkcja `score_pracownik(p, data, kod, state)`** — ocena kandydata (patrz Sekcja 9).

**Funkcja `generuj_wszystkie_harmonogramy(pracownicy, rok, miesiac)`** — wywołuje pipeline dla każdej z 5 grup niezależnie, zwraca słownik `{schedule_key: HarmonogramState}`.

### 4.8. `modules/ui_components.py` — interfejs użytkownika

Renderuje wyniki w przeglądarce za pomocą Streamlit i Pandas Styler.

**Kluczowe funkcje:**

- `buduj_df_do_edycji(state, dni, swieta, pokazuj_niedyspozycje=False)` — tworzy DataFrame: wiersze = pracownicy, kolumny = dni miesiąca; puste komórki jako `""` (nie `NaN`). Gdy `pokazuj_niedyspozycje=True`, komórki w dniach z `Pracownik.niedyspozycje` wypełniane są symbolem `"X"` (tylko widok — nie edytor).
- `_buduj_styled_df(df, dni, swieta)` — Pandas Styler z dynamicznym kolorowaniem:
  - weekendy: szary `#636363`, biały tekst
  - święta: czerwony `#B31515`, biały tekst
  - zmiany: D=`#118249`, N=`#12196B`, DN=`#731A6E`, R=`#5F6639`, DK=`#9C6B10`
  - niedyspozycja (`X`): ciemnoczerwony `#C62828`, biały tekst
- `renderuj_harmonogram(state, dni, swieta, normatyw_info)` — buduje dwa osobne DataFrame: `df_widok` (z `X` dla niedyspozycji, przekazywany do Pandas Styler) oraz `df` (czysty, bez `X`, przekazywany do `st.data_editor`); po edycji automatycznie przelicza bilanse
- `oblicz_podsumowanie(state, normatywy)` — tabela z kolumnami: normatyw, przepracowane, bilans, liczba dyżurów nocnych/dziennych/weekendowych/świątecznych, suma dyżurów
- `eksportuj_harmonogram(state, dni, key)` — eksport do CSV i Excel z pustymi komórkami (bez NaN/None)

---

## 5. Typy zmian i normy obsady

### 5.1. Kody zmian

| Kod | Typ | Czas [min] | Start | Koniec | Liczy się do normatywu |
|-----|-----|-----------|-------|--------|------------------------|
| D | Dyżur dzienny | 720 | 7:00 | 19:00 | Tak |
| N | Dyżur nocny | 720 | 19:00 | 7:00+1d | Tak |
| DN | Dyżur całodobowy | 1440 | 7:00 | 7:00+1d | Tak |
| R | Zmiana robocza | 455 | 7:00 | 14:35 | Tak |
| DK | Końcówka | indyw. | 7:00 | — | Tak |
| U | Urlop | 0 | — | — | Nie |
| W | Wolne | 0 | — | — | Nie |

### 5.2. Normy obsady per harmonogram

| Harmonogram | Min D | Min N | Min R | Max D | Max N | Max R |
|-------------|-------|-------|-------|-------|-------|-------|
| gastro_piel | 2 | 2 | 1 | 3 | 3 | 1 |
| gastro_opiek | 1–2 | 1 | 0 | 3 | 2 | 0 |
| wew_piel | 2 | 2 | 0 | 3 | 3 | 0 |
| oiok_piel | 1 | 1 | 1 | 2 | 2 | 1 |
| wew_oiok_opiek | 2 | 2 | 0 | 3 | 3 | 0 |

Wartości `max_*` ograniczają liczbę osób danego typu na jednej dobie, zapobiegając skupieniu zbyt wielu dyżurów w jednym dniu (efekt „tłumu").

---

## 6. Obliczanie normatywu

### 6.1. Wzór ogólny

**Etatowiec (normatyw elastyczny — zależy od liczby dni roboczych w miesiącu):**

```
N_min = dni_robocze × stawka_minutowa

gdzie:
  stawka_minutowa = 455 min (7h35min)  dla pracownika bez orzeczenia
  stawka_minutowa = 420 min (7h00min)  dla pracownika z orzeczeniem
```

**Rozkład na zmiany 12h (tylko pracownicy zmianowi):**

```
pelne_12h = N_min // 720
koncowka  = N_min mod 720
```

Jeśli `koncowka > 0`, pracownik otrzymuje jedną zmianę DK o długości `koncowka` minut.

**Kontraktowiec (normatyw stały — minimalna liczba godzin):**

```
Duży kontrakt:  N_min = 9600 min  (160h)
Mały kontrakt:  N_min = 7200 min  (120h)
```

Kontraktowcy muszą **osiągnąć lub przekroczyć** minimum. Dla nich nie obowiązuje zakaz nadgodzin ani limit 36h/tydzień.

### 6.2. Przykład — marzec 2026

- Dni robocze: 22
- Etat zwykły: 22 × 455 = **10 010 min = 166h50min**
- Rozkład: 10010 // 720 = **13 dyżurów × 12h** + końcówka 10010 % 720 = **650 min = 10h50min**
- Etat z orzeczeniem: 22 × 420 = **9 240 min = 154h00min**
- Rozkład: 9240 // 720 = **12 dyżurów × 12h** + końcówka 9240 % 720 = **600 min = 10h00min**

---

## 7. Ograniczenia algorytmu

### 7.1. Ograniczenia twarde (C — zawsze muszą być spełnione)

| ID | Ograniczenie | Funkcja w kodzie |
|----|-------------|-----------------|
| C1 | Pracownik jest niedyspozycyjny w danym dniu | `sprawdz_niedyspozycje` |
| C2 | Pracownik ma już przydzieloną zmianę roboczą w tym dniu | `czy_mozna_przydzielic` |
| C3 | Flaga `pracuje_w_weekendy = False` i data jest sobotą lub niedzielą | `sprawdz_weekendy` |
| C4 | Przerwa między zmianami mniejsza niż 12h – sprawdzana **dwukierunkowo**: od końca poprzedniej do początku nowej (`sprawdz_przerwe_12h`) ORAZ od końca nowej do początku następnej już przydzielonej zmiany (`sprawdz_przerwe_12h_nastepna`) | `sprawdz_przerwe_12h`, `sprawdz_przerwe_12h_nastepna` |
| C5 | Etatowiec zmianowy: suma godzin w tygodniu po dodaniu zmiany przekracza 36h | `sprawdz_max_36h_tydzien` |
| C6 | Etatowiec: suma przepracowanych godzin po dodaniu zmiany przekracza normatyw (nadgodziny) | `sprawdz_bilans_bez_nadgodzin` |
| C7 | Co 4. niedziela musi być wolna — seria roboczych niedziel (wstecz + 1 + wprzód) nie może przekroczyć 3 | `sprawdz_co_4_niedziela` |

### 7.2. Ograniczenia miękkie (S — optymalizowane przez scoring)

| ID | Kryterium | Waga | Kierunek |
|----|-----------|------|---------|
| S1 | Priorytet pracowników z największym niedoborem godzin | +10 na blok 12h | Wyższy niedobór → wyższy priorytet |
| S2 | Balans dyżurów nocnych względem średniej grupy | −5 za dyżur ponad średnią | Zmniejsza różnice między pracownikami |
| S3 | Balans dyżurów weekendowych | −3 za dyżur ponad średnią | j.w. |
| S4 | Balans dyżurów świątecznych | −3 za dyżur ponad średnią | j.w. |
| S5 | Równomierne rozłożenie zmian — bonus za dłuższą przerwę od ostatniej zmiany | +min(przerwa_dni, 7) × 2 | Zapobiega skupianiu zmian |
| S6 | Ochrona pojemności tygodniowej (tylko etatowcy zmianowi) | −15 | Kara gdy zmiana wyczerpuje limit 36h |
| S7 | Rotacja niedzielna — kara blokująca 4. niedzielę z rzędu | −500 | Praktycznie weto |

---

## 8. Algorytm krok po kroku

### Faza 0: Przygotowanie danych

```
WEJŚCIE: plik CSV personelu, plik CSV niedyspozycji (opcjonalny), rok, miesiąc

1. Wczytaj personel → lista obiektów Pracownik
2. Wczytaj niedyspozycje → zaktualizuj pola Pracownik.niedyspozycje
3. Oblicz informacje o miesiącu:
   a. Lista wszystkich dni 1..N
   b. Zbiór świąt: pobierz_swieta(rok) [algorytm Gaussa dla Wielkanocy]
   c. Dni robocze = dni bez weekendów i świąt
   d. Liczba dni roboczych = |dni_robocze|
4. Dla każdego pracownika oblicz normatyw:
   oblicz_normatyw(pracownik, liczba_dni_roboczych) → obiekt Normatyw
5. Podziel personel na 5 grup wg harmonogramu:
   grupuj_wg_harmonogramu(pracownicy) → {klucz: [Pracownik]}
6. Dla każdej grupy: utwórz HarmonogramState(pracownicy, normatywy, dni, swieta)
```

### Faza 1: Przydzielanie zmian R (pracownicy tylko_7h)

Dotyczy pracowników z flagą `tylko_7h = True`.

```
DLA KAŻDEGO dnia roboczego (poniedziałek–piątek, nie święto):
  DLA KAŻDEGO pracownika z flagą tylko_7h:
    JEŚLI czy_mozna_przydzielic(p, dzień, "R", ...):
      state.przydziel(p.imie_nazwisko, dzień, "R")
```

Pracownicy ci mają dyżury R w każdym dniu roboczym. Nie mają dyżurów nocnych, weekendowych ani DK.

### Faza 2: Przydzielanie zmian kontraktowcom

```
POSORTUJ kontraktowców rosnąco wg liczby już przydzielonych zmian

DLA KAŻDEGO kontraktowca p:
  DOPÓKI state.przepracowane[p] < normatyw.minuty:
    
    ZBIERZ kandydujące_dni = []:
    DLA KAŻDEGO dnia w miesiącu:
      DLA KAŻDEGO kodu w ["DN", "D", "N"]:   # preferuj 24h
        JEŚLI state.liczba_na_dzien(dzień, typ) >= max_obsada → POMIŃ (tłum)
        JEŚLI czy_mozna_przydzielic(p, dzień, kod, ...) → dodaj (dzień, kod) do listy
    
    JEŚLI kandydujące_dni jest puste → BREAK (niemożliwe uzupełnienie)
    
    DLA KAŻDEGO (dzień, kod):
      n = liczba zmian już przydzielonych pracownikowi
      potrzebne = max(1, (normatyw.minuty + DN_MINUTY - 1) // DN_MINUTY)
      ideal = (n + 0.5) × len(dni) / potrzebne   # środek n-tego "okna"
      od_ideal = |indeks_dnia - ideal|
      unique_people = liczba unikalnych pracowników w tej samej grupie,
                      którzy w dniu mają jakąkolwiek zmianę roboczą
                      (kod ∈ WORKING_SHIFTS)
      klucz = (unique_people, od_ideal, obsada_dnia, kara_skupień, -rozmiar_luki)
    
    WYBIERZ (dzień, kod) z najniższym kluczem → state.przydziel(p, dzień, kod)
```

Sortowanie po `unique_people` (tłum na dobie) jako kryterium głównym ogranicza „napakowanie” pod koniec miesiąca,
a dopiero potem `od_ideal` wymusza równomierne rozłożenie DN w czasie (po całym miesiącu).

### Faza 3: Obsada minimalna D/N — etatowcy zmianowi

```
min_D = norma.day_shifts_min
min_N = norma.night_shifts

DLA KAŻDEGO dnia miesiąca:
  obs_D = state.liczba_na_dzien(dzień, "D")
  obs_N = state.liczba_na_dzien(dzień, "N")
  brak_D = max(0, min_D - obs_D)
  brak_N = max(0, min_N - obs_N)
  
  # Krok 1: przydziel etatowcami zmianowymi
  DLA i = 1..brak_D:
    kandydaci = [(score_pracownik(p, dzień, "D", state), p)
                 dla każdego etatowca zmianowego p]
    kandydaci = [x dla x w kandydaci JEŚLI score > -∞]
    JEŚLI kandydaci niepuste: przydziel najlepszemu
  
  # (analogicznie dla N)
  
  # Krok 2: fallback — kontraktowcy (jeśli brakuje po Kroku 1)
  JEŚLI obs_D < min_D LUB obs_N < min_N:
    DLA KAŻDEGO kontraktowca (bez zmiany w tym dniu):
      (analogicznie — uzupełnij brakujące D lub N)
  
  # Krok 3: gwarancja ≥ 2 unikalnych osób (gdy min_D>0 i min_N>0)
  unique_total = liczba_unikalnych_pracowników_z_jakąkolwiek_zmianą(dzień)
  JEŚLI unique_total < 2:
    (przydziel dodatkową D lub N z puli dostępnych pracowników)
```

Krok 3 zapobiega sytuacji, w której jeden pracownik z dyżurem DN formalnie pokrywa zarówno D jak i N, ale pracuje sam przez całą dobę.

### Faza 3b: Uzupełnianie niedoborów godzin etatowców

```
POWTARZAJ dopóki ∃ etatowiec zmianowy z niedoborem ≥ 720 min (12h):
  
  POSORTUJ etatowców rosnąco wg liczby przydzielonych zmian
  
  DLA KAŻDEGO etatowca p z niedoborem ≥ 12h:
    ZBIERZ możliwe_dni = []:
    DLA KAŻDEGO dnia:
      DLA kodu w ["D", "N"]:
        JEŚLI state.liczba_na_dzien(dzień, kod_typ) >= max_obsada → POMIŃ
        JEŚLI czy_mozna_przydzielic(p, dzień, kod, ...) → dodaj
    
    JEŚLI możliwe_dni niepuste:
      klucz = (obsada, kara_skupień, -luka, od_ideal)
        obsada     – bieżąca obsada D lub N w tym dniu (KRYTERIUM GŁÓWNE – unikaj tłoku)
        kara_skupień – 200 gdy dzień następuje bezpośrednio po zmianie
        luka       – rozmiar luki między sąsiednimi zmianami pracownika (większa → lepiej)
        od_ideal   – odległość od idealnej pozycji w miesiącu (tylko tiebreaker)
      WYBIERZ najlepszy dzień → przydziel
```

### Faza 4: Końcówki DK

```
DLA KAŻDEGO etatowca zmianowego p:
  JEŚLI normatyw.koncowka_minuty > 0 oraz state.przepracowane[p] < normatyw.minuty:
    ZBIERZ kandydat-dni = {dni robocze pn–pt, bez świąt, gdzie p nie ma jeszcze przydziału
    oraz czy_mozna_przydzielic(p, dzień, "DK", ...) zwraca True}

    DLA każdego kandydata d:
      tlum_na_dobie = liczba osób z jakąkolwiek zmianą roboczą w dniu d
      od_ideal = |indeks(d) - ideal|, gdzie ideal zależy od liczby już przydzielonych bloków 12h
                  (D+DN i N+DN liczą się jako osobne bloki) względem normatyw.pelne_dyzury_12h

    wybierz d z minimalnym kluczem (tlum_na_dobie, od_ideal)
    state.przydziel(p, d, "DK")
```

### Faza 5: Fallback — uzupełnienie pustych dni

```
DLA KAŻDEGO dnia miesiąca:
  JEŚLI ∃ pracownik z jakąkolwiek zmianą roboczą w tym dniu → POMIŃ

  # Próba 1: bez naruszania bilansów
  POSORTUJ wszystkich pracowników rosnąco wg bilansu godzin
  DLA KAŻDEGO pracownika p:
    JEŚLI niedyspozycja LUB zajęty LUB ograniczenie weekendu → POMIŃ
    JEŚLI etat AND przepracowane + 720 > normatyw → POMIŃ
    JEŚLI NOT sprawdz_co_4_niedziela(...) → POMIŃ
    kod = "D" JEŚLI obs_D ≤ obs_N ELSE "N"
    JEŚLI NOT sprawdz_przerwe_12h(...) → POMIŃ          # C4 wstecz
    JEŚLI NOT sprawdz_przerwe_12h_nastepna(...) → POMIŃ  # C4 wprzód
    state.przydziel(p, dzień, kod)
    BREAK
  
  # Próba 2: awaryjnie (bez kontroli bilansu normatywu)
  JEŚLI dzień wciąż pusty:
    (jak wyżej, ale bez warunku bilansu — ostateczna siatka bezpieczeństwa)
```

---

## 9. Funkcja oceny (scoring)

```python
def score_pracownik(p, data, kod, state) -> float:

    # Ograniczenia twarde — eliminacja kandydata
    if not czy_mozna_przydzielic(p, data, kod, ...):
        return -inf

    score = 0.0
    n = len(state.pracownicy)

    # S1: priorytet niedoboru godzin
    score += (state.pozostale_minuty(p.imie_nazwisko) / 720) * 10

    # S2: balans dyżurów nocnych
    avg_nocne = sum(state.liczba_nocnych.values()) / n
    score -= max(0, state.liczba_nocnych[p.imie_nazwisko] - avg_nocne) * 5

    # S3: balans weekendów
    avg_week = sum(state.liczba_weekendowych.values()) / n
    score -= max(0, state.liczba_weekendowych[p.imie_nazwisko] - avg_week) * 3

    # S4: balans świąt
    avg_swiet = sum(state.liczba_swiatecznych.values()) / n
    score -= max(0, state.liczba_swiatecznych[p.imie_nazwisko] - avg_swiet) * 3

    # S5: równomierne rozłożenie — bonus za dłuższą przerwę
    gap = liczba_dni_od_ostatniej_zmiany(p, data, state)
    score += min(gap, 7) * 2    # plateau po 7 dniach → max +14

    # S6: ochrona pojemności tygodniowej (tylko etatowcy zmianowi)
    if p.is_etat and not p.tylko_7h:
        tyg = oblicz_godziny_tygodnia(state.przydzial[p.imie_nazwisko], data)
        if MAX_WEEKLY_MINUTES_ETAT - tyg - 720 < 720:
            score -= 15

    # S7: rotacja niedzielna — weto blokujące 4. z rzędu niedzielę
    if data.weekday() == 6:   # niedziela
        nd_1 = data - timedelta(weeks=1)
        nd_2 = data - timedelta(weeks=2)
        nd_next = data + timedelta(weeks=1)
        if (przydzial.get(nd_1) in WORKING_SHIFTS and
            przydzial.get(nd_2) in WORKING_SHIFTS and
            nd_next.month == data.month):
                score -= 500

    return score
```

**Dobór wag:**

- S1 (+10 na blok 12h) — kryterium dominujące; pracownik z 5 blokami niedoboru otrzymuje +50 względem pracownika z pełnym normatywem.
- S2 (−5) > S3/S4 (−3) — nocne są trudniejsze do zbalansowania niż weekendowe.
- S5 (max +14) — działa jako miękka korekta rozkładu, nie dominuje nad niedoborem.
- S6 (−15) — skromna kara, chroni zdolność planowania reszty tygodnia.
- S7 (−500) — praktyczne weto; ustępuje tylko gdy nie ma żadnego innego kandydata.

---

## 10. Złożoność obliczeniowa

| Faza | Złożoność | Opis |
|------|-----------|------|
| Faza 0 | O(P) | Obliczanie normatywów |
| Faza 1 | O(D × P_R) | P_R – pracownicy tylko_7h; przydzielenie bezwarunkowe |
| Faza 2 | O(D × P_K²) | P_K – kontraktowcy; sortowanie kandydatów po dniach |
| Faza 3 | O(D × P_E²) | P_E – etatowcy zmianowi; scoring dla każdego dnia |
| Faza 3b | O(iter × D × P_E²) | iter ≤ P_E iteracji pętli uzupełniania |
| Faza 4 | O(D × P_E) | Liniowe szukanie dnia na końcówkę |
| Faza 5 | O(D × P) | Fallback dla pustych dni |
| **Łącznie** | **O(P_E × D × P²)** | Praktycznie: D=31, P_E≤12 → kilkadziesiąt tysięcy operacji |

Dla typowych rozmiarów (50 pracowników, 5 grup, 31 dni) całkowity czas generowania wynosi poniżej 1 sekundy. Każda z 5 grup przetwarzana jest niezależnie, co w przyszłości umożliwia łatwe zrównoleglenie.

---

## 11. Interfejs użytkownika i funkcje aplikacji

### 11.1. Widok główny

Aplikacja uruchamiana jest poleceniem `streamlit run app.py` i otwiera się w przeglądarce internetowej. Pasek boczny zawiera:

- przycisk uploadu pliku CSV z personelem (wymagany),
- przycisk uploadu pliku CSV z niedyspozycjami (opcjonalny),
- selektor miesiąca i roku,
- przycisk „Generuj harmonogram".

Po kliknięciu przycisku wyświetlane są 5 zakładek (jedna per harmonogram), każda zawierająca:

1. **Nagłówek** z informacją o normatywie: liczba dni roboczych, łączny czas w minutach i godzinach, rozkład na zmiany 12h + końcówka.
2. **Podgląd harmonogramu** — kolorowana tabela tylko do odczytu (Pandas Styler).
3. **Edytor harmonogramu** — rozwijany panel z edytowalnym `st.data_editor`; zmiany automatycznie przeliczają bilanse po zatwierdzeniu.
4. **Tabela podsumowująca** — per pracownik: normatyw, przepracowane, bilans, liczba dyżurów nocnych/dziennych/weekendowych/świątecznych, suma dyżurów.
5. **Przycisk eksportu** — zapis do pliku CSV lub Excel.

### 11.2. Kolorowanie komórek

| Element | Kolor tła | Kolor tekstu |
|---------|-----------|-------------|
| Weekend (sb, nd) | Szary `#636363` | Biały |
| Święto | Czerwony `#B31515` | Biały |
| Zmiana D | Zielony `#118249` | Biały |
| Zmiana N | Ciemny niebieski `#12196B` | Biały |
| Zmiana DN | Fioletowy `#731A6E` | Biały |
| Zmiana R | Oliwkowy `#5F6639` | Biały |
| Zmiana DK | Brązowy `#9C6B10` | Biały |
| Niedyspozycja (`X`) | Ciemnoczerwony `#C62828` | Biały |
| Pusta komórka | Biały | — |

### 11.3. Edycja i eksport

Kolorowana tabela tylko do odczytu wyświetla symbol `X` (ciemnoczerwone tło) w komórkach odpowiadających dniom niedyspozycji pracownika — o ile wczytano plik CSV niedyspozycji. Symbol `X` pojawia się wyłącznie w pustych komórkach (jeśli tego dnia przydzielono zmianę, zmiana ma pierwszeństwo). Edytor poniżej nie zawiera symbolu `X` — pola niedyspozycji są tam puste, dzięki czemu ręczna edycja pozostaje nieskomplikowana.

Edytor pozwala ręcznie poprawić kod zmiany w dowolnej komórce. Dozwolone kody: `D`, `N`, `DN`, `R`, `DK`, `U`, `W`, `""`. Po zapisaniu zmiany tabela podsumowująca automatycznie się przelicza. Eksport zachowuje puste komórki jako puste (nie `NaN`), nie stosuje kolorowania i nie zawiera symbolu `X` — plik jest gotowy do dalszej obróbki.

---

## 12. Znane ograniczenia i kierunki rozszerzeń

### 12.1. Ograniczenia obecnej wersji

- Algorytm nie cofa decyzji (*no backtracking*) — lokalne optimum może nie być globalnym optimum; w skrajnych przypadkach (mało personelu, wiele niedyspozycji) norma obsady może nie zostać osiągnięta.
- Limit 36h/tydzień oraz normatyw nie są egzekwowane w Fazie 5 Próba 2 (fallback awaryjny) — w sytuacjach kryzysowych możliwe minimalne przekroczenie. Ograniczenie C4 (przerwa 12h) obowiązuje również w Fazie 5.
- Chronologiczna kolejność dni w fazach 3/3b może faworyzować początki miesiąca przy bardzo napiętych harmonogramach.
- Brak obsługi urlopów planowanych (U) — urlopy muszą być wprowadzane ręcznie przez edytor.
- Planowanie jest miesięczne — brak ciągłości bilansów między miesiącami.

### 12.2. Możliwe rozszerzenia

- Zastąpienie heurystyki zachłannej algorytmem genetycznym lub symulowanym wyżarzaniem dla globalnej optymalizacji.
- Uwzględnienie preferencji zmianowych pracowników (np. zakaz nocy, preferowany weekend).
- Planowanie wielomiesięczne z przenoszeniem bilansu godzin i rotacją niedzielną między miesiącami.
- Automatyczne wczytywanie urlopów z pliku CSV.
- Generowanie raportów PDF gotowych do druku.

---

## 13. Przepływ danych — diagram

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  personel   │    │  niedyspozycje   │    │  rok, miesiąc   │
│  .csv       │    │  .csv (opt.)     │    │  (sidebar)      │
└──────┬──────┘    └────────┬─────────┘    └────────┬────────┘
       │                   │                        │
       ▼                   ▼                        ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│ data_loader.py  │ │ data_loader  │ │    holidays.py        │
│ → [Pracownik]   │ │ → niedysp.   │ │    → swieta, dni rob. │
└────────┬────────┘ └──────┬───────┘ └────────────┬─────────┘
         │                 │                       │
         └─────────────────┴───────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  normative.py    │
                        │  → [Normatyw]    │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  scheduler.py    │◄── constraints.py
                        │  (5 faz)         │    (C1–C7)
                        │  → HarmonogramState│
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ ui_components.py │
                        │ → Streamlit UI   │
                        │ → export CSV/XLS │
                        └──────────────────┘
```

---

*Dokument sporządzony na potrzeby pracy dyplomowej licencjackiej:*  
*„Zautomatyzowany system do generowania harmonogramów pracy dla personelu medycznego, oparty o algorytmy heurystyczne", 2025/2026.*
