# Heurystyka algorytmu generowania harmonogramów pracy

## 1. Definicja problemu

### Kontekst szpitalny

System obsługuje **trzy oddziały szpitalne**: gastrologiczny, wewnętrzny oraz OIOK. Dla każdego oddziału generowane są oddzielne harmonogramy dla pielęgniarek i opiekunek. Opiekunki oddziałów wewnętrznego i OIOK prowadzą wspólny harmonogram. Łącznie powstaje **5 harmonogramów**:

| Klucz harmonogramu | Oddział | Rola |
|--------------------|---------|------|
| `gastro_piel` | Gastrologiczny | Pielęgniarki (2D + 2N + 1R na dobę) |
| `gastro_opiek` | Gastrologiczny | Opiekunki (1–2D + 1N na dobę) |
| `wew_piel` | Wewnętrzny | Pielęgniarki (2D + 2N na dobę) |
| `oiok_piel` | OIOK | Pielęgniarki (1D + 1N + 1R na dobę) |
| `wew_oiok_opiek` | Wewnętrzny + OIOK | Opiekunki wspólnie (2D + 2N na dobę) |

### Formalizacja

Problem generowania harmonogramów pracy dla personelu medycznego należy do klasy problemów NP-trudnych. Formalizując: mamy zbiór pracowników `P`, zbiór dni `D` (np. 31 dni miesiąca), zbiór typów zmian `S = {D, N, DN, R, DK}` oraz zbiór ograniczeń `C`. Szukamy funkcji przydziału `f: P × D → S ∪ {∅}` takiej, że:

- każdego dnia spełnione są normy obsady dla każdego oddziału,
- dla każdego pracownika spełnione są wszystkie ograniczenia `C`,
- normatyw godzin każdego pracownika jest osiągnięty.

Przestrzeń możliwych przydziałów rośnie wykładniczo wraz z liczbą pracowników i dni, co uniemożliwia przeszukiwanie wszystkich możliwości metodą siłową w rozsądnym czasie.

## 2. Wybór heurystyki zachłannej

### Uzasadnienie wyboru

Do rozwiązania problemu zastosowano **heurystykę zachłanną** (ang. *greedy algorithm*). Algorytm zachłanny w każdym kroku dokonuje lokalnie optymalnej decyzji bez cofania się i przeglądania alternatyw. Wybór ten jest uzasadniony:

1. **Szybkość działania** – złożoność wielomianowa (O(P · D · S)) zamiast wykładniczej, co umożliwia generowanie harmonogramu w sekundy nawet dla ~50 pracowników i 31 dni.
2. **Interpretowalność** – wynikowy harmonogram jest łatwy do wyjaśnienia i modyfikacji przez człowieka.
3. **Wystarczająca jakość** – w praktycznych systemach harmonogramowania szpitalnego wyniki algorytmów zachłannych z odpowiednio zaprojektowaną funkcją oceny są akceptowalne i zbliżone do rozwiązań optymalnych.
4. **Wymagania pracy dyplomowej** – heurystyka zachłanna spełnia wymagania zastosowania algorytmu heurystycznego.

## 3. Ograniczenia algorytmu

### Ograniczenia twarde (muszą być zawsze spełnione)

| ID | Ograniczenie |
|----|-------------|
| C1 | Pracownik jest niedyspozycyjny w danym dniu (CSV niedyspozycji) |
| C2 | Pracownik ma już przydzieloną zmianę w danym dniu |
| C3 | Flaga `pracuje_w_weekendy = nie` + data jest sobotą/niedzielą |
| C4 | Przerwa od końca poprzedniej zmiany do początku nowej < 12h |
| C5 | Etatowiec: suma godzin w tygodniu po dodaniu zmiany > 36h |
| C6 | Etatowiec: suma godzin po dodaniu zmiany > normatyw (nadgodziny) |
| C7 | Co 4. niedziela musi być wolna – po 3 kolejnych niedzielach roboczych następna niedziela jest zablokowana (dotyczy wszystkich pracowników) |

### Ograniczenia miękkie (optymalizowane przez funkcję scoring)

| ID | Ograniczenie | Waga |
|----|-------------|------|
| S1 | Priorytet dla pracowników z największym niedoborem godzin | +10/12h blok |
| S2 | Balansowanie liczby dyżurów nocnych względem średniej grupy | -5/dyżur ponad śr. |
| S3 | Balansowanie dyżurów weekendowych | -3/dyżur ponad śr. |
| S4 | Balansowanie dyżurów świątecznych | -3/dyżur ponad śr. |
| S5 | Równomierne rozłożenie zmian w czasie – bonus za większą przerwę od ostatniej zmiany | +min(dni_przerwy, 7) × 2 |
| S6 | Ochrona pojemności tygodniowej – kara gdy ta zmiana byłaby ostatnią możliwą w tygodniu (tylko etatowcy zmianowi) | -15 |
| S7 | Rotacja niedzielna – kara gdy przydzielenie w tę niedzielę zablokowałoby pracownika na następną (2 poprzednie niedziele pracujące) | -500 |

