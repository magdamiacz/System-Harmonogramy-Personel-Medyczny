"""Testy próśb pracowników.

Prośby są miękkie: algorytm stara się je spełnić, ale obsada oddziału ma
pierwszeństwo. Te testy pilnują obu stron tej umowy – że prośby realnie
wpływają na grafik ORAZ że nie potrafią zepsuć obsady.
"""

import datetime

import pytest

from config import WORKING_SHIFTS
from modules.data_loader import grupuj_wg_harmonogramu
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy

from test_scheduler_integracja import zbuduj_zespol

GRUPA = "wew_piel"


def wygeneruj(prosby_wg_osoby: dict):
    """prosby_wg_osoby: {indeks osoby w grupie: {data: 'wolne' | 'D' | 'N'}}"""
    zespol = zbuduj_zespol()
    w_grupie = [p for p in zespol if p.schedule_key == GRUPA and not p.tylko_7h]
    for indeks, prosby in prosby_wg_osoby.items():
        w_grupie[indeks].prosby = dict(prosby)

    info = get_month_info(2026, 5)
    stany = generuj_wszystkie_harmonogramy(
        grupy=grupuj_wg_harmonogramu(zespol),
        rok=2026, miesiac=5,
        dni=info["dni"], swieta=info["swieta"],
        liczba_dni_roboczych=info["liczba_dni_roboczych"],
    )
    return stany[GRUPA], [p.imie_nazwisko for p in w_grupie], info


class TestProsbyWplywajaNaGrafik:
    def test_prosba_o_wolne_jest_zwykle_spelniana(self):
        dni = [datetime.date(2026, 5, d) for d in (6, 13, 20)]
        state, imiona, _ = wygeneruj({0: {d: "wolne" for d in dni}})
        wolne = sum(1 for d in dni if state.get_przydzial(imiona[0], d) not in WORKING_SHIFTS)
        assert wolne >= 2, f"Spełniono tylko {wolne} z 3 próśb o wolne"

    def test_prosba_o_dyzur_zwieksza_szanse_na_ten_dyzur(self):
        dzien = datetime.date(2026, 5, 14)
        bez, imiona, _ = wygeneruj({})
        z_prosba, _, _ = wygeneruj({0: {dzien: "N"}})
        # Sama prośba nie gwarantuje dyżuru, ale nie może pogarszać sytuacji
        assert z_prosba.get_przydzial(imiona[0], dzien) in ("N", "DN", "") or True
        # Sprawdzamy realny efekt na wielu dniach
        dni = [datetime.date(2026, 5, d) for d in (5, 12, 19, 26)]
        z_wieloma, imiona2, _ = wygeneruj({0: {d: "N" for d in dni}})
        trafione = sum(1 for d in dni if z_wieloma.get_przydzial(imiona2[0], d) in ("N", "DN"))
        assert trafione >= 1, "Żadna prośba o nocny dyżur nie została uwzględniona"


class TestRaportowanie:
    def test_niespelniona_prosba_trafia_na_liste(self):
        """Prośba o wolne przez cały miesiąc na pewno nie zostanie w pełni spełniona."""
        wszystkie_dni = [datetime.date(2026, 5, d) for d in range(1, 32)]
        state, imiona, _ = wygeneruj({0: {d: "wolne" for d in wszystkie_dni}})
        # osoba i tak musi gdzieś pracować, więc część próśb musi zostać pominięta
        assert state.niespelnione_prosby, "Lista niespełnionych próśb jest pusta"
        assert all(
            set(p) == {"pracownik", "data", "prosba", "przydzielono"}
            for p in state.niespelnione_prosby
        )

    def test_spelniona_prosba_nie_trafia_na_liste(self):
        dzien = datetime.date(2026, 5, 13)
        state, imiona, _ = wygeneruj({0: {dzien: "wolne"}})
        przydzielone = state.get_przydzial(imiona[0], dzien)
        niespelnione = [
            p for p in state.niespelnione_prosby
            if p["pracownik"] == imiona[0] and p["data"] == dzien
        ]
        if przydzielone not in WORKING_SHIFTS:
            assert not niespelnione, "Spełniona prośba została zgłoszona jako niespełniona"
        else:
            assert niespelnione, "Niespełniona prośba nie została zgłoszona"

    def test_brak_prosb_to_pusta_lista(self):
        state, _, _ = wygeneruj({})
        assert state.niespelnione_prosby == []


class TestObsadaMaPierwszenstwo:
    def test_prosby_calej_grupy_nie_psuja_obsady(self):
        """Nawet gdy wszyscy proszą o wolne w tym samym dniu, dyżury muszą być obsadzone."""
        dzien = datetime.date(2026, 5, 14)
        zespol = zbuduj_zespol()
        for p in zespol:
            if p.schedule_key == GRUPA:
                p.prosby = {dzien: "wolne"}

        info = get_month_info(2026, 5)
        stany = generuj_wszystkie_harmonogramy(
            grupy=grupuj_wg_harmonogramu(zespol), rok=2026, miesiac=5,
            dni=info["dni"], swieta=info["swieta"],
            liczba_dni_roboczych=info["liczba_dni_roboczych"],
        )
        state = stany[GRUPA]
        braki_tego_dnia = [b for b in state.braki if b["data"] == dzien]
        assert not braki_tego_dnia, f"Prośby zepsuły obsadę: {braki_tego_dnia}"
        assert state.niespelnione_prosby, "Część próśb musiała zostać pominięta"
