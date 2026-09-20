# Semantyka nieobecności: urlop wypoczynkowy (U) i macierzyński (UM).
#
# Jedyne miejsce w projekcie, które rozumie zapis kodu urlopu. Kod może nieść
# liczbę godzin ("U12" = 12h urlopu w tym dniu). Bez liczby oznacza pełną normę
# dobową pracownika: 7h35min, a przy orzeczeniu 7h.
#
# Godziny urlopu pomniejszają NORMATYW pracownika – nigdy nie dopisują się do
# przepracowanych godzin. Dlatego kody urlopowe celowo nie trafiają do
# SHIFT_DURATIONS ani do map minut w schedulerze; liczyłyby się wtedy podwójnie.

import datetime
import re
from typing import Dict, Iterable, Optional, Tuple

from config import WORK_MINUTES_PER_DAY_DISABILITY, WORK_MINUTES_PER_DAY_STANDARD

# Rodzaje absencji rozpoznawane w kodzie zmiany
RODZAJE_ABSENCJI = ("U", "UM")

# Więcej godzin urlopu niż doba to na pewno pomyłka przy wpisywaniu
MAX_GODZIN_ABSENCJI = 24

# "U", "U12", "UM8", dopuszczalna spacja i dowolna wielkość liter
_RE_ABSENCJA = re.compile(r"^(UM|U)\s*(\d{1,2})?$", re.IGNORECASE)


def parse_absencja(kod: str) -> Optional[Tuple[str, Optional[int]]]:
    """Rozbija kod absencji na (rodzaj, godziny).

    Zwraca ("U", 12) dla "U12", ("U", None) dla samego "U" (pełna norma dobowa),
    oraz None gdy kod nie jest absencją lub jest niepoprawny.
    """
    if not kod:
        return None
    dopasowanie = _RE_ABSENCJA.match(str(kod).strip())
    if not dopasowanie:
        return None

    rodzaj = dopasowanie.group(1).upper()
    godziny_txt = dopasowanie.group(2)
    if godziny_txt is None:
        return rodzaj, None

    godziny = int(godziny_txt)
    if godziny > MAX_GODZIN_ABSENCJI:
        return None
    return rodzaj, godziny


def czy_absencja(kod: str) -> bool:
    """Czy kod oznacza urlop (dowolnej postaci)."""
    return parse_absencja(kod) is not None


def normalizuj_kod(kod: str) -> Optional[str]:
    """Sprowadza kod do postaci kanonicznej ("u 12" -> "U12"). None gdy niepoprawny."""
    rozbite = parse_absencja(kod)
    if rozbite is None:
        return None
    rodzaj, godziny = rozbite
    return rodzaj if godziny is None else f"{rodzaj}{godziny}"


def norma_dobowa(orzeczenie: bool = False) -> int:
    """Dobowa norma czasu pracy w minutach – podstawa dla kodu bez liczby godzin."""
    return WORK_MINUTES_PER_DAY_DISABILITY if orzeczenie else WORK_MINUTES_PER_DAY_STANDARD


def minuty_absencji(kod: str, orzeczenie: bool = False) -> int:
    """Ile minut normatywu zdejmuje dany kod absencji. 0 gdy kod nie jest absencją."""
    rozbite = parse_absencja(kod)
    if rozbite is None:
        return 0
    _, godziny = rozbite
    if godziny is None:
        return norma_dobowa(orzeczenie)
    return godziny * 60


def suma_minut_absencji(
    absencje: Dict[datetime.date, str],
    dni: Iterable[datetime.date],
    orzeczenie: bool = False,
) -> int:
    """Suma minut absencji pracownika ograniczona do podanych dni.

    Ograniczenie do dni jest istotne: normatyw dotyczy jednego miesiąca, więc
    urlop spoza niego nie może go pomniejszać.
    """
    dni_zbior = set(dni)
    return sum(
        minuty_absencji(kod, orzeczenie)
        for data, kod in absencje.items()
        if data in dni_zbior
    )
