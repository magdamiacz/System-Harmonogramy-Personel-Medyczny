# Algorytm zachłanny generowania harmonogramu pracy.
#
# Fazy działania:
#   1. Przydziel zmiany R pracownikom z flagą tylko_7h (każdy dzień roboczy)
#   2. Przydziel zmiany DN/D/N pracownikom na kontraktach (preferuj 24h)
#   3. Przydziel zmiany D i N etatowcom zmianowym (minimalna norma obsady)
#   3b. Uzupełnij niedobory godzin etatowców (z limitem obsady na dobę)
#   4. Uzupełnij końcówki DK
#   5. Awaryjnie uzupełnij dni bez obsady

import datetime
from typing import Dict, List, Set

from config import (
    FULL_SHIFT_MINUTES,
    MAX_WEEKLY_MINUTES_ETAT,
    STAFFING_NORMS,
    WORK_MINUTES_PER_DAY_STANDARD,
    WORKING_SHIFTS,
)
from modules.absences import suma_minut_absencji
from modules.constraints import (
    czy_mozna_przydzielic,
    czy_mozna_przydzielic_awaryjnie,
    oblicz_godziny_tygodnia,
)
from modules.data_loader import Pracownik
from modules.holidays import czy_swieto, czy_weekend
from modules.normative import Normatyw, oblicz_normatywy

# Minuty na zmianę (DK obsługiwane osobno – długość indywidualna)
_MINUTY_ZMIANY: Dict[str, int] = {
    "R":  WORK_MINUTES_PER_DAY_STANDARD,
    "D":  FULL_SHIFT_MINUTES,
    "N":  FULL_SHIFT_MINUTES,
    "DN": 24 * 60,
}

# Zbiory kodów liczące się jako dany typ obsady
_KODY_OBSADY: Dict[str, set] = {
    "D": {"D", "DN"},
    "N": {"N", "DN"},
    "R": {"R"},
}

# Stan harmonogramu

class HarmonogramState:
    """Bieżący stan generowania harmonogramu dla jednej grupy pracowników."""

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

        names = [p.imie_nazwisko for p in pracownicy]
        self.przydzial:          Dict[str, Dict[datetime.date, str]] = {n: {} for n in names}
        self.przepracowane:      Dict[str, int] = {n: 0 for n in names}
        self.liczba_nocnych:     Dict[str, int] = {n: 0 for n in names}
        self.liczba_weekendowych:Dict[str, int] = {n: 0 for n in names}
        self.liczba_swiatecznych:Dict[str, int] = {n: 0 for n in names}
        self.liczba_dziennych:   Dict[str, int] = {n: 0 for n in names}

    def przydziel(self, imie: str, data: datetime.date, kod: str) -> None:
        """Przydziela zmianę i aktualizuje liczniki."""
        self.przydzial[imie][data] = kod
        normatyw = self.normatywy[imie]
        minuty = normatyw.koncowka_minuty if kod == "DK" else _MINUTY_ZMIANY.get(kod, 0)
        self.przepracowane[imie] += minuty

        if kod in WORKING_SHIFTS:
            if kod in ("N", "DN"):
                self.liczba_nocnych[imie] += 1
            if czy_weekend(data):
                self.liczba_weekendowych[imie] += 1
            if czy_swieto(data, self.swieta):
                self.liczba_swiatecznych[imie] += 1
            if kod in ("D", "DN"):
                self.liczba_dziennych[imie] += 1

    def get_przydzial(self, imie: str, data: datetime.date) -> str:
        return self.przydzial[imie].get(data, "")

    def pozostale_minuty(self, imie: str) -> int:
        return max(0, self.normatywy[imie].minuty - self.przepracowane[imie])

    def liczba_na_dzien(self, data: datetime.date, typ: str) -> int:
        """Ile osób ma danego dnia zmianę danego typu (D=D+DN, N=N+DN, R=R)."""
        kody = _KODY_OBSADY.get(typ, set())
        return sum(1 for p in self.pracownicy if self.get_przydzial(p.imie_nazwisko, data) in kody)


# Pomocniki rozkładu zmian

