# modules/holidays.py
# Obliczanie polskich świąt ustawowych dla dowolnego roku.
# Świąta stałe (co roku ta sama data) + ruchome (Wielkanoc i pochodne).

import datetime
from typing import Set


def _oblicz_wielkanoc(rok: int) -> datetime.date:
    """
    Oblicza datę Niedzieli Wielkanocnej algorytmem anonimowym z 1876 r.
    (tzw. algorytm Meeusa/Jonesa/Butchera).
    """
    a = rok % 19
    b = rok // 100
    c = rok % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    miesiac = (h + l - 7 * m + 114) // 31
    dzien = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(rok, miesiac, dzien)


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
