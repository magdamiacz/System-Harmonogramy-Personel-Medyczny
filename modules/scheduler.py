# modules/scheduler.py
# Algorytm zachłanny generowania harmonogramu pracy.
#
# Fazy działania:
#   1. Przydziel zmiany R pracownikom z flagą tylko_7h (każdy dzień roboczy)
#   2. Przydziel zmiany DN/D/N pracownikom na kontraktach (preferuj 24h)
#   3. Przydziel zmiany D i N etatowcom zmianowym
#   4. Uzupełnij końcówki DK tam, gdzie etatowiec nie dobił normatywu
#   5. Zweryfikuj pokrycie obsady (loguj braki)

import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from config import (
    FULL_SHIFT_MINUTES,
    MIN_HOURS_DUZY_KONTRAKT,
    MIN_HOURS_MALY_KONTRAKT,
    STAFFING_NORMS,
    WORK_MINUTES_PER_DAY_STANDARD,
    WORKING_SHIFTS,
)
from modules.constraints import czy_mozna_przydzielic
from modules.data_loader import Pracownik
from modules.holidays import czy_niedziela, czy_swieto, czy_weekend
from modules.normative import Normatyw, oblicz_normatywy


# ---------------------------------------------------------------------------
# Typy pomocnicze
# ---------------------------------------------------------------------------

# Przydział: {imie_nazwisko: {data: kod_zmiany}}
ScheduleDict = Dict[str, Dict[datetime.date, str]]

# Przepracowane minuty: {imie_nazwisko: int}
WorkedMinutes = Dict[str, int]


# ---------------------------------------------------------------------------
# Stan harmonogramu w trakcie generowania
# ---------------------------------------------------------------------------

class HarmonogramState:
    """
    Przechowuje bieżący stan generowania harmonogramu dla jednej grupy
    pracowników (np. gastro_piel).
    """

    def __init__(
        self,
        pracownicy: List[Pracownik],
        normatywy: Dict[str, Normatyw],
        dni: List[datetime.date],
        swieta: Set[datetime.date],
    ):
        self.pracownicy = pracownicy
        self.normatywy = normatywy
        self.dni = dni
        self.swieta = swieta

        # Przydzielone zmiany: {imie: {data: kod}}
        self.przydzial: ScheduleDict = {p.imie_nazwisko: {} for p in pracownicy}

        # Przepracowane minuty per pracownik
        self.przepracowane: WorkedMinutes = {p.imie_nazwisko: 0 for p in pracownicy}

        # Liczniki do balansowania
        self.liczba_nocnych: Dict[str, int] = {p.imie_nazwisko: 0 for p in pracownicy}
        self.liczba_weekendowych: Dict[str, int] = {p.imie_nazwisko: 0 for p in pracownicy}
        self.liczba_swiatecznych: Dict[str, int] = {p.imie_nazwisko: 0 for p in pracownicy}
        self.liczba_dziennych: Dict[str, int] = {p.imie_nazwisko: 0 for p in pracownicy}

    def przydziel(self, imie: str, data: datetime.date, kod: str) -> None:
        """Przydziela zmianę i aktualizuje liczniki."""
        normatyw = self.normatywy[imie]
        self.przydzial[imie][data] = kod

        # Minuty
        if kod == "DK":
            minuty = normatyw.koncowka_minuty
        elif kod == "R":
            minuty = WORK_MINUTES_PER_DAY_STANDARD
        elif kod == "D":
            minuty = FULL_SHIFT_MINUTES
        elif kod == "N":
            minuty = FULL_SHIFT_MINUTES
        elif kod == "DN":
            minuty = 24 * 60
        else:
            minuty = 0
        self.przepracowane[imie] += minuty

        # Liczniki specjalne
        if kod in ("N", "DN"):
            self.liczba_nocnych[imie] += 1
        if kod in ("D", "N", "DN", "R", "DK"):
            if czy_weekend(data):
                self.liczba_weekendowych[imie] += 1
            if czy_swieto(data, self.swieta):
                self.liczba_swiatecznych[imie] += 1
            if kod in ("D", "DN"):
                self.liczba_dziennych[imie] += 1

    def get_przydzial(self, imie: str, data: datetime.date) -> str:
        return self.przydzial[imie].get(data, "")

    def pozostale_minuty(self, imie: str) -> int:
        """Ile minut brakuje do normatywu."""
        return max(0, self.normatywy[imie].minuty - self.przepracowane[imie])

    def liczba_na_dzien(self, data: datetime.date, typ: str) -> int:
        """
        Liczy ile osób ma danego dnia zmianę danego typu.
        typ: "D" (D+DN), "N" (N+DN), "R"
        """
        if typ == "D":
            return sum(
                1 for p in self.pracownicy
                if self.get_przydzial(p.imie_nazwisko, data) in ("D", "DN")
            )
        if typ == "N":
            return sum(
                1 for p in self.pracownicy
                if self.get_przydzial(p.imie_nazwisko, data) in ("N", "DN")
            )
        if typ == "R":
            return sum(
                1 for p in self.pracownicy
                if self.get_przydzial(p.imie_nazwisko, data) == "R"
            )
        return 0


# ---------------------------------------------------------------------------
# Funkcja scoring pracowników (zachłanna heurystyka)
# ---------------------------------------------------------------------------

def score_pracownik(
    p: Pracownik,
    data: datetime.date,
    kod: str,
    state: HarmonogramState,
) -> float:
    """
    Oblicza wynik (im wyższy, tym bardziej pożądany do przydziału).
    Kryteria zachłanne:
      +10  za każde 12h brakujących do normatywu (priorytet dla tych, co mają braki)
      -5   za każdy dyżur nocny powyżej średniej (balansowanie nocy)
      -3   za każdy dyżur weekendowy powyżej średniej
      -3   za każdy dyżur świąteczny powyżej średniej
      -100 (weto) jeśli ograniczenia twarde nie są spełnione
    """
    imie = p.imie_nazwisko
    normatyw = state.normatywy[imie]

    # Sprawdź ograniczenia twarde – jeśli niespełnione, wynik jest -inf
    if not czy_mozna_przydzielic(
        pracownik=p,
        data=data,
        nowy_kod=kod,
        przydzial=state.przydzial[imie],
        przepracowane_minuty=state.przepracowane[imie],
        normatyw_minuty=normatyw.minuty,
        koncowka_minuty=normatyw.koncowka_minuty,
        rok=data.year,
        miesiac=data.month,
    ):
        return float("-inf")

    score = 0.0
    n = len(state.pracownicy)

    # Priorytet: im więcej brakuje do normatywu, tym wyższy priorytet
    brakujace_12h_bloki = state.pozostale_minuty(imie) / FULL_SHIFT_MINUTES
    score += brakujace_12h_bloki * 10

    # Balansowanie nocy
    if n > 1:
        avg_nocne = sum(state.liczba_nocnych.values()) / n
        score -= max(0, state.liczba_nocnych[imie] - avg_nocne) * 5

    # Balansowanie weekendów
    if n > 1:
        avg_weekend = sum(state.liczba_weekendowych.values()) / n
        score -= max(0, state.liczba_weekendowych[imie] - avg_weekend) * 3

    # Balansowanie świąt
    if n > 1:
        avg_swiata = sum(state.liczba_swiatecznych.values()) / n
        score -= max(0, state.liczba_swiatecznych[imie] - avg_swiata) * 3

    return score


# ---------------------------------------------------------------------------
# Faza 1: Zmiany R (7h35) dla pracowników tylko_7h
# ---------------------------------------------------------------------------

def faza_1_r_shifts(state: HarmonogramState) -> None:
    """
    Przydziela zmiany R w każdy dzień roboczy (pn-pt, nie święto)
    pracownikom z flagą tylko_7h.
    """
    pracownicy_r = [p for p in state.pracownicy if p.tylko_7h]
    if not pracownicy_r:
        return

    for data in state.dni:
        # Zmiany R tylko w dni robocze (pn-pt, nie święto)
        if data.weekday() >= 5:
            continue
        if czy_swieto(data, state.swieta):
            continue

        for p in pracownicy_r:
            imie = p.imie_nazwisko
            normatyw = state.normatywy[imie]

            # Nie przydzielaj jeśli już ma zmianę lub nie ma czasu do normatywu
            if state.get_przydzial(imie, data) != "":
                continue
            if state.przepracowane[imie] >= normatyw.minuty:
                continue

            # Sprawdź ograniczenia
            if czy_mozna_przydzielic(
                pracownik=p,
                data=data,
                nowy_kod="R",
                przydzial=state.przydzial[imie],
                przepracowane_minuty=state.przepracowane[imie],
                normatyw_minuty=normatyw.minuty,
                koncowka_minuty=normatyw.koncowka_minuty,
                rok=data.year,
                miesiac=data.month,
            ):
                state.przydziel(imie, data, "R")


# ---------------------------------------------------------------------------
# Faza 2: Kontrakty (DN preferowane, potem D/N)
# ---------------------------------------------------------------------------

def faza_2_kontrakty(
    state: HarmonogramState,
    norm: object,  # DailyStaffingNorm
) -> None:
    """
    Przydziela zmiany pracownikom na kontraktach.
    Preferuje dyżury 24h (DN), ale akceptuje też D lub N.
    Przestrzega limitu obsady na dobę (max_*) – bez tłumów.
    """
    kontrakty = [p for p in state.pracownicy if p.is_kontrakt and not p.tylko_7h]
    if not kontrakty:
        return

    max_d = _get_max_shifts(norm, "D")
    max_n = _get_max_shifts(norm, "N")

    for p in kontrakty:
        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]

        # Dni posortowane po obsadzie (rosnąco) – rozkład zamiast tłumów
        dni_posortowane = sorted(
            state.dni,
            key=lambda d: (state.liczba_na_dzien(d, "D") + state.liczba_na_dzien(d, "N")),
        )

        for data in dni_posortowane:
            if state.przepracowane[imie] >= normatyw.minuty:
                break

            if state.get_przydzial(imie, data) != "":
                continue

            if data.weekday() >= 5 and not p.pracuje_w_weekendy:
                continue

            obs_d = state.liczba_na_dzien(data, "D")
            obs_n = state.liczba_na_dzien(data, "N")

            for kod in ("DN", "D", "N"):
                # DN zajmuje slot D i N – oba muszą mieć miejsce
                if kod == "DN" and (obs_d >= max_d or obs_n >= max_n):
                    continue
                if kod == "D" and obs_d >= max_d:
                    continue
                if kod == "N" and obs_n >= max_n:
                    continue
                if czy_mozna_przydzielic(
                    pracownik=p,
                    data=data,
                    nowy_kod=kod,
                    przydzial=state.przydzial[imie],
                    przepracowane_minuty=state.przepracowane[imie],
                    normatyw_minuty=normatyw.minuty * 2,
                    koncowka_minuty=normatyw.koncowka_minuty,
                    rok=data.year,
                    miesiac=data.month,
                ):
                    state.przydziel(imie, data, kod)
                    break


# ---------------------------------------------------------------------------
# Faza 3: Obsada oddziału – etatowcy zmianowi (D i N)
# ---------------------------------------------------------------------------

def faza_3_obsada(
    state: HarmonogramState,
    norm: object,  # DailyStaffingNorm
) -> None:
    """
    Dla każdego dnia miesiąca sprawdza brakującą obsadę (D/N)
    i zachłannie przydziela etatowcom najlepiej pasującego pracownika.
    """
    etatowcy = [p for p in state.pracownicy if p.is_etat and not p.tylko_7h]
    if not etatowcy:
        return

    for data in state.dni:
        # Policz aktualną obsadę D i N (łącznie z kontraktami)
        obsada_d = sum(
            1 for p in state.pracownicy
            if state.get_przydzial(p.imie_nazwisko, data) in ("D", "DN")
        )
        obsada_n = sum(
            1 for p in state.pracownicy
            if state.get_przydzial(p.imie_nazwisko, data) in ("N", "DN")
        )

        brak_d = max(0, norm.day_shifts - obsada_d)
        brak_n = max(0, norm.night_shifts - obsada_n)

        # Przydziel brakujące D
        for _ in range(brak_d):
            kandydaci = [
                (score_pracownik(p, data, "D", state), p)
                for p in etatowcy
                if state.get_przydzial(p.imie_nazwisko, data) == ""
            ]
            kandydaci = [(s, p) for s, p in kandydaci if s > float("-inf")]
            if not kandydaci:
                break
            kandydaci.sort(key=lambda x: x[0], reverse=True)
            _, najlepszy = kandydaci[0]
            state.przydziel(najlepszy.imie_nazwisko, data, "D")

        # Przydziel brakujące N
        for _ in range(brak_n):
            kandydaci = [
                (score_pracownik(p, data, "N", state), p)
                for p in etatowcy
                if state.get_przydzial(p.imie_nazwisko, data) == ""
            ]
            kandydaci = [(s, p) for s, p in kandydaci if s > float("-inf")]
            if not kandydaci:
                break
            kandydaci.sort(key=lambda x: x[0], reverse=True)
            _, najlepszy = kandydaci[0]
            state.przydziel(najlepszy.imie_nazwisko, data, "N")


# ---------------------------------------------------------------------------
# Faza 3b: Uzupełnianie niedoborów etatowców ponad minimum obsady
# ---------------------------------------------------------------------------

