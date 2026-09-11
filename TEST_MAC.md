# Testy akceptacyjne – MacBook (Apple Silicon)

Checklist do wykonania na docelowym Macu przed przekazaniem aplikacji użytkownikowi.

## Przygotowanie

- [ ] Rozpakuj `Harmonogramy-Mac.zip`
- [ ] Uruchom w Terminalu (w folderze projektu):
  ```bash
  chmod +x prepare_mac.sh start.command Harmonogramy.app/Contents/MacOS/Harmonogramy
  ./prepare_mac.sh
  ```

---

## Test 1: Brak Pythona

**Warunek:** Python niezainstalowany (lub tymczasowo ukryty z PATH).

- [ ] Dwuklik `Harmonogramy.app`
- [ ] Pojawia się alert: „Brak Pythona” z instrukcją instalacji z python.org
- [ ] Aplikacja nie crashuje bez komunikatu

---

## Test 2: Pierwsze uruchomienie (z Pythonem 3.10)

- [ ] Zainstaluj Python 3.10 z python.org (.pkg)
- [ ] Skopiuj folder `Harmonogramy` do `~/Applications/`
- [ ] Przeciągnij `Harmonogramy.app` na pulpit
- [ ] Prawy klik → Otwórz (obejście Gatekeeper, jeśli wymagane)
- [ ] Powiadomienie o pierwszej instalacji pakietów (2–4 min)
- [ ] Po zakończeniu otwiera się Safari/Chrome na `http://localhost:8501`
- [ ] Tytuł strony: „Zautomatyzowany System Generowania Harmonogramów Pracy”
- [ ] W folderze aplikacji powstał podfolder `.venv`

---

## Test 3: Kolejne uruchomienie (< 5 s)

- [ ] Zamknij kartę przeglądarki i okno Terminala (jeśli widoczne)
- [ ] Ponowny dwuklik `Harmonogramy.app`
- [ ] Start w **mniej niż 5 sekund**
- [ ] Przeglądarka otwiera istniejącą stronę aplikacji

---

## Test 4: Port już zajęty

- [ ] Uruchom aplikację (serwer działa)
- [ ] Drugi dwuklik `Harmonogramy.app` **bez zamykania pierwszej**
- [ ] Otwiera się przeglądarka z działającą aplikacją (bez błędu portu)

---

## Test 5: Funkcjonalność biznesowa

- [ ] Wgraj `personel_wlasciwy.csv` w panelu bocznym
- [ ] Opcjonalnie wgraj `niedyspozycje.csv`
- [ ] Wybierz rok i miesiąc
- [ ] Kliknij **Generuj harmonogram**
- [ ] Pojawiają się zakładki z harmonogramami
- [ ] Eksport działa (CSV/Excel – według UI)

---

## Test 6: Zamykanie

- [ ] Zamknij kartę przeglądarki
- [ ] Zamknij okno Terminala (jeśli otwarte)
- [ ] W Terminalu: `lsof -i :8501` – **brak** procesu nasłuchującego

---

## Test 7: Ikona (opcjonalnie)

- [ ] Prawy klik `Harmonogramy.app` → Pobierz informacje
- [ ] Wklej własną ikonę PNG 512×512
- [ ] Ikona widoczna na pulpicie po odświeżeniu

---

## Wynik

| Data | Tester | Mac (model/chip) | macOS | Wynik |
|------|--------|------------------|-------|-------|
|      |        | M_ / Apple Silicon |       | OK / FAIL |

Uwagi:
