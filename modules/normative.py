# Obliczanie normatywu miesięcznego dla każdego pracownika
# oraz rozkładu tego normatywu na zmiany 12h i końcówkę (DK).

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

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
    minuty: int              # Normatyw SKUTECZNY – już po odliczeniu urlopów
    pelne_dyzury_12h: int    # Liczba pełnych dyżurów 12h
    koncowka_minuty: int     # Reszta po pełnych dyżurach (0 = brak końcówki)
    dni_robocze: int         # Liczba dni roboczych w miesiącu
    minuty_bazowe: int = 0   # Normatyw przed odliczeniem urlopów
    minuty_absencji: int = 0 # Ile minut zdjęły urlopy

    @property
    def godziny_str(self) -> str:
        """Normatyw jako string 'Xh Ymin'."""
        return _minuty_na_str(self.minuty)

    @property
    def absencja_str(self) -> str:
        """Odliczony urlop jako string, '—' gdy pracownik nie ma urlopu."""
        if self.minuty_absencji == 0:
            return "—"
        return _minuty_na_str(self.minuty_absencji)

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

def oblicz_normatyw(
    pracownik: Pracownik,
    liczba_dni_roboczych: int,
    minuty_absencji: int = 0,
) -> Normatyw:
    """
    Oblicza normatyw miesięczny pracownika, pomniejszony o godziny urlopu.

    Podstawa dla etatowców:
        - zwykły:        liczba_dni_roboczych × 7h35min (455 min)
        - z orzeczeniem: liczba_dni_roboczych × 7h00min (420 min)
    Dla kontraktów podstawą jest minimum umowne: 160h (duży) albo 120h (mały).

    Od podstawy odejmujemy `minuty_absencji` (urlop). Pole `minuty` niesie
    normatyw SKUTECZNY, dzięki czemu bilans, limit nadgodzin i scoring działają
    bez żadnych zmian.

    Rozkład na zmiany liczony jest z wartości POMNIEJSZONEJ – długość końcówki
    DK to `minuty % 720`, więc urlop skraca również końcówkę.
    """
    if pracownik.is_etat:
        na_dobe = (
            WORK_MINUTES_PER_DAY_DISABILITY if pracownik.orzeczenie
            else WORK_MINUTES_PER_DAY_STANDARD
        )
        minuty_bazowe = liczba_dni_roboczych * na_dobe
    elif pracownik.is_duzy_kontrakt:
        minuty_bazowe = MIN_HOURS_DUZY_KONTRAKT
    else:
        minuty_bazowe = MIN_HOURS_MALY_KONTRAKT

    minuty_absencji = max(0, minuty_absencji)
    minuty = max(0, minuty_bazowe - minuty_absencji)

    # Pracownicy tylko_7h pracują na zmianach R, nie na 12h – bez rozkładu i końcówki
    if pracownik.is_etat and pracownik.tylko_7h:
        pelne_dyzury = 0
        koncowka = 0
    else:
        pelne_dyzury = minuty // FULL_SHIFT_MINUTES
        koncowka = minuty % FULL_SHIFT_MINUTES

    return Normatyw(
        pracownik=pracownik.imie_nazwisko,
        typ_umowy=pracownik.typ_umowy,
        minuty=minuty,
        pelne_dyzury_12h=pelne_dyzury,
        koncowka_minuty=koncowka,
        dni_robocze=liczba_dni_roboczych,
        minuty_bazowe=minuty_bazowe,
        minuty_absencji=minuty_absencji,
    )


def oblicz_normatywy(
    pracownicy: List[Pracownik],
    liczba_dni_roboczych: int,
    minuty_absencji: Optional[Dict[str, int]] = None,
) -> dict:
    """
    Oblicza normatywy dla całej listy pracowników.

    `minuty_absencji` to {imie_nazwisko: minuty urlopu w tym miesiącu}.
    Pominięcie argumentu daje normatywy bez odliczeń – jak przed zmianą.

    Zwraca słownik {imie_nazwisko: Normatyw}.
    """
    absencje = minuty_absencji or {}
    return {
        p.imie_nazwisko: oblicz_normatyw(
            p, liczba_dni_roboczych, absencje.get(p.imie_nazwisko, 0)
        )
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
