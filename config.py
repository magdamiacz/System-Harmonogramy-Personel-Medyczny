# Centralna konfiguracja: typy zmian, normy oddziałów, parametry umów

from dataclasses import dataclass, field
from typing import Dict, List

# Typy zmian (kody używane w harmonogramie)

# Godziny trwania każdego kodu zmiany (w minutach)
SHIFT_DURATIONS: Dict[str, int] = {
    "D":  12 * 60,           # Dyżur dzienny 7:00-19:00
    "N":  12 * 60,           # Dyżur nocny  19:00-7:00
    "DN": 24 * 60,           # Dyżur całodobowy 7:00-7:00 (kontrakty)
    "R":  7 * 60 + 35,       # Zmiana robocza 7:00-14:35
    "DK": None,              # Końcówka – długość obliczana indywidualnie
    "U":  0,                 # Urlop wypoczynkowy
    "UM": 0,                 # Urlop macierzyński
    "W":  0,                 # Wolne za niedzielę/święto
    "":   0,                 # Pusta komórka = dzień wolny
}

# Godzina rozpoczęcia każdego kodu zmiany (24h format, dla obliczeń przerw)
SHIFT_START_HOUR: Dict[str, int] = {
    "D":  7,
    "N":  19,
    "DN": 7,
    "R":  7,
    "DK": 7,   # Końcówki zakłada się rano
    "U":  0,
    "UM": 0,
    "W":  0,
    "":   0,
}

# Godzina zakończenia (następny dzień gdy > 24)
SHIFT_END_HOUR: Dict[str, int] = {
    "D":  19,
    "N":  31,   # 19 + 12 = 31 (7 następnego dnia)
    "DN": 31,   # 7 + 24 = 31 (7 następnego dnia)
    "R":  14,   # ~14:35
    "DK": 14,   # zmienna, szacunkowo
    "U":  0,
    "UM": 0,
    "W":  0,
    "":   0,
}

# Skróty zmian, które faktycznie liczą się jako przepracowane godziny
WORKING_SHIFTS = {"D", "N", "DN", "R", "DK"}

# Skróty zmian nocnych (do liczenia dyżurów nocnych w podsumowaniu)
NIGHT_SHIFTS = {"N", "DN"}

# Normy umów o pracę

# Minuty na dobę roboczą dla pracownika etatowego
WORK_MINUTES_PER_DAY_STANDARD = 7 * 60 + 35   # 455 minut (7h35min)
WORK_MINUTES_PER_DAY_DISABILITY = 7 * 60       # 420 minut (7h00min) – orzeczenie

# Minimalne godziny dla kontraktów (w minutach)
MIN_HOURS_DUZY_KONTRAKT = 160 * 60    # 9600 minut
MIN_HOURS_MALY_KONTRAKT = 120 * 60    # 7200 minut

# Maksymalne godziny tygodniowo dla etatowców (w minutach)
MAX_WEEKLY_MINUTES_ETAT = 36 * 60     # 2160 minut

# Minimalna przerwa między zmianami (w minutach)
MIN_REST_MINUTES = 12 * 60            # 720 minut

# Długość pełnego dyżuru w minutach
FULL_SHIFT_MINUTES = 12 * 60          # 720 minut

# Normy obsady na dobę dla każdego harmonogramu
# Każdy harmonogram definiuje wymaganą obsadę: ile D, N, R na każdy dzień.
# Opcja "flexible" pozwala na wariant (np. 1 lub 2 D w gastro-opiekunki).

@dataclass
class DailyStaffingNorm:
    """
    Wymagana i maksymalna obsada na dobę dla jednego harmonogramu.
    Obsada na dobę = dokładnie tyle osób, ile wymaga oddział (bez tłumów).
    max_* pozwala na minimalną nadwyżkę tylko gdy konieczne do normatywu.
    """
    day_shifts: int          # Wymagana liczba dyżurów D (12h)
    night_shifts: int        # Wymagana liczba dyżurów N (12h)
    r_shifts: int = 0       # Wymagana liczba zmian R (7h35min)
    day_shifts_min: int = 0  # Minimalna liczba D (gdy zakres np. 1-2)
    # Maksymalna obsada – aby uniknąć tłumów; nadwyżka tylko gdy konieczna
    max_day_shifts: int = 0   # 0 = domyślnie day_shifts + 1
    max_night_shifts: int = 0  # 0 = domyślnie night_shifts + 1
    max_r_shifts: int = 0     # 0 = domyślnie r_shifts (bez nadwyżki)

STAFFING_NORMS: Dict[str, DailyStaffingNorm] = {
    "gastro_piel": DailyStaffingNorm(
        day_shifts=2,
        night_shifts=2,
        r_shifts=1,
        day_shifts_min=2,
        max_day_shifts=3,   # 2 wymagane, max +1 nadwyżka
        max_night_shifts=3,
        max_r_shifts=1,     # R bez nadwyżki
    ),
    "gastro_opiek": DailyStaffingNorm(
        day_shifts=2,
        night_shifts=1,
        r_shifts=0,
        day_shifts_min=1,
        max_day_shifts=3,
        max_night_shifts=2,
        max_r_shifts=0,
    ),
    "wew_piel": DailyStaffingNorm(
        day_shifts=2,
        night_shifts=2,
        r_shifts=0,
        day_shifts_min=2,
        max_day_shifts=3,
        max_night_shifts=3,
        max_r_shifts=0,
    ),
    "oiok_piel": DailyStaffingNorm(
        day_shifts=1,
        night_shifts=1,
        r_shifts=1,
        day_shifts_min=1,
        max_day_shifts=2,
        max_night_shifts=2,
        max_r_shifts=1,
    ),
    "wew_oiok_opiek": DailyStaffingNorm(
        day_shifts=2,
        night_shifts=2,
        r_shifts=0,
        day_shifts_min=2,
        max_day_shifts=3,
        max_night_shifts=3,
        max_r_shifts=0,
    ),
}

# Mapowanie oddział + rola -> klucz harmonogramu

SCHEDULE_KEYS: List[str] = [
    "gastro_piel",
    "gastro_opiek",
    "wew_piel",
    "oiok_piel",
    "wew_oiok_opiek",
]

SCHEDULE_LABELS: Dict[str, str] = {
    "gastro_piel":     "Gastrologiczny – Pielęgniarki",
    "gastro_opiek":    "Gastrologiczny – Opiekunki",
    "wew_piel":        "Wewnętrzny – Pielęgniarki",
    "oiok_piel":       "OIOK – Pielęgniarki",
    "wew_oiok_opiek":  "Wewnętrzny/OIOK – Opiekunki",
}

def get_schedule_key(oddzial: str, rola: str) -> str:
    """Zwraca klucz harmonogramu na podstawie oddziału i roli pracownika."""
    oddzial = oddzial.strip().lower()
    rola = rola.strip().lower()

    if oddzial == "gastrologiczny" and rola == "pielęgniarki":
        return "gastro_piel"
    if oddzial == "gastrologiczny" and rola == "opiekunki":
        return "gastro_opiek"
    if oddzial == "wewnętrzny" and rola == "pielęgniarki":
        return "wew_piel"
    if oddzial == "oiok" and rola == "pielęgniarki":
        return "oiok_piel"
    if "wewnętrzny" in oddzial and "oiok" in oddzial and rola == "opiekunki":
        return "wew_oiok_opiek"
    if oddzial in ("wewnętrzny/oiok", "wewnętrzny / oiok") and rola == "opiekunki":
        return "wew_oiok_opiek"

    raise ValueError(f"Nieznany oddział/rola: '{oddzial}' / '{rola}'")
