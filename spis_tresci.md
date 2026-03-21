# Przykładowy spis treści pracy licencjackiej

**Tytuł pracy:**
Zautomatyzowany system do generowania harmonogramów pracy dla personelu medycznego, oparty o algorytmy heurystyczne

---

## Spis treści

**Wstęp** ............................................................................................................................................. 1

---

### Rozdział 1. Harmonogramowanie pracy w jednostkach ochrony zdrowia

1.1. Specyfika organizacji pracy w szpitalu .................................................................................. 5
1.2. Prawne i organizacyjne uwarunkowania czasu pracy personelu medycznego ........................ 7
1.3. Rodzaje umów i norm czasu pracy pielęgniarek oraz opiekunów medycznych ...................... 9
1.4. Analiza istniejących rozwiązań do zarządzania harmonogramami ......................................... 11
1.5. Uzasadnienie potrzeby automatyzacji procesu układania grafiku ......................................... 13

---

### Rozdział 2. Problem harmonogramowania jako zagadnienie obliczeniowe

2.1. Formalna definicja problemu harmonogramowania zmianowego ........................................... 15
2.2. Klasyfikacja problemu – złożoność obliczeniowa NP-trudnych problemów szeregowania .... 17
2.3. Przegląd podejść do rozwiązywania problemów harmonogramowania .................................. 19
&nbsp;&nbsp;&nbsp;&nbsp;2.3.1. Metody dokładne (programowanie liniowe, przeszukiwanie z powrotami) ................ 19
&nbsp;&nbsp;&nbsp;&nbsp;2.3.2. Metody metaheurystyczne (algorytmy genetyczne, symulowane wyżarzanie) .......... 21
&nbsp;&nbsp;&nbsp;&nbsp;2.3.3. Heurystyki zachłanne – uzasadnienie wyboru do niniejszej pracy ........................... 23
2.4. Ograniczenia twarde i miękkie w problemach harmonogramowania szpitalnego .................. 25

---

### Rozdział 3. Projekt systemu

3.1. Wymagania funkcjonalne i niefunkcjonalne systemu ............................................................. 27
3.2. Architektura modułowa aplikacji ............................................................................................ 29
&nbsp;&nbsp;&nbsp;&nbsp;3.2.1. Moduł wczytywania danych personelu (`data_loader`) .............................................. 30
&nbsp;&nbsp;&nbsp;&nbsp;3.2.2. Moduł obliczania świąt polskich (`holidays`) ............................................................. 31
&nbsp;&nbsp;&nbsp;&nbsp;3.2.3. Moduł obliczania normatywów godzinowych (`normative`) ...................................... 32
&nbsp;&nbsp;&nbsp;&nbsp;3.2.4. Moduł walidacji ograniczeń (`constraints`) ................................................................ 33
&nbsp;&nbsp;&nbsp;&nbsp;3.2.5. Moduł algorytmu generowania harmonogramu (`scheduler`) ................................... 34
&nbsp;&nbsp;&nbsp;&nbsp;3.2.6. Moduł interfejsu użytkownika (`ui_components`) ..................................................... 35
3.3. Model danych – struktura pracownika i harmonogramu ........................................................ 36
3.4. Konfiguracja norm obsady dla poszczególnych oddziałów .................................................... 38
3.5. Format plików wejściowych CSV ........................................................................................... 40

---

### Rozdział 4. Algorytm heurystyczny generowania harmonogramu

