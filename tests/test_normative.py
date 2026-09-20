"""Testy normatywu miesięcznego pomniejszanego o godziny urlopu."""

import pytest

from config import get_schedule_key
from modules.data_loader import Pracownik
from modules.normative import oblicz_normatyw, oblicz_normatywy


def zrob_pracownika(
    imie="Testowa Anna",
    typ_umowy="etat",
    orzeczenie=False,
    tylko_7h=False,
) -> Pracownik:
    return Pracownik(
        imie_nazwisko=imie,
        oddzial="wewnętrzny",
        rola="pielęgniarki",
        typ_umowy=typ_umowy,
        orzeczenie=orzeczenie,
        tylko_7h=tylko_7h,
        pracuje_w_weekendy=True,
        schedule_key=get_schedule_key("wewnętrzny", "pielęgniarki"),
    )


class TestBezUrlopu:
    def test_etat_bez_zmian_gdy_brak_argumentu(self):
        # 22 dni robocze × 455 min = 10010 min = 166h50min
        n = oblicz_normatyw(zrob_pracownika(), 22)
        assert n.minuty == 10010
        assert n.godziny_str == "166h50min"
        assert n.minuty_absencji == 0
        assert n.minuty_bazowe == 10010

    def test_orzeczenie_skraca_dobe(self):
        n = oblicz_normatyw(zrob_pracownika(orzeczenie=True), 22)
        assert n.minuty == 22 * 420

    def test_tylko_7h_bez_rozkladu_na_dyzury(self):
        n = oblicz_normatyw(zrob_pracownika(tylko_7h=True), 22)
        assert n.pelne_dyzury_12h == 0
        assert n.koncowka_minuty == 0

    def test_kontrakty_maja_minimum_umowne(self):
        assert oblicz_normatyw(zrob_pracownika(typ_umowy="duzy_kontrakt"), 22).minuty == 9600
        assert oblicz_normatyw(zrob_pracownika(typ_umowy="maly_kontrakt"), 22).minuty == 7200


class TestUrlopObnizaNormatyw:
    def test_przyklad_z_wymagania(self):
        """166h50min minus jeden dzień U12 daje 154h50min."""
        n = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=720)
        assert n.minuty == 10010 - 720
        assert n.godziny_str == "154h50min"
        assert n.minuty_bazowe == 10010
        assert n.minuty_absencji == 720

    def test_pelny_dyzur_urlopu_zabiera_jeden_dyzur_a_nie_koncowke(self):
        """Urlop równy 12h zdejmuje jeden pełny dyżur; reszta z dzielenia się nie zmienia."""
        bez = oblicz_normatyw(zrob_pracownika(), 22)
        z_urlopem = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=720)
        assert (bez.pelne_dyzury_12h, bez.koncowka_minuty) == (13, 650)
        assert (z_urlopem.pelne_dyzury_12h, z_urlopem.koncowka_minuty) == (12, 650)

    def test_urlop_niepelnodyzurowy_skraca_koncowke_DK(self):
        """Końcówka to reszta z dzielenia przez 720, więc urlop 7h35 ją przelicza."""
        n = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=455)
        assert n.minuty == 9555
        assert n.pelne_dyzury_12h == 13
        assert n.koncowka_minuty == 195          # 9555 = 13×720 + 195
        assert n.koncowka_str == "3h15min"

    def test_wielokrotnosc_dyzuru_daje_zerowa_koncowke(self):
        n = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=10010 - 8640)
        assert n.minuty == 8640                  # 12 × 720
        assert n.pelne_dyzury_12h == 12
        assert n.koncowka_minuty == 0
        assert n.koncowka_str == "—"

    def test_urlop_wiekszy_niz_normatyw_zeruje_wszystko(self):
        n = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=99999)
        assert n.minuty == 0
        assert n.pelne_dyzury_12h == 0
        assert n.koncowka_minuty == 0

    def test_ujemny_urlop_traktowany_jak_zero(self):
        n = oblicz_normatyw(zrob_pracownika(), 22, minuty_absencji=-500)
        assert n.minuty == 10010

    @pytest.mark.parametrize("typ", ["duzy_kontrakt", "maly_kontrakt"])
    def test_urlop_obniza_takze_kontrakty(self, typ):
        """Decyzja użytkowniczki: urlop obniża wymagane godziny wszystkim."""
        bazowy = oblicz_normatyw(zrob_pracownika(typ_umowy=typ), 22).minuty
        n = oblicz_normatyw(zrob_pracownika(typ_umowy=typ), 22, minuty_absencji=720)
        assert n.minuty == bazowy - 720


class TestNormatywyGrupy:
    def test_mapuje_urlopy_po_nazwisku(self):
        ludzie = [zrob_pracownika("Anna A"), zrob_pracownika("Barbara B")]
        wynik = oblicz_normatywy(ludzie, 22, {"Anna A": 720})
        assert wynik["Anna A"].minuty == 10010 - 720
        assert wynik["Barbara B"].minuty == 10010

    def test_brak_argumentu_nie_zmienia_wynikow(self):
        ludzie = [zrob_pracownika("Anna A")]
        assert oblicz_normatywy(ludzie, 22)["Anna A"].minuty == 10010

    def test_nieznane_nazwisko_w_mapie_jest_ignorowane(self):
        ludzie = [zrob_pracownika("Anna A")]
        wynik = oblicz_normatywy(ludzie, 22, {"Ktos Inny": 720})
        assert wynik["Anna A"].minuty == 10010
