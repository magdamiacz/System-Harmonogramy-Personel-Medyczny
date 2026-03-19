# app.py
# Główna aplikacja Streamlit – Zautomatyzowany System Generowania Harmonogramów
# Uruchamianie: streamlit run app.py

import datetime
import sys
import os

import streamlit as st

# Dodaj katalog projektu do ścieżki (potrzebne gdy uruchamiamy z innego folderu)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import SCHEDULE_KEYS, SCHEDULE_LABELS, WORK_MINUTES_PER_DAY_STANDARD
from modules.data_loader import grupuj_wg_harmonogramu, wczytaj_niedyspozycje, wczytaj_personel
from modules.holidays import get_month_info
from modules.scheduler import generuj_wszystkie_harmonogramy
from modules.ui_components import eksportuj_harmonogram, renderuj_harmonogram, renderuj_podsumowanie


# ---------------------------------------------------------------------------
# Konfiguracja strony
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Harmonogram pracy – personel medyczny",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Zautomatyzowany System Generowania Harmonogramów Pracy")
st.caption("Personel medyczny | Algorytm zachłanny | Praca dyplomowa 2025/2026")

# ---------------------------------------------------------------------------
# Sidebar: parametry i import danych
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Parametry")

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
        format_func=lambda m: datetime.date(int(rok), m, 1).strftime("%B").capitalize(),
        index=teraz.month - 1,
        key="miesiac",
    )

    st.divider()
    st.header("Import danych")

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
        "Generuj harmonogram",
        type="primary",
        use_container_width=True,
        key="generuj_btn",
    )

    # Link do opisu heurystyki
    st.divider()
    st.markdown("📄 [Opis algorytmu (heurystyka.md)](heurystyka.md)")


# ---------------------------------------------------------------------------
# Główna logika: wczytaj dane i wygeneruj harmonogram
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Wyświetlanie harmonogramów w zakładkach
# ---------------------------------------------------------------------------

harmonogramy = st.session_state.get("harmonogramy", {})
info = st.session_state.get("info_miesiaca")

if not harmonogramy:
    # Ekran powitalny przed wygenerowaniem
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
    nazwa_miesiaca = datetime.date(int(rok), int(miesiac), 1).strftime("%B %Y")
    normatyw_min = info["liczba_dni_roboczych"] * WORK_MINUTES_PER_DAY_STANDARD
    normatyw_h = normatyw_min // 60
    normatyw_m = normatyw_min % 60
    normatyw_str = f"{normatyw_h}h{normatyw_m:02d}min" if normatyw_m else f"{normatyw_h}h"
    st.markdown(
        f"### {nazwa_miesiaca.capitalize()}  "
        f"| Dni robocze: **{info['liczba_dni_roboczych']}**  "
        f"| Normatyw etat: **{normatyw_str}**"
    )

    # Listowanie świąt w miesiącu
    swieta_w_miesiacu = sorted([
        d for d in info["swieta"]
        if d.month == int(miesiac) and d.year == int(rok)
    ])
    if swieta_w_miesiacu:
        st.caption("Święta w tym miesiącu: " + ", ".join(str(d) for d in swieta_w_miesiacu))

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
