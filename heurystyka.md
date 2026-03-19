# Heurystyka algorytmu generowania harmonogramów pracy

## 1. Definicja problemu

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
| C7 | Etatowiec: 3 kolejne niedziele robocze → następna niedziela musi być wolna |

### Ograniczenia miękkie (optymalizowane przez funkcję scoring)

| ID | Ograniczenie | Waga |
|----|-------------|------|
| S1 | Priorytet dla pracowników z największym niedoborem godzin | +10/12h blok |
| S2 | Balansowanie liczby dyżurów nocnych względem średniej grupy | -5/dyżur ponad śr. |
| S3 | Balansowanie dyżurów weekendowych | -3/dyżur ponad śr. |
| S4 | Balansowanie dyżurów świątecznych | -3/dyżur ponad śr. |

## 4. Struktura algorytmu krok po kroku

### Faza 0: Przygotowanie

```
1. Wczytaj dane personelu z CSV
2. Wczytaj niedyspozycje z CSV (opcjonalnie)
3. Oblicz informacje o miesiącu:
   - lista dni, liczba dni roboczych
   - zbiór świąt polskich (stałe + Wielkanoc + Boże Ciało)
4. Oblicz normatywy dla każdego pracownika:
   - etat zwykły: dni_robocze × 7h35min = N_min minut
   - etat z orzeczeniem: dni_robocze × 7h00min
   - duży kontrakt: minimum 160h
   - mały kontrakt: minimum 120h
5. Rozłóż normatyw etatowca na zmiany:
   - pelne_12h = N_min // 720 min
   - końcówka = N_min % 720 min (np. 7h40min)
6. Zgrupuj pracowników wg harmonogramu (5 grup)
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
DLA KAŻDEGO kontraktowca:
  DLA KAŻDEGO dnia miesiąca (chronologicznie):
    JEŚLI przepracowane < minimum_kontraktu:
      SPRAWDŹ możliwość DN (preferowane – 24h) → JEŚLI OK: PRZYDZIEL DN, BREAK
      SPRAWDŹ możliwość D → JEŚLI OK: PRZYDZIEL D, BREAK
      SPRAWDŹ możliwość N → JEŚLI OK: PRZYDZIEL N, BREAK
```

Algorytm preferuje dyżury 24h (DN), ponieważ:
- kontrakt wymaga dużej liczby godzin (min 160h/120h),
- w oryginalnych grafnikach kontraktowcy mają dyżury DN,
- minimalizuje to liczbę dni z dyżurami.

### Faza 3: Obsada D/N etatowców zmianowych

Jest to główna faza – zapewnia spełnienie normy obsady dla każdego dnia.

```
DLA KAŻDEGO dnia miesiąca:
  POLICZ aktualną obsadę D (z kontraktów i wcześniejszych przydziałów)
  POLICZ aktualną obsadę N
  brak_D = max(0, norma.D - obsada_D)
  brak_N = max(0, norma.N - obsada_N)

  DLA każdego brakującego dyżuru D:
    DLA KAŻDEGO etatowca bez zmiany w tym dniu:
      OBLICZ score = scoring(pracownik, dzień, "D")
        - JEŚLI ograniczenia twarde niespełnione → score = -∞
        - INACZEJ:
            score += (brakujące_godziny / 12h) × 10     [priorytet niedoboru]
            score -= nadwyżka_nocy × 5                  [balans nocy]
            score -= nadwyżka_weekendów × 3              [balans weekendów]
            score -= nadwyżka_świąt × 3                  [balans świąt]
    PRZYDZIEL zmianę D pracownikowi z NAJWYŻSZYM score

  DLA każdego brakującego dyżuru N:
    (analogicznie jak D, scoring dla kodu "N")
```

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

### Faza 5: Weryfikacja

```
DLA KAŻDEGO dnia:
  SPRAWDŹ czy obsada D >= norma.day_shifts
  SPRAWDŹ czy obsada N >= norma.night_shifts
  JEŚLI brak → zaloguj ostrzeżenie (niewystarczająca liczba personelu)

DLA KAŻDEGO pracownika:
  SPRAWDŹ bilans godzin
  JEŚLI etatowiec ma bilans > 0 → ostrzeżenie o nadgodzinach
  JEŚLI kontrakt ma bilans < 0 → ostrzeżenie o niedoborze
```

## 5. Funkcja scoring – szczegóły

Funkcja `score_pracownik(p, data, kod, state)` zwraca liczbę rzeczywistą:

```
score = 0

# Ograniczenia twarde – eliminacja kandydata
JEŚLI NIE czy_mozna_przydzielic(...):
    ZWRÓĆ -∞

# Kryterium 1: priorytet niedoboru godzin
score += (pozostałe_minuty / 720) × 10

# Kryterium 2: balans dyżurów nocnych
avg_nocne = suma_nocnych_w_grupie / liczba_pracowników
score -= max(0, nocne_pracownika - avg_nocne) × 5

# Kryterium 3: balans weekendów
avg_weekend = suma_weekendowych / liczba_pracowników
score -= max(0, weekendowe_pracownika - avg_weekend) × 3

# Kryterium 4: balans świąt
avg_swieta = suma_swiatecznych / liczba_pracowników
score -= max(0, swiateczne_pracownika - avg_swieta) × 3

ZWRÓĆ score
```

Wagi zostały dobrane eksperymentalnie tak, aby:
- Priorytet niedoboru godzin był dominującym kryterium (waga 10).
- Balans nocek był ważniejszy od weekendów/świąt (waga 5 > 3).

## 6. Złożoność obliczeniowa

| Faza | Złożoność | Opis |
|------|-----------|------|
| Faza 0 | O(P) | Obliczanie normatywów |
| Faza 1 | O(D × P_R) | P_R – liczba pracowników tylko_7h |
| Faza 2 | O(D × P_K × 3) | P_K – kontraktowcy, 3 typy zmian |
| Faza 3 | O(D × (P_E)²) | P_E – etatowcy, scoring każdego kandydata |
| Faza 4 | O(D × P_E) | Szukanie dnia na końcówkę |
| **Łącznie** | **O(D × P²)** | Praktycznie: D=31, P≤15 → ~7000 operacji |

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
