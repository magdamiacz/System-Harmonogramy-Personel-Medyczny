# Obliczanie normatywu miesięcznego dla każdego pracownika
# oraz rozkładu tego normatywu na zmiany 12h i końcówkę (DK).

import math
from dataclasses import dataclass
from typing import List

from config import (
    FULL_SHIFT_MINUTES,
    MIN_HOURS_DUZY_KONTRAKT,
    MIN_HOURS_MALY_KONTRAKT,
    WORK_MINUTES_PER_DAY_DISABILITY,
    WORK_MINUTES_PER_DAY_STANDARD,
)
from modules.data_loader import Pracownik


# Struktura wynikowa normatywu

@dataclass
class Normatyw:
    """Normatyw miesięczny pracownika wraz z rozkładem na zmiany."""
    pracownik: str           # Imię i nazwisko
    typ_umowy: str
    minuty: int              # Łączny normatyw w minutach
    pelne_dyzury_12h: int    # Liczba pełnych dyżurów 12h
    koncowka_minuty: int     # Reszta po pełnych dyżurach (0 = brak końcówki)
    dni_robocze: int         # Liczba dni roboczych w miesiącu

    @property
    def godziny_str(self) -> str:
        """Normatyw jako string 'Xh Ymin'."""
        return _minuty_na_str(self.minuty)

    @property
    def koncowka_str(self) -> str:
        """Końcówka jako string 'Xh Ymin'."""
        if self.koncowka_minuty == 0:
            return "—"
        return _minuty_na_str(self.koncowka_minuty)

    @property
    def opis_rozkladu(self) -> str:
        """Czytelny opis, np. '12 dyżurów × 12h + 1 × 7h40min'."""
        if self.typ_umowy == "etat":
            opis = f"{self.pelne_dyzury_12h} dyżurów × 12h"
            if self.koncowka_minuty > 0:
                opis += f" + 1 × {self.koncowka_str}"
            return opis
        elif self.typ_umowy == "duzy_kontrakt":
            return f"minimum 160h (kontrakt duży)"
        else:
            return f"minimum 120h (kontrakt mały)"


# Pomocnicze funkcje formatujące

def _minuty_na_str(minuty: int) -> str:
    """Formatuje minuty na 'Xh Ymin', np. 151h40min."""
    h = minuty // 60
    m = minuty % 60
    if m == 0:
        return f"{h}h"
    return f"{h}h{m:02d}min"


def minuty_na_godziny_float(minuty: int) -> float:
    """Konwertuje minuty na godziny z dwoma miejscami dziesiętnymi."""
    return round(minuty / 60, 2)


# Główna funkcja obliczania normatywu

def oblicz_normatyw(pracownik: Pracownik, liczba_dni_roboczych: int) -> Normatyw:
    """
    Oblicza normatyw miesięczny pracownika.

    Dla etatowców:
        - zwykły:        liczba_dni_roboczych × 7h35min (455 min)
        - z orzeczeniem: liczba_dni_roboczych × 7h00min (420 min)
    Rozkład na zmiany: normatyw // 720 pełnych dyżurów 12h + reszta (końcówka).

    Dla kontraktów:
        - duży kontrakt: minimum 160h (bez sztywnego normatywu, liczymy minimum)
        - mały kontrakt: minimum 120h
    """
    if pracownik.is_etat:
        # Etatowiec - normatyw zależy od liczby dni roboczych
        if pracownik.orzeczenie:
            minuty = liczba_dni_roboczych * WORK_MINUTES_PER_DAY_DISABILITY
        else:
            minuty = liczba_dni_roboczych * WORK_MINUTES_PER_DAY_STANDARD

        # Pracownicy tylko_7h mają zmiany R a nie 12h, więc nie rozkładamy na 12h
        if pracownik.tylko_7h:
            pelne_dyzury = 0
            koncowka = 0
        else:
            # Rozkład na dyżury 12h + końcówka
            pelne_dyzury = minuty // FULL_SHIFT_MINUTES
            koncowka = minuty % FULL_SHIFT_MINUTES

        return Normatyw(
            pracownik=pracownik.imie_nazwisko,
            typ_umowy=pracownik.typ_umowy,
            minuty=minuty,
            pelne_dyzury_12h=pelne_dyzury,
            koncowka_minuty=koncowka,
            dni_robocze=liczba_dni_roboczych,
        )

    elif pracownik.is_duzy_kontrakt:
        # Duży kontrakt: minimum 160h - rozkładamy na maksymalnie możliwe DN/D/N
        minuty = MIN_HOURS_DUZY_KONTRAKT
        return Normatyw(
            pracownik=pracownik.imie_nazwisko,
            typ_umowy=pracownik.typ_umowy,
            minuty=minuty,
            pelne_dyzury_12h=minuty // FULL_SHIFT_MINUTES,
            koncowka_minuty=minuty % FULL_SHIFT_MINUTES,
            dni_robocze=liczba_dni_roboczych,
        )

    else:
        # Mały kontrakt: minimum 120h
        minuty = MIN_HOURS_MALY_KONTRAKT
        return Normatyw(
            pracownik=pracownik.imie_nazwisko,
            typ_umowy=pracownik.typ_umowy,
            minuty=minuty,
            pelne_dyzury_12h=minuty // FULL_SHIFT_MINUTES,
            koncowka_minuty=minuty % FULL_SHIFT_MINUTES,
            dni_robocze=liczba_dni_roboczych,
        )


def oblicz_normatywy(
    pracownicy: List[Pracownik],
    liczba_dni_roboczych: int,
) -> dict:
    """
    Oblicza normatywy dla całej listy pracowników.

    Zwraca słownik {imie_nazwisko: Normatyw}.
    """
    return {
        p.imie_nazwisko: oblicz_normatyw(p, liczba_dni_roboczych)
        for p in pracownicy
    }


# Obliczanie przepracowanych godzin z przydzielonych zmian

def oblicz_przepracowane_minuty(
    przydzial: dict,
    normatyw: Normatyw,
) -> int:
    """
    Oblicza łączną liczbę przepracowanych minut na podstawie słownika przydziału.

    Parametry:
        przydzial: {data: kod_zmiany}, np. {date(2026,1,1): "D", ...}
        normatyw: Normatyw pracownika (potrzebny do określenia długości DK)

    Zwraca liczbę minut.
    """
    from config import SHIFT_DURATIONS, WORKING_SHIFTS

    total = 0
    for data, kod in przydzial.items():
        if kod not in WORKING_SHIFTS:
            continue
        if kod == "DK":
            # Końcówka - długość to reszta do normatywu po pełnych dyżurach
            total += normatyw.koncowka_minuty
        elif kod == "R":
            # Zmiany R mają stałą długość 7h35min
            from config import WORK_MINUTES_PER_DAY_STANDARD
            total += WORK_MINUTES_PER_DAY_STANDARD
        else:
            dur = SHIFT_DURATIONS.get(kod, 0)
            if dur is not None:
                total += dur
    return total


def oblicz_bilans(przepracowane_minuty: int, normatyw: Normatyw) -> int:
    """
    Oblicza bilans godzin: przepracowane - normatyw (w minutach).
    Wartość ujemna = niedobór, 0 = dokładnie, dodatnia = nadgodziny.
    """
    return przepracowane_minuty - normatyw.minuty