def _get_max_shifts(norm, typ: str) -> int:
    """Zwraca maksymalną liczbę zmian danego typu na dobę (limit przeciw tłumom)."""
    if typ == "D":
        return norm.max_day_shifts if norm.max_day_shifts > 0 else norm.day_shifts + 1
    if typ == "N":
        return norm.max_night_shifts if norm.max_night_shifts > 0 else norm.night_shifts + 1
    return norm.max_r_shifts if norm.max_r_shifts > 0 else norm.r_shifts


def faza_3b_uzupelnianie(
    state: HarmonogramState,
    norm: object,  # DailyStaffingNorm
) -> None:
    """
    Po wypełnieniu minimalnej normy obsady, część etatowców zmianowych
    może wciąż mieć niedobór godzin. Ta faza przydziela dodatkowe D lub N,
    PRZESTRZEGAJĄC LIMITU OBSADY NA DOBĘ (max_*), aby uniknąć tłumów.
    Nadwyżkowe zmiany są ROZKŁADANE na dni z mniejszą obsadą.
    """
    etatowcy = [p for p in state.pracownicy if p.is_etat and not p.tylko_7h]
    if not etatowcy:
        return

    max_d = _get_max_shifts(norm, "D")
    max_n = _get_max_shifts(norm, "N")

    zmiana_nastapila = True
    while zmiana_nastapila:
        zmiana_nastapila = False

        for p in etatowcy:
            imie = p.imie_nazwisko
            normatyw = state.normatywy[imie]

            if state.pozostale_minuty(imie) < FULL_SHIFT_MINUTES:
                continue

            # Zbierz dni, gdzie pracownik może dostać D lub N, z posortowaniem
            # po aktualnej obsadzie (rosnąco) – preferuj dni z mniejszą obsadą
            kandydaci_d = []
            kandydaci_n = []
            for data in state.dni:
                if state.get_przydzial(imie, data) != "":
                    continue
                obs_d = state.liczba_na_dzien(data, "D")
                obs_n = state.liczba_na_dzien(data, "N")
                if obs_d < max_d and czy_mozna_przydzielic(
                    p, data, "D",
                    state.przydzial[imie], state.przepracowane[imie],
                    normatyw.minuty, normatyw.koncowka_minuty,
                    data.year, data.month,
                ):
                    kandydaci_d.append((obs_d, data))
                if obs_n < max_n and czy_mozna_przydzielic(
                    p, data, "N",
                    state.przydzial[imie], state.przepracowane[imie],
                    normatyw.minuty, normatyw.koncowka_minuty,
                    data.year, data.month,
                ):
                    kandydaci_n.append((obs_n, data))

            # Sortuj: dni z mniejszą obsadą pierwsze (rozkład zamiast tłumów)
            kandydaci_d.sort(key=lambda x: x[0])
            kandydaci_n.sort(key=lambda x: x[0])

            for kod, kandydaci in (("D", kandydaci_d), ("N", kandydaci_n)):
                if not kandydaci:
                    continue
                _, data = kandydaci[0]
                state.przydziel(imie, data, kod)
                zmiana_nastapila = True
                break

            if state.pozostale_minuty(imie) < FULL_SHIFT_MINUTES:
                continue


# ---------------------------------------------------------------------------
# Faza 4: Końcówki DK
# ---------------------------------------------------------------------------

def faza_4_koncowki(
    state: HarmonogramState,
) -> None:
    """
    Dla etatowców zmianowych, którzy po przydziale D/N mają niedobór godzin
    mniejszy niż 12h (bo normatyw nie jest wielokrotnością 12h),
    dodaje końcówkę DK w pierwszym wolnym dniu roboczym.
    """
    for p in state.pracownicy:
        if not p.is_etat or p.tylko_7h:
            continue

        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]

        # Brak końcówki – normatyw jest dokładną wielokrotnością 12h
        if normatyw.koncowka_minuty == 0:
            continue

        # Jeśli już nie ma niedoboru, DK niepotrzebna
        if state.przepracowane[imie] >= normatyw.minuty:
            continue

        # Szukaj pierwszego wolnego dnia roboczego
        for data in state.dni:
            if data.weekday() >= 5:
                continue
            if czy_swieto(data, state.swieta):
                continue
            if state.get_przydzial(imie, data) != "":
                continue

            # Sprawdź przerwe 12h przed DK
            if czy_mozna_przydzielic(
                pracownik=p,
                data=data,
                nowy_kod="DK",
                przydzial=state.przydzial[imie],
                przepracowane_minuty=state.przepracowane[imie],
                normatyw_minuty=normatyw.minuty,
                koncowka_minuty=normatyw.koncowka_minuty,
                rok=data.year,
                miesiac=data.month,
            ):
                state.przydziel(imie, data, "DK")
                break


