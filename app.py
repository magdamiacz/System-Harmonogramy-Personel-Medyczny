# Główna aplikacja Streamlit – Zautomatyzowany System Generowania Harmonogramów
# Uruchamianie: streamlit run app.py

import datetime
import sys
import os

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SCHEDULE_KEYS, SCHEDULE_LABELS, WORK_MINUTES_PER_DAY_STANDARD
from modules.normative import _minuty_na_str
from modules.data_loader import grupuj_wg_harmonogramu
from modules.repository import wczytaj_pracownikow
from modules.ui_ewidencja import renderuj_ekran_nieobecnosci, renderuj_ekran_pracownikow
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy
from modules.icons import logo_svg
from modules.theme import inject_global_css, inject_login_css
from modules.ui_components import eksportuj_harmonogram, renderuj_harmonogram, renderuj_podsumowanie
from modules.ui_html import (
    brand_html,
    card_head_html,
    date_chips_html,
    hero_html,
    login_head_html,
    section_title_html,
    stat_cards_html,
)


# Konfiguracja strony

st.set_page_config(
    page_title="Harmonogram pracy – personel medyczny",
    page_icon=logo_svg(64, "fav"),
    layout="wide",
    initial_sidebar_state="auto",
)

inject_global_css()


# Diagnostyka wersji bibliotek – widoczna wyłącznie po dopisaniu ?diag=1 do adresu.
# Służy potwierdzeniu, że serwer faktycznie instaluje requirements.txt.
# TYMCZASOWE – usunąć po weryfikacji wdrożenia bazy danych.
if st.query_params.get("diag"):
    import importlib

    wersje = []
    for nazwa in ("streamlit", "pandas", "openpyxl", "psycopg"):
        try:
            wersje.append(f"{nazwa} {importlib.import_module(nazwa).__version__}")
        except Exception as e:
            wersje.append(f"{nazwa} BRAK ({type(e).__name__})")
    st.code(" | ".join(wersje), language=None)


MIESIACE_PL = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
]

# Ekrany aplikacji
WIDOK_GRAFIK = "Grafik"
WIDOK_PRACOWNICY = "Pracownicy"
WIDOK_NIEOBECNOSCI = "Nieobecności"
WIDOKI = [WIDOK_GRAFIK, WIDOK_PRACOWNICY, WIDOK_NIEOBECNOSCI]


# Login screen
def show_login():
    inject_login_css()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(login_head_html(), unsafe_allow_html=True)

        username = st.text_input("Login", placeholder="Wpisz login")
        password = st.text_input("Hasło", type="password", placeholder="Wpisz hasło")

        if st.button("Zaloguj się", use_container_width=True, type="primary"):
            correct_username = st.secrets.get("USERNAME", "pielegniarki")
            correct_password = st.secrets.get("PASSWORD", "harmonogram2024")

            if username == correct_username and password == correct_password:
                st.session_state["logged_in"] = True
                st.success("Zalogowano pomyślnie!")
                st.rerun()
            else:
                st.error("Niepoprawny login lub hasło")


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False


if not st.session_state["logged_in"]:
    show_login()
    st.stop()


st.markdown(
    hero_html(
        "Zautomatyzowany System Generowania Harmonogramów Pracy",
        "Personel medyczny · Algorytm zachłanny",
    ),
    unsafe_allow_html=True,
)

# Sidebar: parametry i import danych

