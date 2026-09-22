# Ekrany ewidencji: lista pracowników oraz zaznaczanie nieobecności.
#
# Oba ekrany zapisują dane wprost do bazy, więc przetrwają restart aplikacji.

import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from config import SCHEDULE_LABELS, get_schedule_key
from modules.absences import czy_absencja, normalizuj_kod
from modules.db import BrakKonfiguracjiBazy
from modules.repository import (
    ETYKIETY_RODZAJOW,
    NIEDYSPOZYCJA,
    PROSBA_DYZUR,
    PROSBA_WOLNE,
    URLOP,
    usun_nieobecnosc,
    usun_pracownika,
    waliduj_pracownika,
    wczytaj_nieobecnosci,
    wczytaj_pracownikow,
    zapisz_nieobecnosc,
    zapisz_pracownika,
    zapisz_zakres_nieobecnosci,
)
from modules.ui_html import card_head_html, section_title_html

NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]

ODDZIALY = ["wewnętrzny", "gastrologiczny", "oiok", "wewnętrzny/oiok"]
ROLE = ["pielęgniarki", "opiekunki"]
TYPY_UMOWY = ["etat", "duzy_kontrakt", "maly_kontrakt"]

# Skróty wpisywane w siatce nieobecności
POMOC_KODY = (
    "X – niedyspozycja · U, U12, UM8 – urlop (liczba = godziny) · "
    "PW – prośba o wolne · PD / PN – prośba o dyżur dzienny / nocny"
)
WZORZEC_KOMORKI = r"^(|X|PW|PD|PN|U\d{0,2}|UM\d{0,2})$"


def _pokaz_blad_bazy(blad: Exception) -> None:
    st.error(
        "Brak połączenia z bazą danych. Ustaw `DATABASE_URL` w sekretach aplikacji "
        "(lokalnie w `.streamlit/secrets.toml`, na serwerze w ustawieniach Streamlit Cloud)."
    )
    with st.expander("Szczegóły techniczne"):
        st.code(str(blad), language=None)


# Zamiana między wpisem w bazie a skrótem w komórce

def kod_komorki(rodzaj: str, kod: Optional[str]) -> str:
    if rodzaj == NIEDYSPOZYCJA:
        return "X"
    if rodzaj == URLOP:
        return kod or "U"
    if rodzaj == PROSBA_WOLNE:
        return "PW"
    if rodzaj == PROSBA_DYZUR:
        return "P" + (kod or "D")
    return ""


def rozbij_komorke(tekst: str) -> Optional[Tuple[str, Optional[str]]]:
    """Zamienia skrót z komórki na (rodzaj, kod). None gdy pusto lub nieznane."""
    t = str(tekst or "").strip().upper()
    if not t:
        return None
    if t == "X":
        return NIEDYSPOZYCJA, None
    if t == "PW":
        return PROSBA_WOLNE, None
    if t in ("PD", "PN"):
        return PROSBA_DYZUR, t[1]
    if czy_absencja(t):
        return URLOP, normalizuj_kod(t)
    return None


# Ekran: pracownicy

def renderuj_ekran_pracownikow() -> None:
    st.markdown(section_title_html("users", "Pracownicy"), unsafe_allow_html=True)

    try:
        pracownicy, ostrzezenia = wczytaj_pracownikow()
    except (BrakKonfiguracjiBazy, Exception) as e:  # noqa: B014 - czytelny komunikat ważniejszy
        _pokaz_blad_bazy(e)
        return

    for uwaga in ostrzezenia:
        st.warning(uwaga)

    st.caption(
        "Dodawaj wiersze na dole tabeli, poprawiaj dane wprost w komórkach, "
        "a usuwaj zaznaczając wiersz i wciskając Delete. Zapis następuje po kliknięciu przycisku."
    )

    df = pd.DataFrame(
        [
            {
                "Imię i nazwisko": p.imie_nazwisko,
                "Oddział": p.oddzial,
                "Rola": p.rola,
                "Typ umowy": p.typ_umowy,
                "Orzeczenie": p.orzeczenie,
                "Tylko 7h35 (zmiany R)": p.tylko_7h,
                "Pracuje w weekendy": p.pracuje_w_weekendy,
            }
            for p in pracownicy
        ],
        columns=[
            "Imię i nazwisko", "Oddział", "Rola", "Typ umowy",
            "Orzeczenie", "Tylko 7h35 (zmiany R)", "Pracuje w weekendy",
        ],
    )

    edytowany = st.data_editor(
        df,
        key="editor_pracownicy",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Imię i nazwisko": st.column_config.TextColumn(required=True, width="medium"),
            "Oddział": st.column_config.SelectboxColumn(options=ODDZIALY, required=True),
            "Rola": st.column_config.SelectboxColumn(options=ROLE, required=True),
            "Typ umowy": st.column_config.SelectboxColumn(options=TYPY_UMOWY, required=True),
            "Orzeczenie": st.column_config.CheckboxColumn(
                help="Orzeczenie o niepełnosprawności – skraca dobę do 7h"
            ),
            "Tylko 7h35 (zmiany R)": st.column_config.CheckboxColumn(
                help="Pracownik obsługuje wyłącznie zmiany R w dni robocze"
            ),
            "Pracuje w weekendy": st.column_config.CheckboxColumn(),
        },
    )

    if st.button("Zapisz zmiany", type="primary", key="zapisz_pracownikow"):
        _zapisz_pracownikow(df, edytowany)


