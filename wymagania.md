- Potrzebuję zrobić aplikację na pracę licencjacką z seminarium sztuczna inteligencja. Tytuł mojej aplikacji to „Zautomatyzowany system do generowania harmonogramów pracy dla personelu medycznego, oparty o algorytmy heurystyczne". Chcę, aby ta aplikacja była napisana w python i miała wykorzystaną bibliotekę streamlit do jej uruchamiania w przeglądarce. Mam podane wytyczne odnośnie reguł i zasad, które muszą być uwzględnione przy generowaniu harmonogramu. Będzie do wykorzystane dla szpitala, dla trzech oddziałów: gastrologiczny, wewnętrzny oraz OIOK.
- Chcę aby interfejs był prosty. Importujemy dane personelu z pliku CSV, następnie wygenerowany zostaje harmonogram pracy dla pielęgniarek oraz opiekunek. Każdy oddział musi mieć wygenerowany własny harmonogram. Harmonogram musi być także oddzielny dla pielęgniarek i opiekunek. Na końcu ma być podsumowanie w tabeli, kto ile ma godzin, czy wyrobił normę, jaki ma typ umowy oraz bilans godzinowy, ile miał dyżurów nocnych, ile dziennych, ile świątecznych, ile weekendowych (do każdego harmonogramu takie podsumowanie)
- Normatyw miesięczny obliczany jest w kontekście umowy o pracę, każda osoba, która pracuje na etacie musi mieć dokładnie tyle godzin ile zostało obliczone w normatywie (czyli bilans godzin musi wynosić 0.00h, lub mniej, ale nie może być większy - nie może być nadgodzin). Oblicza się go następująco:

- Ilość dni roboczych \* 7h35min -> zwykli pracownicy
- Ilość dni roboczych \* 7h -> pracownik z orzeczeniem

- Normatyw miesięczny dla osób pracujących na kontrakcie:

- Duży kontrakt = minimum 160h
- Mały kontrakt = minimum 120h

- Rozkład normatywu: Pracownicy, którzy pracują zmianowo mają mieć jak najwięcej dyżurów 12 godzinnych. Pracownicy, którzy pracują w dni robocze pracują od poniedziałku do piątku po 7h35min.
- Normy zatrudnienia w poszczególnych oddziałach:

- Oddział gastrologiczny:
  - Pielęgniarki: 2 po 12h na dyżur dzienny, 2 po 12h na dyżur nocny, 1 pracująca 7h35min. = łącznie 5 na dobę.
  - Opiekunki: 1 lub 2 po 12h na dyżur dzienny, 1 po 12h dyżur nocny = łącznie 2/3 na dobę.
- Oddział wewnętrzny:
  - Pielęgniarki: 2 po 12h dyżur dzienny, 2 po 12h dyżur nocny = łącznie 4 osoby na dobę.
- Oddział OIOK:
  - Pielęgniarki: 1 po 12h dyżur dzienny, 1 po 12h dyżur nocny, 1 pracująca 7h35min = łącznie 3 osoby na dobę.
- Opiekunki na OIOK i na wewnętrznym pracują razem, mają mieć jeden wspólny harmonogram:
  - 2 po 12h dyżur dzienny, 2 po 12h dyżur nocny = łącznie 4 na dobę.

- Ważne kwestie, które należy uwzględnić:

- Ilość dyżurów godzin nocnych i świąteczny powinna być podobna względem pracowników.
- Pracownicy zaznaczają dyspozycje ( osoby plik do wgrania z niedyspozycjami w pliku csv).
- Co 4 niedziela musi być wolna.
- Minimum 12h przerwy między następnymi dyżurami.
- Dla pracowników etatowych: max. W tygodniu można przepracować 36h
- Etatowcy pracują w zmianach 12 godzinnych.
- Dla kontraktów chcemy jak najwięcej dyżurów 24h (lub mogą mieć po 12h).
- Opiekunki mają tylko etat.
- Harmonogram pracy można edytować, automatycznie po edycji zmiana pojawia się w docelowym harmonogramie oraz aktualizuje się godzina w tabeli podsumowującej.
- Aplikacja ma być podzielona na moduły
- Potrzebny jest jeden moduł do obliczania świąt w Polsce. 
- Przykład przydziału zmian dla etatowców: Jeśli normatyw w danym miesiącu wynosi 166h50min to wychodzi 13 dyżurów x 12 godzin + 1 x 10h50min. Te końcówy czyli np. 10h50min również mają być dopisane w harmonogram jako zmiana (końcówka). Na takiej zasadzie przydzielaj pracownikom etatowym zmiany. 
- Aplikacja ma być do pracy dyplomowej - zatem wykorzystaj algorytm zachłanny. Opisz mi na końcu w osobnym pliku MD jaka jest zastosowana heurystyka, jak działa krok po kroku.
- Kod ma być napisany przejrzyście, dodawaj także w nim komentarze. 
- Pamiętaj o spełnieniu minimum godzin przez kontrakty. Może być więcej godzin dla nich ale nie mniej. 