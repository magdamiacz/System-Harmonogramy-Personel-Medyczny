# Walidacja ograniczeń harmonogramu dla poszczególnych pracowników.
# Każda funkcja zwraca True, jeśli ograniczenie jest spełnione (można przydzielić zmianę).

import datetime
from typing import Dict, Optional

from config import (
    FULL_SHIFT_MINUTES,
    MAX_WEEKLY_MINUTES_ETAT,
    MIN_REST_MINUTES,
    NIGHT_SHIFTS,
    SHIFT_DURATIONS,
    SHIFT_END_HOUR,
    SHIFT_START_HOUR,
    WORK_MINUTES_PER_DAY_STANDARD,
    WORKING_SHIFTS,
)
from modules.data_loader import Pracownik

# Rytm nocek: najwyżej 2 noce pod rząd, a po serii co najmniej 2 dni wolne.
MAX_KOLEJNYCH_NOCY = 2
DNI_WOLNE_PO_NOCACH = 2

# Pomocnicze: czas końca ostatniej zmiany

def _get_shift_minutes(kod: str, koncowka_minuty: int = 0) -> int:
    """Zwraca długość zmiany w minutach."""
    if kod == "DK":
        return koncowka_minuty
    if kod == "R":
        return WORK_MINUTES_PER_DAY_STANDARD
    dur = SHIFT_DURATIONS.get(kod, 0)
    return dur if dur is not None else 0


def _koniec_zmiany_minuty_od_polnocy(data: datetime.date, kod: str) -> int:
    """
    Zwraca chwilę zakończenia zmiany jako minuty od północy dnia 'data'.
    Dla zmian przechodzących przez północ (N, DN) wartość > 24*60.
    """
    start = SHIFT_START_HOUR.get(kod, 0) * 60
    dur = _get_shift_minutes(kod)
    return start + dur


def czas_konca_poprzedniej(
    przydzial: Dict[datetime.date, str],
    data_teraz: datetime.date,
    koncowka_minuty: int = 0,
) -> Optional[datetime.datetime]:
    """
    Szuka poprzedniej przydzielonej zmiany roboczej i zwraca jej datetime zakończenia.
    Sprawdza wstecz maksymalnie 2 dni (wystarczy dla 24h DN).
    """
    for delta in range(1, 3):
        prev_date = data_teraz - datetime.timedelta(days=delta)
        kod = przydzial.get(prev_date, "")
        if kod not in WORKING_SHIFTS:
            continue

        start_h = SHIFT_START_HOUR.get(kod, 0)
        dur = _get_shift_minutes(kod, koncowka_minuty)
        start_dt = datetime.datetime(prev_date.year, prev_date.month, prev_date.day, start_h, 0)
        end_dt = start_dt + datetime.timedelta(minutes=dur)
        return end_dt
    return None


# Ograniczenie 1: minimum 12h przerwy między zmianami

def sprawdz_przerwe_12h(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    koncowka_minuty: int = 0,
) -> bool:
    """
    Sprawdza, czy między końcem poprzedniej zmiany a początkiem nowej
    jest co najmniej 12h przerwy.

    Zwraca True, jeśli ograniczenie jest spełnione.
    """
    koniec_poprz = czas_konca_poprzedniej(przydzial, data, koncowka_minuty)
    if koniec_poprz is None:
        return True  # Brak poprzedniej zmiany – OK

    start_h = SHIFT_START_HOUR.get(nowy_kod, 0)
    start_nowy = datetime.datetime(data.year, data.month, data.day, start_h, 0)

    # Przerwa = czas od końca poprzedniej do początku nowej
    przerwa_minuty = (start_nowy - koniec_poprz).total_seconds() / 60
    return przerwa_minuty >= MIN_REST_MINUTES