4.1. Uzasadnienie wyboru heurystyki zachłannej .......................................................................... 43
4.2. Ograniczenia twarde uwzględnione w algorytmie .................................................................. 45
4.3. Ograniczenia miękkie i funkcja oceny (scoring) .................................................................... 47
&nbsp;&nbsp;&nbsp;&nbsp;4.3.1. Priorytet niedoboru godzin (S1) .................................................................................. 48
&nbsp;&nbsp;&nbsp;&nbsp;4.3.2. Balansowanie dyżurów nocnych, weekendowych i świątecznych (S2–S4) ............... 49
&nbsp;&nbsp;&nbsp;&nbsp;4.3.3. Równomierne rozłożenie zmian w czasie (S5) ........................................................... 50
&nbsp;&nbsp;&nbsp;&nbsp;4.3.4. Ochrona pojemności tygodniowej (S6) ....................................................................... 51
&nbsp;&nbsp;&nbsp;&nbsp;4.3.5. Rotacja niedzielna (S7) .............................................................................................. 52
4.4. Opis faz algorytmu krok po kroku ......................................................................................... 53
&nbsp;&nbsp;&nbsp;&nbsp;4.4.1. Faza 0 – przygotowanie danych i obliczanie normatywów ........................................ 53
&nbsp;&nbsp;&nbsp;&nbsp;4.4.2. Faza 1 – przydzielanie zmian R pracownikom 7h35min ............................................. 54
&nbsp;&nbsp;&nbsp;&nbsp;4.4.3. Faza 2 – przydzielanie zmian pracownikom kontraktowym ....................................... 55
&nbsp;&nbsp;&nbsp;&nbsp;4.4.4. Faza 3 – wypełnianie minimalnej normy obsady (etatowcy + fallback) ..................... 56
&nbsp;&nbsp;&nbsp;&nbsp;4.4.5. Faza 3b – uzupełnianie niedoborów godzin etatowców ............................................. 58
&nbsp;&nbsp;&nbsp;&nbsp;4.4.6. Faza 4 – przydzielanie końcówek DK ......................................................................... 59
&nbsp;&nbsp;&nbsp;&nbsp;4.4.7. Faza 5 – awaryjne uzupełnianie dni bez obsady ........................................................ 60
4.5. Analiza złożoności obliczeniowej algorytmu .......................................................................... 61
4.6. Znane ograniczenia heurystyki i możliwe rozszerzenia ......................................................... 63

---

### Rozdział 5. Implementacja systemu

5.1. Wybór technologii – Python, Streamlit, Pandas ..................................................................... 65
5.2. Obliczanie polskich świąt ruchomych i stałych ...................................................................... 67
5.3. Implementacja ograniczeń harmonogramowania ................................................................... 69
5.4. Implementacja algorytmu zachłannego ................................................................................... 71
5.5. Interfejs użytkownika – interaktywna tabela harmonogramu ................................................. 74
&nbsp;&nbsp;&nbsp;&nbsp;5.5.1. Kolorowanie komórek (weekendy, święta, typy zmian) ............................................... 75
&nbsp;&nbsp;&nbsp;&nbsp;5.5.2. Edycja harmonogramu i automatyczna rekalkulacja ................................................... 76
5.6. Tabela podsumowująca – bilans godzin i liczniki dyżurów .................................................... 77
5.7. Eksport danych do plików CSV i Excel ................................................................................... 78

---

### Rozdział 6. Testowanie i weryfikacja systemu

6.1. Metodyka testowania .............................................................................................................. 79
6.2. Weryfikacja spełnienia norm obsady na dobę ......................................................................... 80
6.3. Weryfikacja braku nadgodzin dla pracowników etatowych .................................................... 82
6.4. Weryfikacja równomiernego rozłożenia dyżurów nocnych i weekendowych ......................... 84
6.5. Testy dla różnych miesięcy i wariantów personelu ................................................................ 86
6.6. Omówienie wyników i ograniczeń systemu ............................................................................ 88

---

### Zakończenie ............................................................................................................................... 91

---

### Literatura .................................................................................................................................... 93

---

### Spis rysunków ............................................................................................................................. 97

### Spis tabel .................................................................................................................................... 98

### Spis listingów .............................................................................................................................. 99

---

### Załączniki

Załącznik A. Przykładowy plik CSV z danymi personelu .............................................................101
Załącznik B. Przykładowy plik CSV z niedyspozycjami pracowników ........................................102
Załącznik C. Przykładowy wygenerowany harmonogram dla oddziału gastrologicznego .............103

---

> **Uwaga:** Numery stron są orientacyjne. Objętość pracy licencjackiej zazwyczaj wynosi 50–80 stron tekstu głównego.