# ---------------------------------------------------------------------------
# Główna funkcja generowania harmonogramu dla jednej grupy
# ---------------------------------------------------------------------------

def generuj_harmonogram_grupy(
    pracownicy: List[Pracownik],
    schedule_key: str,
    rok: int,
    miesiac: int,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    liczba_dni_roboczych: int,
) -> HarmonogramState:
    """
    Generuje harmonogram dla jednej grupy pracowników (np. gastro_piel).

    Parametry:
        pracownicy:          lista pracowników w tej grupie
        schedule_key:        klucz harmonogramu
        rok, miesiac:        okres
        dni:                 lista wszystkich dat w miesiącu
        swieta:              zbiór świąt w danym roku
        liczba_dni_roboczych: liczba dni roboczych w miesiącu

    Zwraca HarmonogramState z uzupełnionym przydziałem.
    """
    from modules.normative import oblicz_normatywy

    normatywy = oblicz_normatywy(pracownicy, liczba_dni_roboczych)
    norm = STAFFING_NORMS[schedule_key]
    state = HarmonogramState(pracownicy, normatywy, dni, swieta)

    # Faza 1: R-shifts dla pracowników tylko_7h
    faza_1_r_shifts(state)

    # Faza 2: Kontrakty
    faza_2_kontrakty(state, norm)

    # Faza 3: Obsada D/N etatowców (minimalna norma obsady)
    faza_3_obsada(state, norm)

    # Faza 3b: Uzupełnianie niedoborów – z limitem obsady na dobę (bez tłumów)
    faza_3b_uzupelnianie(state, norm)

    # Faza 4: Końcówki DK
    faza_4_koncowki(state)

    return state


# ---------------------------------------------------------------------------
# Generowanie wszystkich 5 harmonogramów naraz
# ---------------------------------------------------------------------------

def generuj_wszystkie_harmonogramy(
    grupy: Dict[str, List[Pracownik]],
    rok: int,
    miesiac: int,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    liczba_dni_roboczych: int,
) -> Dict[str, HarmonogramState]:
    """
    Generuje harmonogramy dla wszystkich grup pracowników.

    Parametry:
        grupy: {schedule_key: [pracownicy]}

    Zwraca: {schedule_key: HarmonogramState}
    """
    wyniki = {}
    for key, pracownicy in grupy.items():
        if not pracownicy:
            continue
        wyniki[key] = generuj_harmonogram_grupy(
            pracownicy=pracownicy,
            schedule_key=key,
            rok=rok,
            miesiac=miesiac,
            dni=dni,
            swieta=swieta,
            liczba_dni_roboczych=liczba_dni_roboczych,
        )
    return wyniki


# ---------------------------------------------------------------------------
# Obliczanie podsumowania dla harmonogramu
# ---------------------------------------------------------------------------

def oblicz_podsumowanie(
    state: HarmonogramState,
    swieta: Set[datetime.date],
) -> List[dict]:
    """
    Oblicza podsumowanie dla każdego pracownika w harmonogramie.
    Zwraca listę słowników gotowych do wyświetlenia w tabeli.
    """
    from modules.normative import minuty_na_godziny_float, _minuty_na_str

    wyniki = []
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]

        przeprac = state.przepracowane[imie]
        bilans = przeprac - normatyw.minuty

        # Dla kontraktów "ponad minimum" to nie są nadgodziny, lecz nadwyżka dozwolona
        if bilans > 0:
            if p.is_kontrakt:
                bilans_str = f"+{_minuty_na_str(bilans)} (ponad min)"
            else:
                bilans_str = f"+{_minuty_na_str(bilans)} (nadgodziny!)"
        elif bilans < 0:
            bilans_str = f"-{_minuty_na_str(abs(bilans))} (niedobór)"
        else:
            bilans_str = "0h (OK)"

        wyniki.append({
            "Imię i nazwisko": imie,
            "Typ umowy": p.typ_umowy,
            "Normatyw": _minuty_na_str(normatyw.minuty),
            "Przepracowane": _minuty_na_str(przeprac),
            "Bilans": bilans_str,
            "Bilans_min": bilans,
            "Dyżury dzienne": state.liczba_dziennych[imie],
            "Dyżury nocne": state.liczba_nocnych[imie],
            "Dyżury weekendowe": state.liczba_weekendowych[imie],
            "Dyżury świąteczne": state.liczba_swiatecznych[imie],
        })
    return wyniki