## 4. Struktura algorytmu krok po kroku

### Faza 0: Przygotowanie

```
1. Wczytaj dane personelu z CSV
2. Wczytaj niedyspozycje z CSV (opcjonalnie)
3. Oblicz informacje o miesiącu:
   - lista dni, liczba dni roboczych
   - zbiór świąt polskich (stałe + Wielkanoc obliczona Gaussowską Formułą Wielkanocną + Boże Ciało)
4. Oblicz normatywy dla każdego pracownika:
   - etat zwykły: dni_robocze × 7h35min = N_min minut
   - etat z orzeczeniem: dni_robocze × 7h00min
   - duży kontrakt: minimum 160h
   - mały kontrakt: minimum 120h
5. Rozłóż normatyw etatowca na zmiany:
   - pelne_12h = N_min // 720 min
   - końcówka = N_min % 720 min (np. 7h40min)
6. Zgrupuj pracowników wg harmonogramu (5 grup):
   - gastro_piel, gastro_opiek, wew_piel, oiok_piel, wew_oiok_opiek
```

### Faza 1: Przydzielanie zmian R (7:00–14:35)

Dotyczy pracowników z flagą `tylko_7h = tak` (np. Miącz Ewa, Bzowska Ewelina, Gańska Ewa).

```
DLA KAŻDEGO dnia roboczego (pn–pt, nie święto):
  DLA KAŻDEGO pracownika z flagą tylko_7h:
    JEŚLI pracownik nie ma zmiany w tym dniu
      AND normatyw nie jest jeszcze wypełniony
      AND wszystkie ograniczenia twarde są spełnione:
        PRZYDZIEL zmianę R
```

Pracownicy ci pracują wyłącznie na zmianie R we wszystkie dni robocze miesiąca, bez dyżurów nocnych i weekendowych.

### Faza 2: Przydzielanie zmian kontraktowcom

Dotyczy pracowników z typem umowy `duzy_kontrakt` lub `maly_kontrakt`.

```
POSORTUJ kontraktowców rosnąco wg liczby już przydzielonych zmian
  (najpierw ci z mniejszą liczbą – zapewnia równomierne rozłożenie w grupie)

DLA KAŻDEGO kontraktowca (w powyższej kolejności):
  DOPÓKI przepracowane < minimum_kontraktu:
    ZBIERZ wszystkie możliwe (dzień, kod) – kod ∈ {DN, D, N}:
      - pomijaj dni zajęte lub niedostępne (ograniczenia twarde)
      - respektuj limit max_day_shifts / max_night_shifts (bez tłumów)
    DLA KAŻDEGO kandydującego dnia oblicz klucz sortowania:
      klucz = (obsada_dnia, -luka, kara_kolejny, od_idealnej_pozycji)
        obsada_dnia  – łączna bieżąca obsada D+N (im mniejsza, tym lepiej)
        luka         – rozmiar luki między sąsiednimi zmianami pracownika
                       (im większa luka, tym bardziej „potrzebny" jest tam dzień)
        kara_kolejny – 200 gdy dzień następuje bezpośrednio po zmianie (unikanie skupisk)
        od_ideal     – odległość od idealnie równomiernej pozycji w miesiącu
    WYBIERZ dzień+kod z NAJNIŻSZYM kluczem → PRZYDZIEL zmianę
```

Algorytm preferuje dyżury 24h (DN), ponieważ:
- kontrakt wymaga dużej liczby godzin (min 160h/120h),
- w oryginalnych grafikach kontraktowcy mają dyżury DN,
- minimalizuje to liczbę dni z dyżurami.

### Faza 3: Obsada D/N – wypełnienie minimalnej normy

Jest to główna faza – zapewnia spełnienie minimalnej normy obsady dla każdego dnia.

```
min_D = norma.day_shifts_min   # elastyczne minimum (np. 1 dla zakresu 1–2)
min_N = norma.night_shifts     # stałe minimum nocne

DLA KAŻDEGO dnia miesiąca:
  POLICZ aktualną obsadę D i N (z kontraktów + wcześniejszych przydziałów)
  brak_D = max(0, min_D - obsada_D)
  brak_N = max(0, min_N - obsada_N)

  # Krok 1: uzupełnij etatowcami zmianowymi
  DLA każdego brakującego dyżuru D:
    DLA KAŻDEGO etatowca bez zmiany w tym dniu:
      OBLICZ score(pracownik, dzień, "D")  [patrz sekcja 5]
    PRZYDZIEL zmianę D pracownikowi z NAJWYŻSZYM score

  DLA każdego brakującego dyżuru N:
    (analogicznie jak D, scoring dla kodu "N")

  # Krok 2 (fallback): jeśli po Kroku 1 wciąż brakuje obsady
  # (np. wszyscy etatowcy wyczerpali normatyw lub są zablokowania)
  → uzupełnij kontraktowcami, którzy jeszcze nie mają zmiany w tym dniu
```