def _rozmiar_luki_pracownika(imie: str, data: datetime.date, state: HarmonogramState) -> int:
    """Rozmiar luki (dni) między zmianami pracownika, w którą wpada data."""
    dni_pracy = sorted(d for d, k in state.przydzial[imie].items() if k in WORKING_SHIFTS)
    if not dni_pracy:
        return len(state.dni)
    pierwszy, ostatni = state.dni[0], state.dni[-1]
    if data < dni_pracy[0]:
        return (dni_pracy[0] - pierwszy).days
    if data > dni_pracy[-1]:
        return (ostatni - dni_pracy[-1]).days
    for i in range(len(dni_pracy) - 1):
        if dni_pracy[i] < data < dni_pracy[i + 1]:
            return (dni_pracy[i + 1] - dni_pracy[i]).days - 1
    return 0


def _dni_od_ostatniej_zmiany(imie: str, data: datetime.date, state: HarmonogramState) -> int:
    """Ile dni minęło od ostatniej zmiany pracownika (lub od początku miesiąca)."""
    dni_pracy = [d for d, k in state.przydzial[imie].items() if k in WORKING_SHIFTS]
    przed = [d for d in dni_pracy if d < data]
    return (data - (max(przed) if przed else state.dni[0])).days


# Funkcja scoring

def score_pracownik(p: Pracownik, data: datetime.date, kod: str, state: HarmonogramState) -> float:
    """Wynik zachłanny – im wyższy, tym pracownik bardziej pożądany do przydziału."""
    imie = p.imie_nazwisko
    normatyw = state.normatywy[imie]

    if not czy_mozna_przydzielic(
        pracownik=p, data=data, nowy_kod=kod,
        przydzial=state.przydzial[imie],
        przepracowane_minuty=state.przepracowane[imie],
        normatyw_minuty=normatyw.minuty,
        koncowka_minuty=normatyw.koncowka_minuty,
        rok=data.year, miesiac=data.month,
    ):
        return float("-inf")

    score = 0.0
    n = len(state.pracownicy)

    # S1: priorytet niedoboru godzin
    score += (state.pozostale_minuty(imie) / FULL_SHIFT_MINUTES) * 10

    # S2–S4: balansowanie nocy / weekendów / świąt
    if n > 1:
        for liczniki, waga in (
            (state.liczba_nocnych,      5),
            (state.liczba_weekendowych, 3),
            (state.liczba_swiatecznych, 3),
        ):
            avg = sum(liczniki.values()) / n
            score -= max(0, liczniki[imie] - avg) * waga

    # S5: bonus za przerwę od ostatniej zmiany (równomierne rozłożenie)
    score += min(_dni_od_ostatniej_zmiany(imie, data, state), 7) * 2

    # S6: kara gdy ta zmiana wyczerpuje tydzień (tylko etatowcy zmianowi)
    if p.is_etat and not p.tylko_7h:
        weekly_used = oblicz_godziny_tygodnia(state.przydzial[imie], data, normatyw.koncowka_minuty)
        if MAX_WEEKLY_MINUTES_ETAT - weekly_used - FULL_SHIFT_MINUTES < FULL_SHIFT_MINUTES:
            score -= 15

    # S7: kara za blokowanie rotacji niedzielnej
    if data.weekday() == 6:
        w1 = state.get_przydzial(imie, data - datetime.timedelta(weeks=1)) in WORKING_SHIFTS
        w2 = state.get_przydzial(imie, data - datetime.timedelta(weeks=2)) in WORKING_SHIFTS
        if w1 and w2 and (data + datetime.timedelta(weeks=1)) in state.dni:
            score -= 500

    return score


# Faza 0: Urlopy wpisane z góry

def faza_0_absencje(state: HarmonogramState) -> None:
    """Wpisuje urlopy do grafiku, zanim algorytm zacznie przydzielać dyżury.

    Kody urlopowe nie należą do WORKING_SHIFTS, więc nie dokładają minut do
    przepracowanych – godziny urlopu zostały już odliczone od normatywu.
    Wpisanie ich tutaj sprawia, że dzień jest zajęty i żadna faza go nie nadpisze.
    """
    dni_miesiaca = set(state.dni)
    for p in state.pracownicy:
        for data, kod in p.absencje.items():
            if data in dni_miesiaca:
                state.przydziel(p.imie_nazwisko, data, kod)


# Faza 1: Zmiany R dla pracowników tylko_7h