with st.sidebar:
    st.markdown(brand_html(), unsafe_allow_html=True)

    widok = st.radio(
        "Widok",
        WIDOKI,
        key="widok",
        label_visibility="collapsed",
    )

    with st.container(border=True):
        st.markdown(card_head_html("calendar-days", "Parametry"), unsafe_allow_html=True)

        # Wybór miesiąca i roku
        teraz = datetime.date.today()
        rok = st.number_input(
            "Rok",
            min_value=2024,
            max_value=2030,
            value=teraz.year,
            step=1,
            key="rok",
        )
        miesiac = st.selectbox(
            "Miesiąc",
            options=list(range(1, 13)),
            format_func=lambda m: MIESIACE_PL[m - 1],
            index=teraz.month - 1,
            key="miesiac",
        )

    st.divider()

    # Przycisk generowania – tylko na ekranie grafiku
    generuj_btn = False
    if widok == WIDOK_GRAFIK:
        generuj_btn = st.button(
            "Generuj harmonogram",
            type="primary",
            use_container_width=True,
            key="generuj_btn",
        )

    # Wylogowanie
    if st.button("Wyloguj się", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()


# Przełączanie ekranów

if widok == WIDOK_PRACOWNICY:
    renderuj_ekran_pracownikow()
    st.stop()

if widok == WIDOK_NIEOBECNOSCI:
    renderuj_ekran_nieobecnosci(int(rok), int(miesiac), MIESIACE_PL[int(miesiac) - 1])
    st.stop()


# Główna logika: wczytaj dane i wygeneruj harmonogram

# Przechowuj wygenerowane harmonogramy w session_state
if "harmonogramy" not in st.session_state:
    st.session_state["harmonogramy"] = {}
if "info_miesiaca" not in st.session_state:
    st.session_state["info_miesiaca"] = None


def wczytaj_i_generuj(rok: int, miesiac: int):
    """Wczytuje pracowników z bazy i uruchamia generator harmonogramów."""
    try:
        pracownicy, bledy_all = wczytaj_pracownikow(int(rok), int(miesiac))
    except Exception as e:
        st.error(
            "Nie udało się pobrać danych z bazy. Sprawdź, czy `DATABASE_URL` jest "
            "ustawiony w sekretach aplikacji."
        )
        with st.expander("Szczegóły techniczne"):
            st.code(str(e), language=None)
        return None, None

    if not pracownicy:
        st.error("W bazie nie ma żadnych pracowników. Dodaj ich na ekranie „Pracownicy”.")
        return None, None

    # Pokaż ostrzeżenia
    if bledy_all:
        with st.expander(f"Ostrzeżenia wczytywania ({len(bledy_all)})", expanded=False):
            for b in bledy_all:
                st.warning(b)

    # Informacje o miesiącu
    info = get_month_info(int(rok), int(miesiac))

    # Grupuj pracowników wg harmonogramu
    grupy = grupuj_wg_harmonogramu(pracownicy)

    # Wygeneruj harmonogramy
    with st.spinner("Generowanie harmonogramów..."):
        harmonogramy = generuj_wszystkie_harmonogramy(
            grupy=grupy,
            rok=int(rok),
            miesiac=int(miesiac),
            dni=info["dni"],
            swieta=info["swieta"],
            liczba_dni_roboczych=info["liczba_dni_roboczych"],
        )

    return harmonogramy, info


# Obsługa przycisku generowania
if generuj_btn:
    harmonogramy, info = wczytaj_i_generuj(rok=rok, miesiac=miesiac)
    if harmonogramy is not None:
        st.session_state["harmonogramy"] = harmonogramy
        st.session_state["info_miesiaca"] = info
        braki = sum(len(state.braki) for state in harmonogramy.values())
        st.success(
            f"Harmonogram wygenerowany dla {info['liczba_dni']} dni "
            f"({info['liczba_dni_roboczych']} dni roboczych)."
        )
        if braki:
            st.warning(
                f"W {braki} miejscach nie udało się zebrać pełnej obsady — "
                "szczegóły przy poszczególnych grafikach poniżej."
            )


# Wyświetlanie harmonogramów w zakładkach

harmonogramy = st.session_state.get("harmonogramy", {})
info = st.session_state.get("info_miesiaca")

if not harmonogramy:
    # Ekran powitalny przed wygenerowaniem
    st.markdown(section_title_html("clipboard-list", "Zacznij tutaj"), unsafe_allow_html=True)
    st.info(
        "Wybierz miesiąc w panelu bocznym i kliknij **Generuj harmonogram**, "
        "aby zobaczyć rozkład zmian."
    )

    with st.expander("Skąd system bierze dane?"):
        st.markdown(
            "- **Pracownicy** — ekran „Pracownicy” w panelu bocznym. Dane zapisują się "
            "w bazie, więc wpisujesz je raz.\n"
            "- **Niedyspozycje, urlopy i prośby** — ekran „Nieobecności”, osobno dla "
            "każdego miesiąca. Algorytm uwzględnia je przy układaniu grafiku.\n"
            "- **Urlop godzinowy** — wpisz `U12`, aby odjąć 12 godzin od normatywu. "
            "Samo `U` odejmuje pełną normę dobową."
        )
else:
    # Metadane miesiąca (normatyw = dni_robocze × 7h35min)
    nazwa_miesiaca = f"{MIESIACE_PL[int(miesiac) - 1]} {rok}"
    normatyw_str = _minuty_na_str(info["liczba_dni_roboczych"] * WORK_MINUTES_PER_DAY_STANDARD)

    st.markdown(
        stat_cards_html([
            ("calendar-days", "Miesiąc", nazwa_miesiaca),
            ("briefcase", "Dni robocze", info["liczba_dni_roboczych"]),
            ("clock", "Normatyw etat", normatyw_str),
        ]),
        unsafe_allow_html=True,
    )

    # Listowanie świąt w miesiącu
    swieta_w_miesiacu = sorted([
        d for d in info["swieta"]
        if d.month == int(miesiac) and d.year == int(rok)
    ])
    if swieta_w_miesiacu:
        st.markdown(date_chips_html("Święta w tym miesiącu", swieta_w_miesiacu), unsafe_allow_html=True)

    # Zakładki – jedna na harmonogram
    dostepne_klucze = [k for k in SCHEDULE_KEYS if k in harmonogramy]
    etykiety_zakładek = [SCHEDULE_LABELS[k] for k in dostepne_klucze]

    tabs = st.tabs(etykiety_zakładek)

    for tab, key in zip(tabs, dostepne_klucze):
        with tab:
            state = harmonogramy[key]
            label = SCHEDULE_LABELS[key]

            # Wyświetl i obsłuż edycję harmonogramu
            updated = renderuj_harmonogram(
                state=state,
                dni=info["dni"],
                swieta=info["swieta"],
                label=label,
                key_prefix=key,
                liczba_dni_roboczych=info["liczba_dni_roboczych"],
            )

            # Jeśli była edycja – zaktualizuj state
            if updated is not None:
                harmonogramy[key] = updated
                st.session_state["harmonogramy"] = harmonogramy
                st.rerun()

            st.divider()

            # Tabela podsumowania
            renderuj_podsumowanie(
                state=harmonogramy[key],
                swieta=info["swieta"],
                key_prefix=key,
            )

            st.divider()

            # Eksport
            with st.expander("Eksportuj dane"):
                eksportuj_harmonogram(
                    state=harmonogramy[key],
                    dni=info["dni"],
                    swieta=info["swieta"],
                    label=label,
                    key_prefix=key,
                )
