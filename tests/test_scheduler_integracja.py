"""Test integracyjny: pełna generacja na prawdziwych danych personelu.

Sprawdza reguły, których nie da się potwierdzić w izolacji – czy algorytm
faktycznie ich przestrzega po przejściu wszystkich sześciu faz, łącznie z fazą
awaryjną, która kiedyś omijała główną bramkę ograniczeń.
"""

import datetime
from pathlib import Path

import pytest

from config import NIGHT_SHIFTS, WORKING_SHIFTS
from modules.data_loader import grupuj_wg_harmonogramu, wczytaj_personel
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy

CSV_PERSONEL = Path(__file__).resolve().parent.parent / "personel_wlasciwy.csv"


@pytest.fixture(scope="module")
def harmonogramy():
    if not CSV_PERSONEL.exists():
        pytest.skip(f"Brak pliku z danymi: {CSV_PERSONEL}")
    pracownicy, _ = wczytaj_personel(str(CSV_PERSONEL))
    info = get_month_info(2026, 5)
    return (
        generuj_wszystkie_harmonogramy(
            grupy=grupuj_wg_harmonogramu(pracownicy),
            rok=2026,
            miesiac=5,
            dni=info["dni"],
            swieta=info["swieta"],
            liczba_dni_roboczych=info["liczba_dni_roboczych"],
        ),
        info,
    )


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


def test_generacja_nie_wyrzuca_wyjatku(harmonogramy):
    stany, _ = harmonogramy
    assert stany, "Nie wygenerowano żadnego harmonogramu"


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


def test_nikt_nie_ma_dwoch_zmian_tego_samego_dnia(harmonogramy):
    stany, info = harmonogramy
    for state in stany.values():
        for p in state.pracownicy:
            przydzial = state.przydzial[p.imie_nazwisko]
            for data, kod in przydzial.items():
                assert isinstance(kod, str)
            # słownik z definicji ma jeden kod na dzień – sprawdzamy zakres dat
            assert set(przydzial).issubset(set(info["dni"]))