def _zapisz_pracownikow(przed: pd.DataFrame, po: pd.DataFrame) -> None:
    """Zapisuje dodane i zmienione wiersze, miękko usuwa skasowane."""
    bledy: List[str] = []
    zapisanych = 0

    for _, wiersz in po.iterrows():
        imie = str(wiersz.get("Imię i nazwisko") or "").strip()
        if not imie:
            continue
        dane = {
            "imie_nazwisko": imie,
            "oddzial": wiersz.get("Oddział"),
            "rola": wiersz.get("Rola"),
            "typ_umowy": wiersz.get("Typ umowy"),
            "orzeczenie": bool(wiersz.get("Orzeczenie", False)),
            "tylko_7h": bool(wiersz.get("Tylko 7h35 (zmiany R)", False)),
            "pracuje_w_weekendy": bool(wiersz.get("Pracuje w weekendy", True)),
        }
        problemy = waliduj_pracownika(dane)
        if problemy:
            bledy.append(f"{imie}: {' '.join(problemy)}")
            continue
        try:
            zapisz_pracownika(dane)
            zapisanych += 1
        except Exception as e:
            bledy.append(f"{imie}: {e}")

    usuniete = set(przed["Imię i nazwisko"]) - set(po["Imię i nazwisko"])
    for imie in usuniete:
        try:
            usun_pracownika(imie)
        except Exception as e:
            bledy.append(f"{imie}: nie udało się usunąć – {e}")

    if bledy:
        st.error("Część zmian nie została zapisana:")
        for b in bledy:
            st.write("• " + b)
    if zapisanych or usuniete:
        st.success(
            f"Zapisano {zapisanych} pracowników"
            + (f", usunięto {len(usuniete)}." if usuniete else ".")
        )
        st.rerun()


# Ekran: nieobecności

def renderuj_ekran_nieobecnosci(rok: int, miesiac: int, nazwa_miesiaca: str) -> None:
    st.markdown(
        section_title_html("calendar-heart", f"Nieobecności — {nazwa_miesiaca} {rok}"),
        unsafe_allow_html=True,
    )

    try:
        pracownicy, _ = wczytaj_pracownikow()
        wpisy = wczytaj_nieobecnosci(rok, miesiac)
    except Exception as e:
        _pokaz_blad_bazy(e)
        return

    if not pracownicy:
        st.info("Najpierw dodaj pracowników na ekranie „Pracownicy”.")
        return

    _formularz_zakresu(pracownicy, rok, miesiac)
    _siatka_miesiaca(pracownicy, wpisy, rok, miesiac)


def _formularz_zakresu(pracownicy: list, rok: int, miesiac: int) -> None:
    """Szybkie zaznaczenie dłuższego okresu – np. dwutygodniowego urlopu."""
    with st.container(border=True):
        st.markdown(
            card_head_html("calendar-days", "Zaznacz okres",
                           "Wygodne przy urlopach ciągnących się przez wiele dni"),
            unsafe_allow_html=True,
        )
        kol1, kol2 = st.columns(2)
        with kol1:
            osoba = st.selectbox(
                "Pracownik", [p.imie_nazwisko for p in pracownicy], key="zakres_osoba"
            )
            rodzaj = st.selectbox(
                "Rodzaj",
                list(ETYKIETY_RODZAJOW),
                format_func=lambda r: ETYKIETY_RODZAJOW[r],
                key="zakres_rodzaj",
            )
        with kol2:
            import calendar

            ostatni = calendar.monthrange(rok, miesiac)[1]
            od = st.date_input(
                "Od", value=datetime.date(rok, miesiac, 1),
                min_value=datetime.date(rok, miesiac, 1),
                max_value=datetime.date(rok, miesiac, ostatni), key="zakres_od",
            )
            do = st.date_input(
                "Do", value=datetime.date(rok, miesiac, min(7, ostatni)),
                min_value=datetime.date(rok, miesiac, 1),
                max_value=datetime.date(rok, miesiac, ostatni), key="zakres_do",
            )

        kod = None
        if rodzaj == URLOP:
            kod = st.text_input(
                "Kod urlopu", value="U",
                help="U = pełna norma dobowa, U12 = 12 godzin", key="zakres_kod",
            )
            if not czy_absencja(kod):
                st.warning("Niepoprawny kod urlopu. Poprawne: U, U8, U12, UM, UM8.")
        elif rodzaj == PROSBA_DYZUR:
            kod = st.selectbox("Jaki dyżur", ["D", "N"], key="zakres_kod_dyzur")

        if st.button("Zaznacz okres", type="primary", key="zakres_zapisz"):
            if rodzaj == URLOP and not czy_absencja(kod):
                st.error("Popraw kod urlopu przed zapisem.")
                return
            try:
                ile = zapisz_zakres_nieobecnosci(
                    osoba, od, do, rodzaj,
                    normalizuj_kod(kod) if rodzaj == URLOP else kod,
                )
                st.success(f"Zaznaczono {ile} dni dla: {osoba}.")
                st.rerun()
            except Exception as e:
                st.error(f"Nie udało się zapisać: {e}")


