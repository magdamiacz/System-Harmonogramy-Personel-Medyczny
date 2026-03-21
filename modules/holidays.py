# modules/holidays.py
# Obliczanie polskich świąt ustawowych dla dowolnego roku.
# Świąta stałe (co roku ta sama data) + ruchome (Wielkanoc i pochodne).

import datetime
from typing import Set


def _oblicz_wielkanoc(rok: int) -> datetime.date:
    """
    Oblicza datę Niedzieli Wielkanocnej Gaussowską Formułą Wielkanocną
    (Gaußsche Osterformel, C.F. Gauss, ok. 1800 r.).

    Zmienne:
        M — epakta stulecia (dni do pełni księżyca)
        N — korekta dnia tygodnia stulecia
        d — liczba dni od 21 marca do pełni księżyca
        e — korekta do najbliższej niedzieli po pełni
    """
    a = rok % 19
    b = rok % 4
    c = rok % 7
    k = rok // 100
    p = (13 + 8 * k) // 25
    q = k // 4
    M = (15 - p + k - q) % 30
    N = (4 + k - q) % 7
    d = (19 * a + M) % 30
    e = (2 * b + 4 * c + 6 * d + N) % 7
    if d + e < 10:
        return datetime.date(rok, 3, 22 + d + e)
    dzien = d + e - 9
    if dzien == 26:
        dzien = 19
    if dzien == 25 and d == 28 and e == 6 and a > 10:
        dzien = 18
    return datetime.date(rok, 4, dzien)


def pobierz_swieta(rok: int) -> Set[datetime.date]:
    """
    Zwraca zbiór wszystkich polskich świąt ustawowych w danym roku.

    Świąta stałe (13 dni ustawowo wolnych od pracy w Polsce):
    - 1 stycznia   – Nowy Rok
    - 6 stycznia   – Trzech Króli
    - 1 maja        – Święto Pracy
    - 3 maja        – Święto Konstytucji 3 Maja
    - 15 sierpnia   – Wniebowzięcie NMP
    - 1 listopada   – Wszystkich Świętych
    - 11 listopada  – Święto Niepodległości
    - 25 grudnia    – Boże Narodzenie (1. dzień)
    - 26 grudnia    – Boże Narodzenie (2. dzień)

    Świąta ruchome:
    - Niedziela Wielkanocna
    - Poniedziałek Wielkanocny (Wielkanoc + 1 dzień)
    - Zielone Świątki (Wielkanoc + 49 dni)
    - Boże Ciało (Wielkanoc + 60 dni)
    """
    wielkanoc = _oblicz_wielkanoc(rok)

    swieta_stale = {
        datetime.date(rok, 1, 1),    # Nowy Rok
        datetime.date(rok, 1, 6),    # Trzech Króli
        datetime.date(rok, 5, 1),    # Święto Pracy
        datetime.date(rok, 5, 3),    # Konstytucja 3 Maja
        datetime.date(rok, 8, 15),   # Wniebowzięcie NMP
        datetime.date(rok, 11, 1),   # Wszystkich Świętych
        datetime.date(rok, 11, 11),  # Święto Niepodległości
        datetime.date(rok, 12, 25),  # Boże Narodzenie dzień 1
        datetime.date(rok, 12, 26),  # Boże Narodzenie dzień 2
    }

    swieta_ruchome = {
        wielkanoc,                                           # Niedziela Wielkanocna
        wielkanoc + datetime.timedelta(days=1),             # Poniedziałek Wielkanocny
        wielkanoc + datetime.timedelta(days=49),            # Zielone Świątki
        wielkanoc + datetime.timedelta(days=60),            # Boże Ciało
    }

    return swieta_stale | swieta_ruchome


def czy_swieto(data: datetime.date, swieta: Set[datetime.date]) -> bool:
    """Sprawdza, czy podana data jest świętem."""
    return data in swieta


def czy_weekend(data: datetime.date) -> bool:
    """Sprawdza, czy podana data jest sobotą (5) lub niedzielą (6)."""
    return data.weekday() >= 5


def czy_niedziela(data: datetime.date) -> bool:
    """Sprawdza, czy podana data jest niedzielą."""
    return data.weekday() == 6


def pobierz_dni_miesiaca(rok: int, miesiac: int) -> list:
    """
    Zwraca listę wszystkich dat w danym miesiącu.
    """
    import calendar
    num_days = calendar.monthrange(rok, miesiac)[1]
    return [datetime.date(rok, miesiac, d) for d in range(1, num_days + 1)]


def pobierz_dni_robocze(rok: int, miesiac: int) -> list:
    """
    Zwraca listę dni roboczych w danym miesiącu
    (bez weekendów i bez świąt).
    """
    swieta = pobierz_swieta(rok)
    return [
        d for d in pobierz_dni_miesiaca(rok, miesiac)
        if d.weekday() < 5 and d not in swieta
    ]


def get_month_info(rok: int, miesiac: int) -> dict:
    """
    Zwraca słownik z przydatnymi informacjami o miesiącu:
    - dni: lista wszystkich dat
    - dni_robocze: lista dni roboczych
    - swieta: zbiór świąt
    - liczba_dni: liczba dni w miesiącu
    - liczba_dni_roboczych: liczba dni roboczych
    """
    swieta = pobierz_swieta(rok)
    dni = pobierz_dni_miesiaca(rok, miesiac)
    dni_robocze = [d for d in dni if d.weekday() < 5 and d not in swieta]
    return {
        "dni": dni,
        "dni_robocze": dni_robocze,
        "swieta": swieta,
        "liczba_dni": len(dni),
        "liczba_dni_roboczych": len(dni_robocze),
    }