def faza_1_r_shifts(state: HarmonogramState) -> None:
    """Przydziela R w każdy dzień roboczy pracownikom z flagą tylko_7h."""
    pracownicy_r = [p for p in state.pracownicy if p.tylko_7h]
    if not pracownicy_r:
        return
    for data in state.dni:
        if data.weekday() >= 5 or czy_swieto(data, state.swieta):
            continue
        for p in pracownicy_r:
            imie = p.imie_nazwisko
            normatyw = state.normatywy[imie]
            if state.get_przydzial(imie, data) != "":
                continue
            if state.przepracowane[imie] >= normatyw.minuty:
                continue
            if czy_mozna_przydzielic(
                pracownik=p, data=data, nowy_kod="R",
                przydzial=state.przydzial[imie],
                przepracowane_minuty=state.przepracowane[imie],
                normatyw_minuty=normatyw.minuty,
                koncowka_minuty=normatyw.koncowka_minuty,
                rok=data.year, miesiac=data.month,
            ):
                state.przydziel(imie, data, "R")


# Faza 2: Kontrakty (DN preferowane, potem D/N)

def faza_2_kontrakty(state: HarmonogramState, norm: object) -> None:
    """Przydziela zmiany kontraktowcom, rozkładając je równomiernie w miesiącu."""
    kontrakty = [p for p in state.pracownicy if p.is_kontrakt and not p.tylko_7h]
    if not kontrakty:
        return

    max_d = _get_max_shifts(norm, "D")
    max_n = _get_max_shifts(norm, "N")

    kontrakty_posortowane = sorted(
        kontrakty, key=lambda x: (len(state.przydzial[x.imie_nazwisko]), x.imie_nazwisko)
    )

    for p in kontrakty_posortowane:
        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]
        # Kontraktowcy preferują DN (24h), więc szacujemy liczbę zmian jednostkami 24h
        potrzebne = max(1, (normatyw.minuty + FULL_SHIFT_MINUTES * 2 - 1) // (FULL_SHIFT_MINUTES * 2))

        def _klucz_dnia(d):
            n_zmian = sum(1 for k in state.przydzial[imie].values() if k in WORKING_SHIFTS)
            # "Tłok" na dobie: ilu pracowników w tej samej grupie ma jakąkolwiek zmianę roboczą
            unique_people = sum(
                1
                for prac in state.pracownicy
                if state.get_przydzial(prac.imie_nazwisko, d) in WORKING_SHIFTS
            )
            obs = state.liczba_na_dzien(d, "D") + state.liczba_na_dzien(d, "N")
            luka = _rozmiar_luki_pracownika(imie, d, state)
            # +0.5 przesuwa idealną pozycję do środka przedziału, nie na początek miesiąca
            ideal = (n_zmian + 0.5) * len(state.dni) / potrzebne if potrzebne else 0
            od_ideal = abs(state.dni.index(d) - ideal)
            kara = 200 if _dni_od_ostatniej_zmiany(imie, d, state) <= 1 else 0
            # unique_people na 1. miejscu → minimalizujemy napakowanie w czasie
            return (unique_people, od_ideal, obs, kara, -luka)

        while state.przepracowane[imie] < normatyw.minuty:
            kandydaci = []
            for data in state.dni:
                if state.get_przydzial(imie, data) != "":
                    continue
                if data.weekday() >= 5 and not p.pracuje_w_weekendy:
                    continue
                obs_d = state.liczba_na_dzien(data, "D")
                obs_n = state.liczba_na_dzien(data, "N")
                klucz = _klucz_dnia(data)
                for kod in ("DN", "D", "N"):
                    if kod == "DN" and (obs_d >= max_d or obs_n >= max_n):
                        continue
                    if kod == "D" and obs_d >= max_d:
                        continue
                    if kod == "N" and obs_n >= max_n:
                        continue
                    if czy_mozna_przydzielic(
                        p, data, kod, state.przydzial[imie], state.przepracowane[imie],
                        normatyw.minuty * 2, normatyw.koncowka_minuty, data.year, data.month,
                    ):
                        kandydaci.append((klucz, data, kod))
                        break
            if not kandydaci:
                break
            kandydaci.sort(key=lambda x: x[0])
            _, data, kod = kandydaci[0]
            state.przydziel(imie, data, kod)


# Faza 3: Obsada D/N – wypełnienie minimalnej normy

def _get_max_shifts(norm, typ: str) -> int:
    """Maksymalna obsada danego typu na dobę (limit przeciw tłumom)."""
    if typ == "D":
        return norm.max_day_shifts if norm.max_day_shifts > 0 else norm.day_shifts + 1
    if typ == "N":
        return norm.max_night_shifts if norm.max_night_shifts > 0 else norm.night_shifts + 1
    return norm.max_r_shifts if norm.max_r_shifts > 0 else norm.r_shifts


def _policz_obsade(state: HarmonogramState, data: datetime.date, typ: str) -> int:
    """Aktualna obsada danego typu na wybraną dobę."""
    return sum(
        1 for p in state.pracownicy
        if state.get_przydzial(p.imie_nazwisko, data) in _KODY_OBSADY.get(typ, set())
    )


def _przydziel_najlepszego(state: HarmonogramState, data: datetime.date, kod: str, pula: list) -> None:
    """Zachłannie przydziela jeden dyżur 'kod' najlepszemu pracownikowi z puli."""
    kandydaci = [
        (score_pracownik(p, data, kod, state), p)
        for p in pula
        if state.get_przydzial(p.imie_nazwisko, data) == ""
    ]
    kandydaci = [(s, p) for s, p in kandydaci if s > float("-inf")]
    if kandydaci:
        kandydaci.sort(key=lambda x: x[0], reverse=True)
        state.przydziel(kandydaci[0][1].imie_nazwisko, data, kod)


def faza_3_obsada(state: HarmonogramState, norm: object) -> None:
    """
    Dla każdego dnia wypełnia minimalną normę obsady D/N.
    Krok 1: etatowcy. Krok 2 (fallback): kontraktowcy.
    """
    etatowcy  = [p for p in state.pracownicy if p.is_etat and not p.tylko_7h]
    kontrakty = [p for p in state.pracownicy if p.is_kontrakt and not p.tylko_7h]
    min_d = norm.day_shifts_min if norm.day_shifts_min > 0 else norm.day_shifts

    # Minimalna liczba UNIKALNYCH pracowników na dobę:
    # zmiana DN (24h) liczy się jako D i N jednocześnie, więc 1 osoba może
    # pozornie spełnić oba minimia – wymagamy co najmniej 2 różnych osób
    # gdy harmonogram potrzebuje zarówno D jak i N.
    min_unique = 2 if (min_d > 0 and norm.night_shifts > 0) else 0

    for data in state.dni:
        for kod, min_obs in (("D", min_d), ("N", norm.night_shifts)):
            brak = max(0, min_obs - _policz_obsade(state, data, kod))
            for _ in range(brak):
                _przydziel_najlepszego(state, data, kod, etatowcy)
            # fallback kontraktami jeśli wciąż brakuje
            brak2 = max(0, min_obs - _policz_obsade(state, data, kod))
            for _ in range(brak2):
                _przydziel_najlepszego(state, data, kod, kontrakty)

        # Krok 3: zapewnij minimalną liczbę unikalnych osób na dobę
        if min_unique > 0:
            pula = etatowcy + kontrakty
            prev_unique = -1
            while True:
                unique = sum(
                    1 for p in state.pracownicy
                    if state.get_przydzial(p.imie_nazwisko, data) in WORKING_SHIFTS
                )
                if unique >= min_unique or unique == prev_unique:
                    break
                prev_unique = unique
                for typ in ("D", "N"):
                    if _policz_obsade(state, data, typ) < _get_max_shifts(norm, typ):
                        _przydziel_najlepszego(state, data, typ, pula)
                        break


# Faza 3b: Uzupełnianie niedoborów godzin etatowców

def faza_3b_uzupelnianie(state: HarmonogramState, norm: object) -> None:
    """
    Przydziela dodatkowe D/N etatowcom z niedoborem godzin,
    respektując limit obsady na dobę (max_*).
    """
    etatowcy = [p for p in state.pracownicy if p.is_etat and not p.tylko_7h]
    if not etatowcy:
        return

    max_d = _get_max_shifts(norm, "D")
    max_n = _get_max_shifts(norm, "N")

    zmiana_nastapila = True
    while zmiana_nastapila:
        zmiana_nastapila = False
        etatowcy_posortowani = sorted(
            etatowcy, key=lambda x: (len(state.przydzial[x.imie_nazwisko]), x.imie_nazwisko)
        )
        for p in etatowcy_posortowani:
            imie = p.imie_nazwisko
            normatyw = state.normatywy[imie]
            if state.pozostale_minuty(imie) < FULL_SHIFT_MINUTES:
                continue

            # Zbierz i posortuj kandydujące dni dla D i N
            najlepszy = None
            najlepszy_klucz = None
            n_juz = sum(1 for k in state.przydzial[imie].values() if k in WORKING_SHIFTS)
            total_pot = max(1, (normatyw.minuty + FULL_SHIFT_MINUTES - 1) // FULL_SHIFT_MINUTES)
            for data in state.dni:
                if state.get_przydzial(imie, data) != "":
                    continue
                luka = _rozmiar_luki_pracownika(imie, data, state)
                kara = 200 if _dni_od_ostatniej_zmiany(imie, data, state) <= 1 else 0
                ideal = (n_juz + 0.5) * len(state.dni) / total_pot
                od_ideal = abs(state.dni.index(data) - ideal)
                for kod, max_obs in (("D", max_d), ("N", max_n)):
                    obs = _policz_obsade(state, data, kod)
                    if obs < max_obs and czy_mozna_przydzielic(
                        p, data, kod,
                        state.przydzial[imie], state.przepracowane[imie],
                        normatyw.minuty, normatyw.koncowka_minuty,
                        data.year, data.month,
                    ):
                        klucz = (obs, kara, -luka, od_ideal)
                        if najlepszy_klucz is None or klucz < najlepszy_klucz:
                            najlepszy_klucz = klucz
                            najlepszy = (imie, data, kod)

            if najlepszy:
                state.przydziel(*najlepszy)
                zmiana_nastapila = True


# Faza 4: Końcówki DK

def faza_4_koncowki(state: HarmonogramState) -> None:
    """Dodaje końcówkę DK etatowcom zmianowym z niedoborem < 12h."""
    dni_index = {d: i for i, d in enumerate(state.dni)}

    for p in state.pracownicy:
        if not p.is_etat or p.tylko_7h:
            continue

        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]
        if normatyw.koncowka_minuty == 0 or state.przepracowane[imie] >= normatyw.minuty:
            continue

        # Docelowa pozycja DK w miesiącu (na podstawie tego, ile 12h bloków pracownik ma już
        # w rozkładzie: D+DN i N+DN liczą się jako osobne bloki).
        n_juz_12h = state.liczba_dziennych[imie] + state.liczba_nocnych[imie]
        potrzebne_12h = normatyw.pelne_dyzury_12h or 1
        ideal = (n_juz_12h + 0.5) * len(state.dni) / potrzebne_12h

        najlepszy_data = None
        najlepszy_klucz = None  # (tłum_na_dobie, od_ideal)

        for data in state.dni:
            # DK tylko w dni robocze (pn–pt) i nie na święto
            if data.weekday() >= 5 or czy_swieto(data, state.swieta):
                continue
            if state.get_przydzial(imie, data) != "":
                continue
            if not czy_mozna_przydzielic(
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
                continue

            # Liczba osób pracujących na jakąkolwiek zmianę roboczą w tej dobie.
            tlum_na_dobie = sum(
                1
                for prac in state.pracownicy
                if state.get_przydzial(prac.imie_nazwisko, data) in WORKING_SHIFTS
            )
            od_ideal = abs(dni_index[data] - ideal)
            klucz = (tlum_na_dobie, od_ideal)

            if najlepszy_klucz is None or klucz < najlepszy_klucz:
                najlepszy_klucz = klucz
                najlepszy_data = data

        if najlepszy_data is not None:
            state.przydziel(imie, najlepszy_data, "DK")


# Faza 5: Uzupełnienie pustych dni (fallback awaryjny)

def faza_5_uzupelnij_puste_dni(state: HarmonogramState, norm: object) -> None:
    """
    Jeśli dzień ma 0 osób na zmianie, awaryjnie przydziela kogoś.
    Próba 1: bez nadgodzin. Próba 2: z minimalnym przekroczeniem normatywu.
    """
    for data in state.dni:
        if any(state.get_przydzial(p.imie_nazwisko, data) in WORKING_SHIFTS for p in state.pracownicy):
            continue

        for allow_overtime in (False, True):
            assigned = False
            kandydaci = sorted(
                state.pracownicy,
                key=lambda p: state.przepracowane[p.imie_nazwisko] - state.normatywy[p.imie_nazwisko].minuty,
            )
            for p in kandydaci:
                imie = p.imie_nazwisko
                if data in p.niedyspozycje or data in p.absencje:
                    continue
                if state.get_przydzial(imie, data) != "":
                    continue
                if data.weekday() >= 5 and not p.pracuje_w_weekendy:
                    continue
                if czy_swieto(data, state.swieta) and not p.pracuje_w_weekendy:
                    continue
                if p.tylko_7h:
                    if data.weekday() < 5 and not czy_swieto(data, state.swieta):
                        state.przydziel(imie, data, "R")
                        assigned = True
                    break

                # Nadgodziny wolno dopuścić wyłącznie kontraktowcom i dopiero
                # w drugim podejściu. Etatowiec nie przekracza normatywu nigdy.
                przekroczy = (
                    state.przepracowane[imie] + FULL_SHIFT_MINUTES
                    > state.normatywy[imie].minuty
                )
                if przekroczy and (p.is_etat or not allow_overtime):
                    continue

                # Zacznij od zmiany słabiej obsadzonej, ale gdy reguły jej nie
                # przepuszczą – spróbuj drugiej, zamiast rezygnować z pracownika.
                if state.liczba_na_dzien(data, "D") <= state.liczba_na_dzien(data, "N"):
                    kolejnosc = ("D", "N")
                else:
                    kolejnosc = ("N", "D")

                for kod in kolejnosc:
                    if czy_mozna_przydzielic_awaryjnie(
                        przydzial=state.przydzial[imie],
                        data=data,
                        nowy_kod=kod,
                        koncowka_minuty=state.normatywy[imie].koncowka_minuty,
                        rok=data.year,
                        miesiac=data.month,
                    ):
                        state.przydziel(imie, data, kod)
                        assigned = True
                        break
                if assigned:
                    break
            if assigned:
                break


# Generowanie harmonogramu dla jednej grupy

def generuj_harmonogram_grupy(
    pracownicy: List[Pracownik],
    schedule_key: str,
    rok: int,
    miesiac: int,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    liczba_dni_roboczych: int,
) -> HarmonogramState:
    """Generuje harmonogram dla jednej grupy pracowników (np. gastro_piel)."""
    # Normatywy muszą być OSTATECZNE przed pierwszym przydziałem: przydziel()
    # odczytuje koncowka_minuty w momencie zapisu, a urlop zmienia jej długość.
    minuty_absencji = {
        p.imie_nazwisko: suma_minut_absencji(p.absencje, dni, p.orzeczenie)
        for p in pracownicy
    }
    normatywy = oblicz_normatywy(pracownicy, liczba_dni_roboczych, minuty_absencji)
    norm = STAFFING_NORMS[schedule_key]
    state = HarmonogramState(pracownicy, normatywy, dni, swieta)

    faza_0_absencje(state)
    faza_1_r_shifts(state)
    faza_2_kontrakty(state, norm)
    faza_3_obsada(state, norm)
    faza_3b_uzupelnianie(state, norm)
    faza_4_koncowki(state)
    faza_5_uzupelnij_puste_dni(state, norm)

    return state


# Generowanie wszystkich harmonogramów

def generuj_wszystkie_harmonogramy(
    grupy: Dict[str, List[Pracownik]],
    rok: int,
    miesiac: int,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    liczba_dni_roboczych: int,
) -> Dict[str, HarmonogramState]:
    """Generuje harmonogramy dla wszystkich grup pracowników."""
    return {
        key: generuj_harmonogram_grupy(pracownicy, key, rok, miesiac, dni, swieta, liczba_dni_roboczych)
        for key, pracownicy in grupy.items()
        if pracownicy
    }


# Podsumowanie

def oblicz_podsumowanie(state: HarmonogramState, swieta: Set[datetime.date]) -> List[dict]:
    """Oblicza podsumowanie dla każdego pracownika (godziny, bilans, liczniki dyżurów)."""
    from modules.normative import _minuty_na_str

    def _bilans_str(bilans: int, is_kontrakt: bool) -> str:
        if bilans > 0:
            return f"+{_minuty_na_str(bilans)} ({'ponad min' if is_kontrakt else 'nadgodziny!'})"
        if bilans < 0:
            return f"-{_minuty_na_str(abs(bilans))} (niedobór)"
        return "0h (OK)"

    wyniki = []
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        normatyw = state.normatywy[imie]
        przeprac = state.przepracowane[imie]
        bilans = przeprac - normatyw.minuty
        suma = sum(1 for k in state.przydzial[imie].values() if k in WORKING_SHIFTS)
        wyniki.append({
            "Imię i nazwisko":    imie,
            "Typ umowy":          p.typ_umowy,
            "Normatyw":           _minuty_na_str(normatyw.minuty),
            "Przepracowane":      _minuty_na_str(przeprac),
            "Bilans":             _bilans_str(bilans, p.is_kontrakt),
            "Bilans_min":         bilans,
            "Suma dyżurów":       suma,
            "Dyżury dzienne":     state.liczba_dziennych[imie],
            "Dyżury nocne":       state.liczba_nocnych[imie],
            "Dyżury weekendowe":  state.liczba_weekendowych[imie],
            "Dyżury świąteczne":  state.liczba_swiatecznych[imie],
        })
    return wyniki
