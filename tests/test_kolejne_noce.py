"""Testy reguły nocek: maks. 2 pod rząd, po serii co najmniej 2 dni wolne."""

import datetime

import pytest

from modules.constraints import sprawdz_kolejne_noce

# Wygodny skrót: pracujemy na maju 2026
def d(dzien: int) -> datetime.date:
    return datetime.date(2026, 5, dzien)


def grafik(**dni) -> dict:
    """grafik(d5="N", d6="N") -> {2026-05-05: "N", 2026-05-06: "N"}"""
    return {d(int(k[1:])): v for k, v in dni.items()}


class TestDlugoscSerii:
    def test_pierwsza_nocka_zawsze_mozliwa(self):
        assert sprawdz_kolejne_noce({}, d(10), "N") is True

    def test_druga_nocka_pod_rzad_dozwolona(self):
        assert sprawdz_kolejne_noce(grafik(d9="N"), d(10), "N") is True

    def test_trzecia_nocka_pod_rzad_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d8="N", d9="N"), d(10), "N") is False

    def test_czwarta_nocka_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d7="N", d8="N", d9="N"), d(10), "N") is False

    def test_nocka_wstawiona_POMIEDZY_dwie_istniejace_odrzucona(self):
        """Fazy uzupełniające wstawiają dyżury przed istniejącymi – seria budowana 'od tyłu'."""
        assert sprawdz_kolejne_noce(grafik(d9="N", d11="N"), d(10), "N") is False

    def test_nocka_przed_dwiema_istniejacymi_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d11="N", d12="N"), d(10), "N") is False


class TestOdpoczynekPoSerii:
    def test_dzienny_dzien_po_nocce_odrzucony(self):
        assert sprawdz_kolejne_noce(grafik(d9="N"), d(10), "D") is False

    def test_dzienny_dwa_dni_po_nocce_odrzucony(self):
        assert sprawdz_kolejne_noce(grafik(d8="N"), d(10), "D") is False

    def test_dzienny_trzy_dni_po_nocce_dozwolony(self):
        assert sprawdz_kolejne_noce(grafik(d7="N"), d(10), "D") is True

    def test_nocka_dwa_dni_po_wczesniejszej_serii_odrzucona(self):
        """Po serii nocy muszą być 2 dni wolne – także zanim zacznie się nowa seria."""
        assert sprawdz_kolejne_noce(grafik(d8="N"), d(10), "N") is False

    def test_nocka_trzy_dni_po_serii_dozwolona(self):
        assert sprawdz_kolejne_noce(grafik(d7="N"), d(10), "N") is True

    def test_zmiana_R_tez_podlega_odpoczynkowi(self):
        assert sprawdz_kolejne_noce(grafik(d9="N"), d(10), "R") is False

    def test_rytm_dzien_noc_wolne_wolne_przechodzi(self):
        """Docelowy rytm z wymagania: dzień, noc, 2 dni przerwy, potem znowu dzień."""
        plan = grafik(d1="D", d2="N")
        assert sprawdz_kolejne_noce(plan, d(3), "D") is False   # zaraz po nocce
        assert sprawdz_kolejne_noce(plan, d(4), "D") is False   # drugi dzień odpoczynku
        assert sprawdz_kolejne_noce(plan, d(5), "D") is True    # po odpoczynku – można


class TestOdpoczynekSprawdzanyWPrzod:
    """Fazy uzupełniające dostawiają nocki PRZED dyżurami już stojącymi w grafiku.

    Sprawdzanie wyłącznie wstecz przepuszczało takie przypadki – wyszło dopiero
    w teście integracyjnym na prawdziwych danych.
    """

    def test_nocka_dzien_przed_istniejacym_dyzurem_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d11="D"), d(10), "N") is False

    def test_nocka_dwa_dni_przed_istniejacym_dyzurem_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d12="D"), d(10), "N") is False

    def test_nocka_trzy_dni_przed_dyzurem_dozwolona(self):
        assert sprawdz_kolejne_noce(grafik(d13="D"), d(10), "N") is True

    def test_odpoczynek_liczony_od_konca_calej_serii(self):
        """Seria kończy się 11-go, więc dyżur 13-go jest wciąż za wcześnie."""
        assert sprawdz_kolejne_noce(grafik(d11="N", d13="D"), d(10), "N") is False

    def test_dyzur_dzienny_nie_podlega_sprawdzaniu_w_przod(self):
        # Dzienna zmiana nie tworzy serii nocnej, więc kolejne dni są bez znaczenia
        assert sprawdz_kolejne_noce(grafik(d11="D"), d(10), "D") is True


class TestDyzurCalodobowy:
    def test_DN_liczy_sie_jako_noc(self):
        assert sprawdz_kolejne_noce(grafik(d8="DN", d9="DN"), d(10), "N") is False

    def test_dwa_DN_pod_rzad_dozwolone(self):
        assert sprawdz_kolejne_noce(grafik(d9="DN"), d(10), "DN") is True

    def test_praca_po_serii_DN_odrzucona(self):
        assert sprawdz_kolejne_noce(grafik(d9="DN"), d(10), "D") is False


class TestKodyNiepracujace:
    @pytest.mark.parametrize("kod", ["", "U", "U12", "UM", "W"])
    def test_kody_bez_pracy_zawsze_dozwolone(self, kod):
        plan = grafik(d8="N", d9="N")
        assert sprawdz_kolejne_noce(plan, d(10), kod) is True

    def test_dzienny_nie_tworzy_serii_nocnej(self):
        assert sprawdz_kolejne_noce(grafik(d8="D", d9="D"), d(10), "D") is True


class TestBrakFalszywychBlokad:
    def test_wczesniejsze_naruszenie_nie_blokuje_odleglego_dnia(self):
        """Kolizja sprzed tygodnia nie może unieważniać poprawnego przydziału."""
        plan = grafik(d1="N", d2="N", d3="D")   # stan już naruszający regułę
        assert sprawdz_kolejne_noce(plan, d(20), "N") is True

    def test_seria_przez_granice_miesiaca_jest_niewidoczna(self):
        """Grafik obejmuje jeden miesiąc – brak danych z poprzedniego traktujemy jak wolne."""
        assert sprawdz_kolejne_noce({}, d(1), "N") is True


class TestParametry:
    def test_mozna_poluzowac_dni_odpoczynku(self):
        plan = grafik(d8="N")
        assert sprawdz_kolejne_noce(plan, d(10), "D") is False
        assert sprawdz_kolejne_noce(plan, d(10), "D", dni_wolne=1) is True

    def test_limit_serii_pozostaje_przy_poluzowanym_odpoczynku(self):
        plan = grafik(d8="N", d9="N")
        assert sprawdz_kolejne_noce(plan, d(10), "N", dni_wolne=1) is False
