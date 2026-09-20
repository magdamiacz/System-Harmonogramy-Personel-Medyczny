"""Testy wykrywania braków obsady.

Algorytm nie zgłasza błędu, gdy nikogo nie da się przydzielić – po prostu
zostawia puste miejsce. Zaostrzone reguły (limit nocek) mogą takie luki tworzyć,
więc muszą być widoczne. Te testy pilnują, że rejestr braków naprawdę działa,
a nie przechodzi tylko dlatego, że nic nie sprawdza.
"""

import pytest

from config import get_schedule_key
from modules.data_loader import Pracownik, grupuj_wg_harmonogramu
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy

from test_scheduler_integracja import zbuduj_zespol


def zespol_o_rozmiarze(ilu: int) -> list:
    """Pielęgniarki gastro – oddział wymaga 2 dziennych i 2 nocnych na dobę."""
    return [
        Pracownik(
            imie_nazwisko=f"Osoba {n:02d}",
            oddzial="gastrologiczny",
            rola="pielęgniarki",
            typ_umowy="etat",
            orzeczenie=False,
            tylko_7h=False,
            pracuje_w_weekendy=True,
            schedule_key=get_schedule_key("gastrologiczny", "pielęgniarki"),
        )
        for n in range(1, ilu + 1)
    ]


def wygeneruj(pracownicy: list):
    info = get_month_info(2026, 5)
    stany = generuj_wszystkie_harmonogramy(
        grupy=grupuj_wg_harmonogramu(pracownicy),
        rok=2026,
        miesiac=5,
        dni=info["dni"],
        swieta=info["swieta"],
        liczba_dni_roboczych=info["liczba_dni_roboczych"],
    )
    return stany


def test_za_maly_zespol_zglasza_braki():
    """Dwie osoby nie obsadzą 2 dziennych i 2 nocnych przez cały miesiąc."""
    stany = wygeneruj(zespol_o_rozmiarze(2))
    state = stany["gastro_piel"]
    assert state.braki, "Rażąco za mały zespół, a mimo to zero zgłoszonych braków"


def test_brak_niesie_komplet_informacji():
    stany = wygeneruj(zespol_o_rozmiarze(2))
    brak = stany["gastro_piel"].braki[0]
    assert set(brak) == {"data", "typ", "wymagane", "obsadzone"}
    assert brak["obsadzone"] < brak["wymagane"]
    assert brak["typ"] in ("D", "N", "R")


def test_realistyczny_zespol_nie_ma_brakow():
    """Reguła nocek nie może psuć obsady przy normalnej liczebności zespołów."""
    stany = wygeneruj(zbuduj_zespol())
    wszystkie = {
        klucz: sum(b["wymagane"] - b["obsadzone"] for b in state.braki)
        for klucz, state in stany.items()
        if state.braki
    }
    assert not wszystkie, f"Nieoczekiwane braki obsady: {wszystkie}"


def test_braki_nie_dotycza_zmian_R_w_weekendy():
    """Zmiany R obsadzane są tylko w dni robocze – ich brak w sobotę to nie luka."""
    stany = wygeneruj(zbuduj_zespol())
    for state in stany.values():
        for brak in state.braki:
            if brak["typ"] == "R":
                assert brak["data"].weekday() < 5
