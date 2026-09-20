"""Testy parsowania kodów urlopu i przeliczania ich na minuty normatywu."""

import datetime

import pytest

from modules.absences import (
    czy_absencja,
    minuty_absencji,
    norma_dobowa,
    normalizuj_kod,
    parse_absencja,
    suma_minut_absencji,
)


class TestParsowanie:
    @pytest.mark.parametrize(
        "kod, oczekiwane",
        [
            ("U", ("U", None)),
            ("U12", ("U", 12)),
            ("u12", ("U", 12)),
            ("U 12", ("U", 12)),
            ("  U8  ", ("U", 8)),
            ("UM", ("UM", None)),
            ("UM8", ("UM", 8)),
            ("um8", ("UM", 8)),
            ("U0", ("U", 0)),
            ("U24", ("U", 24)),
        ],
    )
    def test_poprawne_kody(self, kod, oczekiwane):
        assert parse_absencja(kod) == oczekiwane

    @pytest.mark.parametrize(
        "kod",
        [
            "",
            None,
            "D",
            "N",
            "DN",
            "R",
            "DK",
            "W",
            "UX",
            "U12X",
            "XU",
            "U-4",
            "U25",     # ponad dobę – na pewno pomyłka
            "U100",
        ],
    )
    def test_kody_odrzucone(self, kod):
        assert parse_absencja(kod) is None
        assert czy_absencja(kod) is False

    def test_kody_zmian_nie_sa_absencja(self):
        # Ważne: "DN" zaczyna się od D, ale nie wolno go pomylić z urlopem
        for kod in ("D", "N", "DN", "R", "DK", "W"):
            assert not czy_absencja(kod)

    @pytest.mark.parametrize(
        "kod, oczekiwane",
        [("u 12", "U12"), ("U", "U"), ("um", "UM"), ("UM8", "UM8"), ("UX", None)],
    )
    def test_normalizacja(self, kod, oczekiwane):
        assert normalizuj_kod(kod) == oczekiwane


class TestMinuty:
    def test_kod_z_liczba_to_godziny(self):
        assert minuty_absencji("U12") == 720
        assert minuty_absencji("U8") == 480
        assert minuty_absencji("U0") == 0

    def test_sam_kod_to_norma_dobowa(self):
        assert minuty_absencji("U") == 455          # 7h35min
        assert minuty_absencji("UM") == 455

    def test_orzeczenie_skraca_norme_dobowa(self):
        assert minuty_absencji("U", orzeczenie=True) == 420   # 7h
        assert norma_dobowa(orzeczenie=True) == 420
        assert norma_dobowa(orzeczenie=False) == 455

    def test_orzeczenie_nie_zmienia_kodu_z_liczba(self):
        # Liczba godzin jest podana wprost – orzeczenie nie ma tu nic do rzeczy
        assert minuty_absencji("U12", orzeczenie=True) == 720

    def test_kod_nie_bedacy_absencja_daje_zero(self):
        for kod in ("", "D", "N", "UX"):
            assert minuty_absencji(kod) == 0


class TestSumaWMiesiacu:
    def test_sumuje_tylko_dni_z_zakresu(self):
        absencje = {
            datetime.date(2026, 5, 4): "U12",
            datetime.date(2026, 5, 5): "U",
            datetime.date(2026, 6, 1): "U12",   # inny miesiąc – pomijany
        }
        dni_maja = [datetime.date(2026, 5, d) for d in range(1, 32)]
        assert suma_minut_absencji(absencje, dni_maja) == 720 + 455

    def test_pusta_lista_absencji(self):
        dni = [datetime.date(2026, 5, d) for d in range(1, 32)]
        assert suma_minut_absencji({}, dni) == 0

    def test_uwzglednia_orzeczenie(self):
        absencje = {datetime.date(2026, 5, 4): "U"}
        dni = [datetime.date(2026, 5, 4)]
        assert suma_minut_absencji(absencje, dni, orzeczenie=True) == 420
