# Główna aplikacja Streamlit – Zautomatyzowany System Generowania Harmonogramów
# Uruchamianie: streamlit run app.py

import datetime
import sys
import os

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SCHEDULE_KEYS, SCHEDULE_LABELS, WORK_MINUTES_PER_DAY_STANDARD
from modules.normative import _minuty_na_str
from modules.data_loader import grupuj_wg_harmonogramu, wczytaj_niedyspozycje, wczytaj_personel
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

MIESIACE_PL = [
    "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
    "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
]


# Login screen
def show_login():
    inject_login_css()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.markdown(
                '<div style="text-align:center"><h2>🏥 Harmonogram pracy</h2>'
                '<p style="color:#556477;font-size:0.9rem">Zautomatyzowany System Generowania Harmonogramów</p></div>',
                unsafe_allow_html=True
            )

            username = st.text_input("Login", placeholder="Wpisz login")
            password = st.text_input("Hasło", type="password", placeholder="Wpisz hasło")

            if st.button("🔓 Zaloguj się", use_container_width=True, type="primary"):
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

    with st.container(border=True):
        st.markdown(card_head_html("folder-up", "Import danych"), unsafe_allow_html=True)

        # Plik personelu
        personel_file = st.file_uploader(
            "Plik personelu (CSV)",
            type=["csv"],
            key="personel_upload",
            help="Format: imie_nazwisko, oddzial, rola, typ_umowy, orzeczenie, tylko_7h, pracuje_w_weekendy",
        )

        # Plik niedyspozycji (opcjonalny)
        niedysp_file = st.file_uploader(
            "Plik niedyspozycji (CSV) – opcjonalny",
            type=["csv"],
            key="niedysp_upload",
            help="Format: imie_nazwisko, data (YYYY-MM-DD)",
        )

    st.divider()

    # Przycisk generowania
    generuj_btn = st.button(
        "✨ Generuj harmonogram",
        type="primary",
        use_container_width=True,
        key="generuj_btn",
    )

    # Wylogowanie
    if st.button("🚪 Wyloguj się", use_container_width=True):
        st.session_state["logged_in"] = False
        st.rerun()


# Główna logika: wczytaj dane i wygeneruj harmonogram

# Przechowuj wygenerowane harmonogramy w session_state
if "harmonogramy" not in st.session_state:
    st.session_state["harmonogramy"] = {}
if "info_miesiaca" not in st.session_state:
    st.session_state["info_miesiaca"] = None


def wczytaj_i_generuj(personel_src, niedysp_src, rok: int, miesiac: int):
    """Wczytuje dane, waliduje i uruchamia generator harmonogramów."""
    bledy_all = []

    # Wczytaj personel
    try:
        pracownicy, bledy = wczytaj_personel(personel_src)
        bledy_all.extend(bledy)
    except ValueError as e:
        st.error(f"Błąd wczytywania pliku personelu: {e}")
        return None, None

    if not pracownicy:
        st.error("Brak pracowników w pliku personelu.")
        return None, None

    # Wczytaj niedyspozycje (jeśli podano)
    if niedysp_src is not None:
        try:
            _, bledy_nd = wczytaj_niedyspozycje(niedysp_src, pracownicy)
            bledy_all.extend(bledy_nd)
        except ValueError as e:
            st.warning(f"Błąd wczytywania niedyspozycji: {e}")

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
    if personel_file is None:
        st.error("Wgraj plik personelu przed generowaniem harmonogramu.")
    else:
        harmonogramy, info = wczytaj_i_generuj(
            personel_src=personel_file,
            niedysp_src=niedysp_file,
            rok=rok,
            miesiac=miesiac,
        )
        if harmonogramy is not None:
            st.session_state["harmonogramy"] = harmonogramy
            st.session_state["info_miesiaca"] = info
            st.success(
                f"Harmonogram wygenerowany dla {info['liczba_dni']} dni "
                f"({info['liczba_dni_roboczych']} dni roboczych)."
            )


# Wyświetlanie harmonogramów w zakładkach

harmonogramy = st.session_state.get("harmonogramy", {})
info = st.session_state.get("info_miesiaca")

if not harmonogramy:
    # Ekran powitalny przed wygenerowaniem
    st.markdown(section_title_html("clipboard-list", "Zacznij tutaj"), unsafe_allow_html=True)
    st.info(
        "Wgraj plik personelu w panelu bocznym i kliknij **Generuj harmonogram**, "
        "aby zobaczyć rozkład zmian."
    )

    # Podpowiedź dot. pliku personelu
    with st.expander("Przykład formatu pliku personelu (CSV)"):
        st.code(
            "imie_nazwisko,oddzial,rola,typ_umowy,orzeczenie,tylko_7h,pracuje_w_weekendy\n"
            "Kowalska Anna,gastrologiczny,pielęgniarki,etat,nie,nie,tak\n"
            "Nowak Jan,wewnętrzny,pielęgniarki,duzy_kontrakt,nie,nie,tak\n"
            "Wiśniewska Ewa,OIOK,pielęgniarki,etat,nie,tak,nie",
            language="csv",
        )

    with st.expander("Przykład formatu pliku niedyspozycji (CSV)"):
        st.code(
            "imie_nazwisko,data\n"
            "Kowalska Anna,2026-01-05\n"
            "Kowalska Anna,2026-01-12\n"
            "Nowak Jan,2026-01-20",
            language="csv",
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