def sprawdz_przerwe_12h_nastepna(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    koncowka_minuty: int = 0,
) -> bool:
    """
    Sprawdza, czy koniec nowej zmiany jest co najmniej 12h przed początkiem
    następnej już przydzielonej zmiany roboczej.
    Sprawdza wprzód maksymalnie 2 dni (wystarczy dla 24h DN).

    Zwraca True, jeśli ograniczenie jest spełnione.
    """
    start_h_nowy = SHIFT_START_HOUR.get(nowy_kod, 0)
    dur_nowy = _get_shift_minutes(nowy_kod, koncowka_minuty)
    koniec_nowy = datetime.datetime(data.year, data.month, data.day, start_h_nowy, 0) + datetime.timedelta(minutes=dur_nowy)

    for delta in range(1, 3):
        next_date = data + datetime.timedelta(days=delta)
        kod_nast = przydzial.get(next_date, "")
        if kod_nast not in WORKING_SHIFTS:
            continue
        start_h_nast = SHIFT_START_HOUR.get(kod_nast, 0)
        start_nast = datetime.datetime(next_date.year, next_date.month, next_date.day, start_h_nast, 0)
        przerwa_minuty = (start_nast - koniec_nowy).total_seconds() / 60
        return przerwa_minuty >= MIN_REST_MINUTES

    return True


# Ograniczenie 2: max 36h w tygodniu (etatowcy)

def _poczatek_tygodnia(data: datetime.date) -> datetime.date:
    """Zwraca poniedziałek tygodnia, do którego należy data."""
    return data - datetime.timedelta(days=data.weekday())


def oblicz_godziny_tygodnia(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    koncowka_minuty: int = 0,
) -> int:
    """
    Oblicza łączną liczbę minut przepracowanych w tygodniu daty 'data'
    (tylko zmiany już przydzielone, bez dnia 'data').
    """
    poczatek = _poczatek_tygodnia(data)
    total = 0
    for delta in range(7):
        d = poczatek + datetime.timedelta(days=delta)
        if d >= data:
            break
        kod = przydzial.get(d, "")
        if kod in WORKING_SHIFTS:
            total += _get_shift_minutes(kod, koncowka_minuty)
    return total


def sprawdz_max_36h_tydzien(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    pracownik: Pracownik,
    koncowka_minuty: int = 0,
) -> bool:
    """
    Dla etatowców zmianowych (12h) sprawdza, czy dodanie nowej zmiany
    nie przekroczy 36h/tydzień.
    Pracownicy tylko_7h i kontrakty są zwolnieni z tego ograniczenia –
    ich tygodniowy czas pracy wynika z normatywu (5×7h35 = 37h55 > 36h).
    """
    if not pracownik.is_etat:
        return True
    # Pracownicy tylko_7h mają stały grafik dzienny – ograniczenie 36h nie dotyczy
    if pracownik.tylko_7h:
        return True

    juz_przepracowane = oblicz_godziny_tygodnia(przydzial, data, koncowka_minuty)
    nowe_minuty = _get_shift_minutes(nowy_kod, koncowka_minuty)
    return (juz_przepracowane + nowe_minuty) <= MAX_WEEKLY_MINUTES_ETAT


# Ograniczenie 3: co 4. niedziela musi być wolna

def sprawdz_co_4_niedziela(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    rok: int,
    miesiac: int,
) -> bool:
    """
    Jeśli 'data' jest niedzielą, sprawdza czy przydzielenie zmiany nie spowoduje
    4 (lub więcej) kolejnych roboczych niedziel w serii.

    Algorytm:
      - Liczy ile kolejnych roboczych niedziel jest PRZED 'data' (wstecz).
      - Liczy ile kolejnych roboczych niedziel jest JUŻ PRZYDZIELONYCH PO 'data'
        (w przód – eliminuje tworzenie serii "od tyłu" przez fazy uzupełniające).
      - Łączna seria = wstecz + 1 + wprzód. Dozwolone: seria <= 3.

    Zwraca True, jeśli można przydzielić zmianę.
    """
    if data.weekday() != 6:
        return True

    if nowy_kod not in WORKING_SHIFTS:
        return True

    def _licz_z_kierunku(kierunek: int) -> int:
        """Liczy kolejne robocze niedziele w zadanym kierunku (±1 tygodnia)."""
        licznik = 0
        for n in range(1, 4):
            nd = data + datetime.timedelta(weeks=n * kierunek)
            # Poza zakresem bieżącego miesiąca – przerywamy (brak danych = wolne)
            if nd.month != miesiac or nd.year != rok:
                break
            if przydzial.get(nd, "") in WORKING_SHIFTS:
                licznik += 1
            else:
                break
        return licznik

    seria = _licz_z_kierunku(-1) + 1 + _licz_z_kierunku(+1)
    return seria <= 3


# Ograniczenie 3b: seria nocek i odpoczynek po niej