def _siatka_miesiaca(pracownicy: list, wpisy: List[dict], rok: int, miesiac: int) -> None:
    import calendar

    ostatni = calendar.monthrange(rok, miesiac)[1]
    dni = [datetime.date(rok, miesiac, d) for d in range(1, ostatni + 1)]
    kolumny = [f"{NAZWY_DNI[d.weekday()]} {d.day}" for d in dni]
    kolumna_dla_daty = dict(zip(dni, kolumny))

    grupy = sorted({p.schedule_key for p in pracownicy})
    wybrana = st.selectbox(
        "Grupa", grupy, format_func=lambda k: SCHEDULE_LABELS.get(k, k), key="siatka_grupa"
    )
    widoczni = [p for p in pracownicy if p.schedule_key == wybrana]

    biezace: Dict[str, Dict[str, str]] = {p.imie_nazwisko: {} for p in widoczni}
    for wpis in wpisy:
        imie = wpis["imie_nazwisko"]
        if imie in biezace and wpis["data"] in kolumna_dla_daty:
            biezace[imie][kolumna_dla_daty[wpis["data"]]] = kod_komorki(
                wpis["rodzaj"], wpis["kod"]
            )

    df = pd.DataFrame(
        [
            {"Imię i nazwisko": p.imie_nazwisko,
             **{k: biezace[p.imie_nazwisko].get(k, "") for k in kolumny}}
            for p in widoczni
        ],
        columns=["Imię i nazwisko"] + kolumny,
    )

    st.caption(POMOC_KODY)
    konfiguracja = {
        "Imię i nazwisko": st.column_config.TextColumn(disabled=True, width="medium")
    }
    for k in kolumny:
        konfiguracja[k] = st.column_config.TextColumn(
            label=k, width="small", validate=WZORZEC_KOMORKI, help=POMOC_KODY
        )

    edytowany = st.data_editor(
        df, key=f"editor_nieobecnosci_{wybrana}", use_container_width=True,
        hide_index=True, num_rows="fixed", column_config=konfiguracja,
    )

    if st.button("Zapisz nieobecności", type="primary", key=f"zapisz_nieob_{wybrana}"):
        _zapisz_siatke(df, edytowany, kolumna_dla_daty)


def _zapisz_siatke(
    przed: pd.DataFrame,
    po: pd.DataFrame,
    kolumna_dla_daty: Dict[datetime.date, str],
) -> None:
    """Zapisuje wyłącznie komórki, które faktycznie się zmieniły."""
    data_dla_kolumny = {kol: data for data, kol in kolumna_dla_daty.items()}
    zmian = 0
    bledy: List[str] = []

    for indeks, wiersz in po.iterrows():
        imie = wiersz["Imię i nazwisko"]
        for kolumna, data in data_dla_kolumny.items():
            stara = str(przed.at[indeks, kolumna] or "").strip().upper()
            nowa = str(wiersz.get(kolumna) or "").strip().upper()
            if stara == nowa:
                continue

            try:
                if stara:
                    rozbita = rozbij_komorke(stara)
                    if rozbita:
                        usun_nieobecnosc(imie, data, rozbita[0])
                if nowa:
                    rozbita = rozbij_komorke(nowa)
                    if rozbita is None:
                        bledy.append(f"{imie}, {data}: nieznany kod „{nowa}”.")
                        continue
                    zapisz_nieobecnosc(imie, data, rozbita[0], rozbita[1])
                zmian += 1
            except Exception as e:
                bledy.append(f"{imie}, {data}: {e}")

    for b in bledy:
        st.error(b)
    if zmian:
        st.success(f"Zapisano zmian: {zmian}.")
        st.rerun()
    elif not bledy:
        st.info("Nie wykryto zmian do zapisania.")