Dwuetapowy fallback jest konieczny np. w ostatnią niedzielę miesiąca 5-niedzielnego, gdy wszyscy etatowcy mają wyczerpany normatyw lub blokadę rotacji niedzielnej.

### Faza 3b: Uzupełnianie niedoborów godzin etatowców

Po Fazie 3 minimalna norma obsady jest spełniona, ale część etatowców może nadal mieć niedobór godzin do normatywu (np. gdy nie przydzielono im wystarczającej liczby zmian w Fazie 3). Ta faza przydziela dodatkowe dyżury D lub N, przestrzegając górnych limitów obsady na dobę.

```
POWTARZAJ dopóki jakikolwiek etatowiec ma niedobór ≥ 12h:

  POSORTUJ etatowców rosnąco wg liczby zmian
    (najpierw ci z najmniejszą liczbą – wyrównuje obciążenie)

  DLA KAŻDEGO etatowca z niedoborem ≥ 12h:
    ZBIERZ wolne dni, w które można przydzielić D lub N:
      - respektuj ograniczenia twarde (przerwa 12h, 36h/tydz., normatyw)
      - respektuj limit max_day_shifts / max_night_shifts (bez tłumów)
    DLA KAŻDEGO kandydującego dnia oblicz klucz: (obsada, -luka, kara_kolejny)
    WYBIERZ najlepszy dzień → PRZYDZIEL D lub N
```

Limity `max_day_shifts` i `max_night_shifts` (konfigurowane w `config.py` per oddział) gwarantują, że dopełnianie niedoborów nie generuje „tłumów" na jednej dobie.

### Faza 4: Końcówki DK

Po przydzieleniu dyżurów 12h część etatowców ma niedobór mniejszy niż 12h (bo normatyw nie jest wielokrotnością 720 min).

```
DLA KAŻDEGO etatowca zmianowego:
  JEŚLI normatyw.końcówka > 0 AND przepracowane < normatyw:
    SZUKAJ pierwszego wolnego dnia roboczego (pn–pt, nie święto):
      JEŚLI przerwa 12h spełniona:
        PRZYDZIEL zmianę DK (o długości = końcówka minut)
        BREAK
```

### Faza 5: Uzupełnienie pustych dni (fallback awaryjny)

Ta faza jest siatką bezpieczeństwa. Sprawdza, czy każdy dzień miesiąca ma co najmniej jedną osobę na zmianie roboczej, i awaryjnie uzupełnia dni całkowicie puste.

```
DLA KAŻDEGO dnia miesiąca:
  JEŚLI liczba osób z jakąkolwiek zmianą roboczą >= 1 → POMIŃ

  # Dzień całkowicie pusty – dwie próby przydzielenia:
  PRÓBA 1 (bez nadgodzin):
    POSORTUJ pracowników rosnąco wg bilansu (najpierw ci z niedoborem)
    DLA KAŻDEGO pracownika (w powyższej kolejności):
      JEŚLI niedyspozycja LUB zajęty LUB weekendowe ograniczenie → POMIŃ
      JEŚLI etat AND przepracowane + 12h > normatyw → POMIŃ
      PRZYDZIEL D lub N (w zależności od aktualnej obsady D vs N) → BREAK

  PRÓBA 2 (emergency – jeśli Próba 1 się nie powiodła):
    Jak wyżej, ale bez sprawdzania bilansu normatywu
    → zapewnia, że żaden dzień nie pozostaje całkowicie bez obsady
```

## 5. Funkcja scoring – szczegóły

Funkcja `score_pracownik(p, data, kod, state)` zwraca liczbę rzeczywistą:

```
score = 0

# Ograniczenia twarde – eliminacja kandydata
JEŚLI NIE czy_mozna_przydzielic(...):
    ZWRÓĆ -∞

# Kryterium 1 (S1): priorytet niedoboru godzin
score += (pozostałe_minuty / 720) × 10

# Kryterium 2 (S2): balans dyżurów nocnych
avg_nocne = suma_nocnych_w_grupie / liczba_pracowników
score -= max(0, nocne_pracownika - avg_nocne) × 5

# Kryterium 3 (S3): balans weekendów
avg_weekend = suma_weekendowych / liczba_pracowników
score -= max(0, weekendowe_pracownika - avg_weekend) × 3

# Kryterium 4 (S4): balans świąt
avg_swieta = suma_swiatecznych / liczba_pracowników
score -= max(0, swiateczne_pracownika - avg_swieta) × 3

# Kryterium 5 (S5): równomierne rozłożenie – bonus za dłuższą przerwę od ostatniej zmiany
gap = liczba_dni_od_ostatniej_zmiany(pracownik, data)
score += min(gap, 7) × 2       # bonus rośnie do 7 dni, potem plateau

# Kryterium 6 (S6): ochrona pojemności tygodniowej (tylko etatowcy zmianowi)
JEŚLI etat AND NOT tylko_7h:
    pozostalo_w_tygodniu = 36h - juz_przepracowane_w_tygodniu - 12h
    JEŚLI pozostalo_w_tygodniu < 12h:
        score -= 15             # ta zmiana wyczerpuje tydzień → kara

# Kryterium 7 (S7): rotacja niedzielna (wspiera ograniczenie C7)
# Cel: unikać sytuacji, w której pracownik przepracowałby 3 niedziele z rzędu
# i nie miałby wolnej 4. niedzieli w miesiącu.
JEŚLI data jest niedzielą:
    JEŚLI pracownik miał dyżur w poprzednią niedzielę AND dwie niedziele temu
       AND następna niedziela jest w tym samym miesiącu:
        score -= 500            # przydzielenie teraz blokuje następną niedzielę

ZWRÓĆ score
```

Wagi zostały dobrane eksperymentalnie tak, aby:
- Priorytet niedoboru godzin był dominującym kryterium zwykłym (waga 10).
- Balans nocy był ważniejszy od weekendów/świąt (waga 5 > 3).
- Równomierne rozłożenie (S5, max +14) działało jako miękka korekta.
- Rotacja niedzielna (S7, −500) była praktycznie wetem, ustępującym tylko gdy nie ma lepszej opcji.

## 6. Złożoność obliczeniowa

| Faza | Złożoność | Opis |
|------|-----------|------|
| Faza 0 | O(P) | Obliczanie normatywów |
| Faza 1 | O(D × P_R) | P_R – liczba pracowników tylko_7h |
| Faza 2 | O(D × P_K²) | P_K – kontraktowcy, sortowanie kandydatów po dniach |
| Faza 3 | O(D × P_E²) | P_E – etatowcy, scoring każdego kandydata |
| Faza 3b | O(iter × D × P_E²) | iter – liczba iteracji pętli uzupełniania (≤ P_E) |
| Faza 4 | O(D × P_E) | Szukanie dnia na końcówkę |
| Faza 5 | O(D × P) | Fallback awaryjny dla pustych dni |
| **Łącznie** | **O(P_E × D × P²)** | Praktycznie: D=31, P_E≤12 → kilkadziesiąt tysięcy operacji |

Dla typowych rozmiarów (50 pracowników, 5 grup, 31 dni) całkowity czas generowania wynosi poniżej 1 sekundy.

## 7. Przykład działania – Faza 3 dla dnia 01.01.2026

Dane: Wewnętrzny – Pielęgniarki, norma = 2D + 2N, 13 pracowników.

```
Dzień: 01.01.2026 (Czwartek, Nowy Rok – ŚWIĘTO)
Obsada wymagana: 2D + 2N
Obsada z kontraktów: 0D + 0N (kontrakty już przydzielone w Fazie 2)

→ brak_D = 2, brak_N = 2

Kandydaci do D:
  Adamczyk Halina   (etat): score = 9.9 (normatyw prawie pełny – wysokie braki)
  Filiks Maria      (etat): score = 9.8
  Jakowiecka Małg.  (etat): C4 naruszone (za mała przerwa) → score = -∞
  ...

Przydzielono D: Adamczyk Halina, Filiks Maria
Przydzielono N: [analogicznie]
```

## 8. Ograniczenia i możliwe rozszerzenia

### Znane ograniczenia heurystyki zachłannej:
- Algorytm nie cofa decyzji – lokalne optimum może nie być globalnym.
- Przy skrajnie napiętym harmonogramie (mało personelu) może nie wypełnić normy obsady.
- Kolejność rozpatrywania dni (chronologiczna) faworyzuje początki miesiąca.

### Możliwe rozszerzenia (poza zakresem pracy):
- Algorytm genetyczny lub symulowane wyżarzanie dla globalnej optymalizacji.
- Uwzględnienie preferencji zmianowych pracowników.
- Planowanie wielomiesięczne z ciągłością bilansów.

---

*Dokument sporządzony na potrzeby pracy dyplomowej: „Zautomatyzowany system do generowania harmonogramów pracy dla personelu medycznego, oparty o algorytmy heurystyczne", 2025/2026.*
