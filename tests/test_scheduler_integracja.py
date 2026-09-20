"""Test integracyjny: pełna generacja na syntetycznym zespole.

Sprawdza reguły, których nie da się potwierdzić w izolacji – czy algorytm
faktycznie ich przestrzega po przejściu wszystkich sześciu faz, łącznie z fazą
awaryjną, która kiedyś omijała główną bramkę ograniczeń.

Zespół jest wymyślony, ale liczebnością i strukturą umów odwzorowuje prawdziwy,
żeby reguła nocek była realnie obciążona. Testy celowo nie korzystają z pliku
z prawdziwymi nazwiskami – to dane osobowe personelu.
"""

import datetime

import pytest

from config import NIGHT_SHIFTS, WORKING_SHIFTS, get_schedule_key
from modules.data_loader import Pracownik, grupuj_wg_harmonogramu
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy

# (oddział, rola, liczba etatów, dużych kontraktów, małych kontraktów, ilu tylko_7h)
SKLAD_ZESPOLU = [
    ("wewnętrzny",      "pielęgniarki", 7,  3, 3, 1),
    ("gastrologiczny",  "pielęgniarki", 10, 2, 0, 1),
    ("gastrologiczny",  "opiekunki",    6,  0, 0, 0),
    ("oiok",            "pielęgniarki", 5,  1, 2, 1),
    ("wewnętrzny/oiok", "opiekunki",    12, 0, 0, 0),
]


def zbuduj_zespol() -> list:
    pracownicy = []
    licznik = 0
    for oddzial, rola, etaty, duze, male, tylko_7h_ilu in SKLAD_ZESPOLU:
        typy = ["etat"] * etaty + ["duzy_kontrakt"] * duze + ["maly_kontrakt"] * male
        for numer, typ in enumerate(typy):
            licznik += 1
            pracownicy.append(
                Pracownik(
                    imie_nazwisko=f"Osoba {licznik:03d}",
                    oddzial=oddzial,
                    rola=rola,
                    typ_umowy=typ,
                    orzeczenie=False,
                    # tylko_7h dotyczy wyłącznie etatowców – tak jest w prawdziwych danych
                    tylko_7h=(typ == "etat" and numer < tylko_7h_ilu),
                    pracuje_w_weekendy=True,
                    schedule_key=get_schedule_key(oddzial, rola),
                )
            )
    return pracownicy


@pytest.fixture(scope="module")
def harmonogramy():
    info = get_month_info(2026, 5)
    stany = generuj_wszystkie_harmonogramy(
        grupy=grupuj_wg_harmonogramu(zbuduj_zespol()),
        rok=2026,
        miesiac=5,
        dni=info["dni"],
        swieta=info["swieta"],
        liczba_dni_roboczych=info["liczba_dni_roboczych"],
    )
    return stany, info


def serie_nocek(przydzial: dict, dni: list) -> list:
    """Zwraca długości wszystkich serii kolejnych nocy."""
    serie, biezaca = [], 0
    for dzien in dni:
        if przydzial.get(dzien, "") in NIGHT_SHIFTS:
            biezaca += 1
        else:
            if biezaca:
                serie.append(biezaca)
            biezaca = 0
    if biezaca:
        serie.append(biezaca)
    return serie


def test_generuje_harmonogram_dla_kazdej_grupy(harmonogramy):
    stany, _ = harmonogramy
    assert len(stany) == len(SKLAD_ZESPOLU)


def test_ktos_faktycznie_dostal_nocki(harmonogramy):
    """Zabezpiecza pozostałe testy – na pustym grafiku przeszłyby bez sensu."""
    stany, info = harmonogramy
    wszystkie = [
        dlugosc
        for state in stany.values()
        for p in state.pracownicy
        for dlugosc in serie_nocek(state.przydzial[p.imie_nazwisko], info["dni"])
    ]
    assert wszystkie, "Nikt nie dostał ani jednej nocki – test nic by nie sprawdzał"


def test_nikt_nie_ma_trzech_nocek_pod_rzad(harmonogramy):
    stany, info = harmonogramy
    winni = []
    for klucz, state in stany.items():
        for p in state.pracownicy:
            najdluzsza = max(
                serie_nocek(state.przydzial[p.imie_nazwisko], info["dni"]), default=0
            )
            if najdluzsza > 2:
                winni.append(f"{klucz}/{p.imie_nazwisko}: {najdluzsza} nocek pod rząd")
    assert not winni, "Naruszenia reguły nocek:\n" + "\n".join(winni)


