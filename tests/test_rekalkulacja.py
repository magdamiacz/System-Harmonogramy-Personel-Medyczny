"""Testy przeliczania grafiku po ręcznej edycji tabeli.

Najważniejszy przypadek: wpisanie urlopu wprost w komórce ma pomniejszyć
normatyw. Wcześniej funkcja odtwarzała przydziały na starych normatywach,
więc ręczny urlop nie miał żadnego wpływu na bilans.
"""

import datetime

import pytest

from config import WORKING_SHIFTS, get_schedule_key
from modules.data_loader import Pracownik, grupuj_wg_harmonogramu
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy
from modules.ui_components import buduj_df_do_edycji, rekalkuluj_state_po_edycji

DZIEN_URLOPU = datetime.date(2026, 5, 12)


def zespol(ilu: int = 8) -> list:
    return [
        Pracownik(
            imie_nazwisko=f"Osoba {n:02d}",
            oddzial="wewnętrzny",
            rola="pielęgniarki",
            typ_umowy="etat",
            orzeczenie=False,
            tylko_7h=False,
            pracuje_w_weekendy=True,
            schedule_key=get_schedule_key("wewnętrzny", "pielęgniarki"),
        )
        for n in range(1, ilu + 1)
    ]


@pytest.fixture
def kontekst():
    info = get_month_info(2026, 5)
    stany = generuj_wszystkie_harmonogramy(
        grupy=grupuj_wg_harmonogramu(zespol()),
        rok=2026,
        miesiac=5,
        dni=info["dni"],
        swieta=info["swieta"],
        liczba_dni_roboczych=info["liczba_dni_roboczych"],
    )
    return stany["wew_piel"], info


def kolumna_dnia(data: datetime.date) -> str:
    return f"{['Pn','Wt','Śr','Cz','Pt','So','Nd'][data.weekday()]} {data.day}"


def wpisz(state, info, imie: str, data: datetime.date, kod: str):
    """Symuluje ręczną edycję jednej komórki w tabeli."""
    df = buduj_df_do_edycji(state, info["dni"], info["swieta"])
    df.loc[df["Imię i nazwisko"] == imie, kolumna_dnia(data)] = kod
    return rekalkuluj_state_po_edycji(state, df, info["dni"])


class TestUrlopWpisanyRecznie:
    def test_urlop_pomniejsza_normatyw(self, kontekst):
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko
        przed = state.normatywy[imie].minuty

        po = wpisz(state, info, imie, DZIEN_URLOPU, "U12")
        assert po.normatywy[imie].minuty == przed - 720
        assert po.normatywy[imie].minuty_absencji == 720

    def test_samo_U_pomniejsza_o_norme_dobowa(self, kontekst):
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko
        przed = state.normatywy[imie].minuty

        po = wpisz(state, info, imie, DZIEN_URLOPU, "U")
        assert po.normatywy[imie].minuty == przed - 455

    def test_urlop_nie_liczy_sie_jako_praca(self, kontekst):
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko
        po = wpisz(state, info, imie, DZIEN_URLOPU, "U12")
        assert po.get_przydzial(imie, DZIEN_URLOPU) == "U12"
        assert po.get_przydzial(imie, DZIEN_URLOPU) not in WORKING_SHIFTS

    def test_urlop_jednej_osoby_nie_rusza_pozostalych(self, kontekst):
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko
        inna = state.pracownicy[1].imie_nazwisko
        przed_inna = state.normatywy[inna].minuty

        po = wpisz(state, info, imie, DZIEN_URLOPU, "U12")
        assert po.normatywy[inna].minuty == przed_inna


class TestZwykleEdycje:
    def test_wpisanie_dyzuru_podbija_przepracowane(self, kontekst):
        state, info = kontekst
        # znajdź osobę i dzień bez przydziału
        imie = state.pracownicy[0].imie_nazwisko
        wolny = next(
            d for d in info["dni"] if state.get_przydzial(imie, d) == ""
        )
        przed = state.przepracowane[imie]

        po = wpisz(state, info, imie, wolny, "D")
        assert po.get_przydzial(imie, wolny) == "D"
        assert po.przepracowane[imie] == przed + 720

    def test_male_litery_sa_akceptowane(self, kontekst):
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko
        po = wpisz(state, info, imie, DZIEN_URLOPU, "u12")
        assert po.get_przydzial(imie, DZIEN_URLOPU) == "U12"

    def test_liczniki_nie_kumuluja_sie_przy_kolejnych_edycjach(self, kontekst):
        """Dwie edycje z rzędu nie mogą podwoić przepracowanych godzin."""
        state, info = kontekst
        imie = state.pracownicy[0].imie_nazwisko

        po_pierwszej = wpisz(state, info, imie, DZIEN_URLOPU, "U12")
        suma_po_pierwszej = po_pierwszej.przepracowane[imie]
        po_drugiej = wpisz(po_pierwszej, info, imie, DZIEN_URLOPU, "U12")
        assert po_drugiej.przepracowane[imie] == suma_po_pierwszej


class TestKolorowanieKodow:
    """Kody urlopu z liczbą godzin muszą dostawać kolor swojego rodzaju."""

    def test_urlop_z_godzinami_ma_kolor_urlopu(self):
        from modules.theme import SHIFT_COLORS
        from modules.ui_components import _kolor_kodu

        assert _kolor_kodu("U12") == SHIFT_COLORS["U"]
        assert _kolor_kodu("U") == SHIFT_COLORS["U"]
        assert _kolor_kodu("UM8") == SHIFT_COLORS["UM"]

    def test_zwykle_kody_zmian_bez_zmian(self):
        from modules.theme import SHIFT_COLORS
        from modules.ui_components import _kolor_kodu

        for kod in ("D", "N", "DN", "R", "DK", "W"):
            assert _kolor_kodu(kod) == SHIFT_COLORS[kod]

    def test_pusty_i_nieznany_kod_bez_koloru(self):
        from modules.ui_components import _kolor_kodu

        assert _kolor_kodu("") == ""
        assert _kolor_kodu("XYZ") == ""