def sprawdz_kolejne_noce(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    max_noce: int = MAX_KOLEJNYCH_NOCY,
    dni_wolne: int = DNI_WOLNE_PO_NOCACH,
) -> bool:
    """
    Pilnuje rytmu nocek: najwyżej `max_noce` nocy pod rząd, a po serii nocy
    co najmniej `dni_wolne` dni bez pracy.

    Sama reguła 12h przerwy tego NIE zapewnia: nocka kończy się o 7:00, a kolejna
    zaczyna o 19:00, czyli dokładnie 720 minut później – warunek przechodzi i seria
    nocek może rosnąć bez końca.

    Sprawdzanie jest dwukierunkowe, bo fazy uzupełniające wstawiają dyżury także
    PRZED już przydzielonymi i zbudowałyby zakazaną serię „od tyłu" (tak samo jak
    przy regule co 4. niedzieli).

    Oceniamy wyłącznie naruszenia, które wprowadza `nowy_kod` – wcześniejsze
    kolizje w innym miejscu grafiku nie mogą blokować poprawnych przydziałów.

    Dni spoza bieżącego miesiąca są traktowane jak wolne (brak danych), więc seria
    przechodząca przez granicę miesiąca jest niewidoczna – to samo ograniczenie
    dotyczy reguły niedzielnej.
    """
    if nowy_kod not in WORKING_SHIFTS:
        return True

    def kod_dnia(d: datetime.date) -> str:
        return nowy_kod if d == data else przydzial.get(d, "")

    def jest_noca(d: datetime.date) -> bool:
        return kod_dnia(d) in NIGHT_SHIFTS

    dzien = datetime.timedelta(days=1)

    if jest_noca(data):
        # 1. Długość serii nocy, do której należy nowy dyżur.
        #    Szukamy jej granic w obie strony – wystarczy zajrzeć o `max_noce`
        #    dni dalej, bo dłuższa seria i tak dyskwalifikuje przydział.
        poczatek = data
        for _ in range(max_noce):
            if not jest_noca(poczatek - dzien):
                break
            poczatek -= dzien
        koniec = data
        for _ in range(max_noce):
            if not jest_noca(koniec + dzien):
                break
            koniec += dzien

        if (koniec - poczatek).days + 1 > max_noce or jest_noca(poczatek - dzien) or jest_noca(koniec + dzien):
            return False

        # 2. Po serii nocy muszą nastąpić dni wolne. Sprawdzenie W PRZÓD jest
        #    konieczne, bo fazy uzupełniające dostawiają nocki PRZED dyżurami,
        #    które już stoją w grafiku – naruszenie powstawałoby „od tyłu".
        for odstep in range(1, dni_wolne + 1):
            if kod_dnia(koniec + dzien * odstep) in WORKING_SHIFTS:
                return False

    # 3. Czy nowy dyżur nie wypada w dniach odpoczynku po wcześniejszej serii nocy.
    #    Warunek `not jest_noca(d + dzien)` odsiewa sytuację, w której nowy dyżur
    #    jest po prostu kolejną nocą tej samej serii – ten przypadek ocenia punkt 1.
    for odstep in range(1, dni_wolne + 1):
        wczesniej = data - dzien * odstep
        if jest_noca(wczesniej) and not jest_noca(wczesniej + dzien):
            return False

    return True


# Ograniczenie 4: niedyspozycje pracownika

def sprawdz_niedyspozycje(
    pracownik: Pracownik,
    data: datetime.date,
) -> bool:
    """
    Zwraca True, jeśli pracownik jest tego dnia dostępny.

    Blokuje zarówno niedyspozycje, jak i dni urlopu. Urlopy trzymamy w osobnym
    polu, bo niosą liczbę godzin i muszą być rozróżnialne w raportach – ale dla
    przydziału dyżuru skutek jest ten sam: tego dnia pracownik nie pracuje.
    """
    if data in pracownik.niedyspozycje:
        return False
    return data not in pracownik.absencje


# Ograniczenie 5: bilans godzin (etatowcy nie mogą mieć nadgodzin)