def test_po_serii_nocek_sa_dwa_dni_wolne(harmonogramy):
    stany, info = harmonogramy
    dzien = datetime.timedelta(days=1)
    winni = []
    for klucz, state in stany.items():
        for p in state.pracownicy:
            przydzial = state.przydzial[p.imie_nazwisko]
            for data in info["dni"]:
                czy_noc = przydzial.get(data, "") in NIGHT_SHIFTS
                czy_koniec_serii = czy_noc and przydzial.get(data + dzien, "") not in NIGHT_SHIFTS
                if not czy_koniec_serii:
                    continue
                for odstep in (1, 2):
                    nastepny = data + dzien * odstep
                    if nastepny not in info["dni"]:
                        continue
                    if przydzial.get(nastepny, "") in WORKING_SHIFTS:
                        winni.append(
                            f"{klucz}/{p.imie_nazwisko}: praca {nastepny} "
                            f"tylko {odstep} dni po nocce {data}"
                        )
    assert not winni, "Za krótki odpoczynek po nockach:\n" + "\n".join(winni[:15])


def test_etatowcy_nie_przekraczaja_normatywu(harmonogramy):
    """Decyzja użytkowniczki: nadgodziny wolno mieć wyłącznie kontraktowcom."""
    stany, _ = harmonogramy
    winni = []
    for klucz, state in stany.items():
        for p in state.pracownicy:
            if not p.is_etat:
                continue
            przepracowane = state.przepracowane[p.imie_nazwisko]
            normatyw = state.normatywy[p.imie_nazwisko].minuty
            if przepracowane > normatyw:
                winni.append(
                    f"{klucz}/{p.imie_nazwisko}: {przepracowane} min > normatyw {normatyw} min"
                )
    assert not winni, "Etatowcy z nadgodzinami:\n" + "\n".join(winni)


def test_przydzialy_miesczą_sie_w_miesiacu(harmonogramy):
    stany, info = harmonogramy
    for state in stany.values():
        for p in state.pracownicy:
            assert set(state.przydzial[p.imie_nazwisko]).issubset(set(info["dni"]))


class TestUrlopWCalejSciezce:
    """Urlop wpisany pracownikowi ma zejść z normatywu i zablokować dzień."""

    @staticmethod
    def wygeneruj(absencje: dict):
        zespol = zbuduj_zespol()
        urlopowicz = next(p for p in zespol if p.is_etat and not p.tylko_7h)
        urlopowicz.absencje = dict(absencje)
        info = get_month_info(2026, 5)
        stany = generuj_wszystkie_harmonogramy(
            grupy=grupuj_wg_harmonogramu(zespol),
            rok=2026,
            miesiac=5,
            dni=info["dni"],
            swieta=info["swieta"],
            liczba_dni_roboczych=info["liczba_dni_roboczych"],
        )
        state = stany[urlopowicz.schedule_key]
        return state, urlopowicz.imie_nazwisko, info

    def test_urlop_obniza_normatyw_o_wpisane_godziny(self):
        dzien = datetime.date(2026, 5, 12)
        bez, imie, _ = self.wygeneruj({})
        z_urlopem, _, _ = self.wygeneruj({dzien: "U12"})
        assert z_urlopem.normatywy[imie].minuty == bez.normatywy[imie].minuty - 720
        assert z_urlopem.normatywy[imie].minuty_absencji == 720

    def test_dzien_urlopu_widnieje_w_grafiku(self):
        dzien = datetime.date(2026, 5, 12)
        state, imie, _ = self.wygeneruj({dzien: "U12"})
        assert state.get_przydzial(imie, dzien) == "U12"

    def test_w_dniu_urlopu_nie_ma_dyzuru(self):
        dzien = datetime.date(2026, 5, 12)
        state, imie, _ = self.wygeneruj({dzien: "U12"})
        assert state.get_przydzial(imie, dzien) not in WORKING_SHIFTS

    def test_urlop_nie_zwieksza_przepracowanych_godzin(self):
        """Urlop schodzi z normatywu – nie wolno go liczyć jako pracy."""
        dzien = datetime.date(2026, 5, 12)
        state, imie, info = self.wygeneruj({dzien: "U12"})
        z_dyzurow = sum(
            1 for kod in state.przydzial[imie].values() if kod in WORKING_SHIFTS
        )
        # przepracowane liczone tylko z dyżurów; U12 nie może ich podbić
        assert state.przepracowane[imie] <= z_dyzurow * 720

    def test_samo_U_zdejmuje_norme_dobowa(self):
        dzien = datetime.date(2026, 5, 12)
        bez, imie, _ = self.wygeneruj({})
        z_urlopem, _, _ = self.wygeneruj({dzien: "U"})
        assert z_urlopem.normatywy[imie].minuty == bez.normatywy[imie].minuty - 455