def sprawdz_bilans_bez_nadgodzin(
    przepracowane_minuty: int,
    normatyw_minuty: int,
    nowy_kod: str,
    koncowka_minuty: int = 0,
) -> bool:
    """
    Dla etatowców: sprawdza, czy dodanie nowej zmiany nie spowoduje
    przekroczenia normatywu (nadgodzin).

    Zwraca True, jeśli po dodaniu zmiany bilans <= 0 (normatyw nie przekroczony).
    """
    nowe_minuty = _get_shift_minutes(nowy_kod, koncowka_minuty)
    return (przepracowane_minuty + nowe_minuty) <= normatyw_minuty


# Ograniczenie 6: pracownik nie pracuje w weekendy (flaga)

def sprawdz_weekendy(
    pracownik: Pracownik,
    data: datetime.date,
    nowy_kod: str,
) -> bool:
    """
    Jeśli pracownik ma flagę pracuje_w_weekendy=False i data jest weekendem,
    zmiana robocza jest niedozwolona.
    """
    if nowy_kod not in WORKING_SHIFTS:
        return True
    if data.weekday() >= 5 and not pracownik.pracuje_w_weekendy:
        return False
    return True


# Zbiorcza walidacja wszystkich ograniczeń

def czy_mozna_przydzielic(
    pracownik: Pracownik,
    data: datetime.date,
    nowy_kod: str,
    przydzial: Dict[datetime.date, str],
    przepracowane_minuty: int,
    normatyw_minuty: int,
    koncowka_minuty: int = 0,
    rok: int = 0,
    miesiac: int = 0,
) -> bool:
    """
    Sprawdza wszystkie ograniczenia twarde i zwraca True tylko wtedy,
    gdy zmiana 'nowy_kod' może zostać przydzielona pracownikowi w danym dniu.
    """
    # Niedyspozycja
    if not sprawdz_niedyspozycje(pracownik, data):
        return False

    # Czy już ma przydzieloną zmianę w ten dzień
    if przydzial.get(data, "") in WORKING_SHIFTS:
        return False

    # Nie może pracować w weekendy
    if not sprawdz_weekendy(pracownik, data, nowy_kod):
        return False

    # Minimalna przerwa 12h (wstecz i wprzód)
    if not sprawdz_przerwe_12h(przydzial, data, nowy_kod, koncowka_minuty):
        return False
    if not sprawdz_przerwe_12h_nastepna(przydzial, data, nowy_kod, koncowka_minuty):
        return False

    # Rytm nocek: maks. 2 pod rząd, potem 2 dni wolne
    if not sprawdz_kolejne_noce(przydzial, data, nowy_kod):
        return False

    # Limit 36h/tydzień jest ograniczeniem miękkim (uśrednienie 40h w okresie rozliczeniowym) – realizowanym przez scoring S6 w scheduler.py.
    # Twarde pozostaje wyłącznie nieprzekroczenie normatywu miesięcznego.

    # Bilans bez nadgodzin (tylko etatowcy)
    if pracownik.is_etat:
        if not sprawdz_bilans_bez_nadgodzin(
            przepracowane_minuty, normatyw_minuty, nowy_kod, koncowka_minuty
        ):
            return False

    # Co 4. niedziela wolna
    if rok and miesiac:
        if not sprawdz_co_4_niedziela(przydzial, data, nowy_kod, rok, miesiac):
            return False

    return True


def czy_mozna_przydzielic_awaryjnie(
    przydzial: Dict[datetime.date, str],
    data: datetime.date,
    nowy_kod: str,
    koncowka_minuty: int = 0,
    rok: int = 0,
    miesiac: int = 0,
) -> bool:
    """
    Zestaw reguł dla fazy awaryjnej, która domyka dni bez żadnej obsady.

    Faza ta świadomie pomija limit normatywu (dopuszcza nadgodziny), ale reguły
    dotyczące bezpieczeństwa pracy muszą obowiązywać zawsze. Trzymamy je tutaj,
    w jednym miejscu, żeby nie dało się dopisać nowej reguły do głównej bramki
    i przeoczyć tej ścieżki – dokładnie tak powstała luka z seriami nocek.
    """
    if not sprawdz_przerwe_12h(przydzial, data, nowy_kod, koncowka_minuty):
        return False
    if not sprawdz_przerwe_12h_nastepna(przydzial, data, nowy_kod, koncowka_minuty):
        return False
    if not sprawdz_kolejne_noce(przydzial, data, nowy_kod):
        return False
    if rok and miesiac:
        if not sprawdz_co_4_niedziela(przydzial, data, nowy_kod, rok, miesiac):
            return False
    return True
