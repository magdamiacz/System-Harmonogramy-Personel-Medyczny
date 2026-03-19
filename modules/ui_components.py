# modules/ui_components.py
# Komponenty interfejsu użytkownika Streamlit:
#   - renderowanie tabeli harmonogramu (edytowalna)
#   - tabela podsumowań
#   - kolorowanie komórek przez CSS

import datetime
from typing import Dict, List, Optional, Set

import pandas as pd
import streamlit as st

from config import SHIFT_DURATIONS, WORKING_SHIFTS, WORK_MINUTES_PER_DAY_STANDARD
from modules.data_loader import Pracownik
from modules.holidays import czy_swieto, czy_weekend, czy_niedziela
from modules.normative import _minuty_na_str
from modules.scheduler import HarmonogramState, oblicz_podsumowanie


# ---------------------------------------------------------------------------
# Kolory kolumn: weekend = żółty, święto = czerwony
# ---------------------------------------------------------------------------

KOLOR_KOLUMNY_WEEKEND = "#ffffcc"   # Jasny żółty
KOLOR_KOLUMNY_SWIETO = "#ffcccc"    # Jasny czerwony


# ---------------------------------------------------------------------------
# Kolory komórek harmonogramu (dla przyszłego użycia)
# ---------------------------------------------------------------------------

KOLOR_ZMIANY: Dict[str, str] = {
    "D":  "#d4edda",   # Zielony jasny – dzień
    "N":  "#cce5ff",   # Niebieski jasny – noc
    "DN": "#fff3cd",   # Żółty – całodobowy
    "R":  "#e2f0cb",   # Jasnozielony – krótka zmiana
    "DK": "#ffeeba",   # Pomarańczowy jasny – końcówka
    "U":  "#f8d7da",   # Czerwony jasny – urlop
    "UM": "#f5c6cb",   # Różowy – urlop macierzyński
    "W":  "#e2e3e5",   # Szary – wolne
    "":   "#ffffff",   # Biały – pusty
}


# ---------------------------------------------------------------------------
# Budowanie DataFrame harmonogramu
# ---------------------------------------------------------------------------

def buduj_df_harmonogramu(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
) -> pd.DataFrame:
    """
    Tworzy DataFrame z harmonogramem:
    - Wiersze = pracownicy
    - Kolumny = daty (formatowane jako 'D\nDD' z oznaczeniem weekendu/święta)
    """
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]

    # Nagłówki kolumn: "Pn\n01", "Wt\n02", ...
    naglowki = []
    for d in dni:
        nazwa = NAZWY_DNI[d.weekday()]
        naglowek = f"{nazwa}\n{d.day:02d}"
        naglowki.append(naglowek)

    dane = {}
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        row = []
        for d in dni:
            row.append(state.get_przydzial(imie, d))
        dane[imie] = row

    df = pd.DataFrame(dane, index=naglowki).T
    df.index.name = "Imię i nazwisko"
    return df


def buduj_df_do_edycji(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
) -> pd.DataFrame:
    """
    Tworzy DataFrame z harmonogramem z prostymi nagłówkami numerycznymi
    dla komponentu st.data_editor (edycja użytkownika).
    Puste komórki = "" (nigdy NaN/None).
    """
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    naglowki_display = [f"{NAZWY_DNI[d.weekday()]} {d.day}" for d in dni]

    dane = {}
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        row = {}
        for d in dni:
            val = state.get_przydzial(imie, d)
            row[f"{NAZWY_DNI[d.weekday()]} {d.day}"] = val if val else ""
        dane[imie] = row

    df = pd.DataFrame.from_dict(dane, orient="index")
    df.columns = naglowki_display
    df.index.name = "Imię i nazwisko"
    df = df.reset_index()
    # Puste komórki – zawsze pusty string, nigdy NaN/None
    df = df.fillna("")
    for col in naglowki_display:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: "" if pd.isna(x) or str(x).strip() in ("nan", "None", "NaN") else str(x).strip())
    return df


# ---------------------------------------------------------------------------
# Nagłówek normatywu i końcówki
# ---------------------------------------------------------------------------

def buduj_tekst_normatywu(
    state: HarmonogramState,
    liczba_dni_roboczych: int,
) -> str:
    """
    Zwraca tekst do nagłówka nad tabelą: jak obliczany jest normatyw
    i jaka wychodzi końcówka do przypisania.
    """
    from config import WORK_MINUTES_PER_DAY_STANDARD, WORK_MINUTES_PER_DAY_DISABILITY, FULL_SHIFT_MINUTES

    # Reprezentatywny normatyw etatowy (zwykły pracownik)
    normatyw_min = liczba_dni_roboczych * WORK_MINUTES_PER_DAY_STANDARD
    pelne = normatyw_min // FULL_SHIFT_MINUTES
    koncowka = normatyw_min % FULL_SHIFT_MINUTES

    normatyw_str = _minuty_na_str(normatyw_min)
    koncowka_str = _minuty_na_str(koncowka) if koncowka > 0 else "—"

    linie = [
        f"**Normatyw etat** (zwykły): {liczba_dni_roboczych} dni roboczych × 7h35min = **{normatyw_str}**",
        f"**Rozkład**: {pelne} dyżurów × 12h" + (f" + 1 × **{koncowka_str}** (końcówka DK)" if koncowka > 0 else ""),
    ]
    # Normatyw z orzeczeniem
    norm_orz = liczba_dni_roboczych * WORK_MINUTES_PER_DAY_DISABILITY
    linie.append(f"**Normatyw z orzeczeniem**: {liczba_dni_roboczych} × 7h = **{_minuty_na_str(norm_orz)}**")
    linie.append("**Kontrakty**: duży min. 160h, mały min. 120h")
    return " | ".join(linie)


def _generuj_css_kolory_kolumn(
    dni: List[datetime.date],
    swieta: Set[datetime.date],
) -> str:
    """Generuje CSS do kolorowania kolumn: weekend=żółty, święto=czerwony."""
    reguly = []
    for i, d in enumerate(dni):
        # Kolumna: 0=Imię, 1..31=dni → nth-child(i+2)
        n = i + 2
        sel = f"td:nth-child({n}), th:nth-child({n})"
        if d in swieta:
            reguly.append(f"[data-testid='stDataFrame'] {sel}, .stDataFrame {sel} {{ background-color: {KOLOR_KOLUMNY_SWIETO} !important; }}")
        elif d.weekday() >= 5:
            reguly.append(f"[data-testid='stDataFrame'] {sel}, .stDataFrame {sel} {{ background-color: {KOLOR_KOLUMNY_WEEKEND} !important; }}")
    return "\n".join(reguly)


# ---------------------------------------------------------------------------
# Rekalkulacja po edycji
# ---------------------------------------------------------------------------

def rekalkuluj_state_po_edycji(
    state: HarmonogramState,
    df_edytowany: pd.DataFrame,
    dni: List[datetime.date],
) -> HarmonogramState:
    """
    Aktualizuje HarmonogramState na podstawie edytowanej tabeli.
    Zeruje przepracowane minuty i liczy od nowa z nowych przydziałów.
    """
    NAZWY_DNI_MAP = {f"Pn {d.day}": d for d in dni}
    NAZWY_DNI_MAP.update({f"Wt {d.day}": d for d in dni})
    NAZWY_DNI_MAP.update({f"Śr {d.day}": d for d in dni})
    NAZWY_DNI_MAP.update({f"Cz {d.day}": d for d in dni})
    NAZWY_DNI_MAP.update({f"Pt {d.day}": d for d in dni})
    NAZWY_DNI_MAP.update({f"So {d.day}": d for d in dni})
    NAZWY_DNI_MAP.update({f"Nd {d.day}": d for d in dni})

    # Zbuduj mapę nagłówek -> data
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    col_to_date = {}
    for d in dni:
        col = f"{NAZWY_DNI[d.weekday()]} {d.day}"
        col_to_date[col] = d

    # Zeruj liczniki
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        state.przydzial[imie] = {}
        state.przepracowane[imie] = 0
        state.liczba_nocnych[imie] = 0
        state.liczba_weekendowych[imie] = 0
        state.liczba_swiatecznych[imie] = 0
        state.liczba_dziennych[imie] = 0

    # Wczytaj nowe przydziały
    for _, row in df_edytowany.iterrows():
        imie = row["Imię i nazwisko"]
        if imie not in state.przydzial:
            continue
        for col, data in col_to_date.items():
            if col not in df_edytowany.columns:
                continue
            val = row.get(col, "")
            if pd.isna(val) or val is None:
                kod = ""
            else:
                kod = str(val).strip().upper()
            if kod in ("", "NAN", "NONE", "NAT"):
                kod = ""
            if kod:
                state.przydziel(imie, data, kod)

    return state


# ---------------------------------------------------------------------------
# Renderowanie tabeli harmonogramu
# ---------------------------------------------------------------------------

def renderuj_harmonogram(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    label: str,
    key_prefix: str,
    liczba_dni_roboczych: int = 0,
) -> Optional[HarmonogramState]:
    """
    Wyświetla edytowalną tabelę harmonogramu w Streamlit.
    Po edycji zwraca zaktualizowany HarmonogramState.
    Zwraca None jeśli nie było edycji.
    """
    st.subheader(label)

    # Nagłówek: normatyw i końcówka
    if liczba_dni_roboczych > 0:
        st.markdown(buduj_tekst_normatywu(state, liczba_dni_roboczych))
        st.caption("Kolumny: żółty = weekend, czerwony = święto")

    # CSS: kolorowanie kolumn weekend/święta
    css = _generuj_css_kolory_kolumn(dni, swieta)
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # Informacja pomocnicza: legenda
    with st.expander("Legenda kodów zmian"):
        st.markdown("""
        | Kod | Znaczenie | Godziny |
        |-----|-----------|---------|
        | **D** | Dyżur dzienny | 7:00–19:00 (12h) |
        | **N** | Dyżur nocny | 19:00–7:00 (12h) |
        | **DN** | Dyżur całodobowy | 7:00–7:00 (24h) – tylko kontrakty |
        | **R** | Zmiana robocza | 7:00–14:35 (7h35min) |
        | **DK** | Końcówka | zmienna (reszta do normatywu) |
        | **U** | Urlop | — |
        | **UM** | Urlop macierzyński | — |
        | **W** | Wolne za niedzielę/święto | — |
        """)

    df = buduj_df_do_edycji(state, dni, swieta)

    # Kolumny danych (bez "Imię i nazwisko")
    data_cols = [c for c in df.columns if c != "Imię i nazwisko"]

    # Konfiguracja kolumn dla data_editor
    col_config = {
        "Imię i nazwisko": st.column_config.TextColumn(
            "Imię i nazwisko",
            disabled=True,
            width="medium",
        )
    }

    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    for i, d in enumerate(dni):
        col_name = f"{NAZWY_DNI[d.weekday()]} {d.day}"
        is_weekend = d.weekday() >= 5
        is_swieto = czy_swieto(d, swieta)

        col_config[col_name] = st.column_config.SelectboxColumn(
            label=col_name,
            options=["", "D", "N", "DN", "R", "DK", "U", "UM", "W"],
            width="small",
        )

    edited_df = st.data_editor(
        df,
        key=f"editor_{key_prefix}",
        use_container_width=True,
        column_config=col_config,
        hide_index=True,
        num_rows="fixed",
    )

    # Sprawdź czy nastąpiła edycja
    if not df.equals(edited_df):
        updated_state = rekalkuluj_state_po_edycji(state, edited_df, dni)
        return updated_state

    return None


# ---------------------------------------------------------------------------
# Tabela podsumowania
# ---------------------------------------------------------------------------

def renderuj_podsumowanie(
    state: HarmonogramState,
    swieta: Set[datetime.date],
    key_prefix: str,
) -> None:
    """
    Wyświetla tabelę podsumowującą pod harmonogramem.
    Zawiera: normatyw, przepracowane, bilans, liczniki dyżurów.
    """
    st.markdown("#### Podsumowanie")

    podsumowanie = oblicz_podsumowanie(state, swieta)
    df = pd.DataFrame(podsumowanie)

    # Kolorowanie wiersza bilansu
    def koloruj_bilans(val):
        if isinstance(val, str):
            if "nadgodziny" in val:
                return "background-color: #f8d7da; color: #721c24;"
            elif "niedobór" in val:
                return "background-color: #fff3cd; color: #856404;"
        return ""

    styled = df.drop(columns=["Bilans_min"]).style.applymap(
        koloruj_bilans, subset=["Bilans"]
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        key=f"summary_{key_prefix}",
    )


# ---------------------------------------------------------------------------
# Eksport do CSV/Excel
# ---------------------------------------------------------------------------

def eksportuj_harmonogram(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    label: str,
    key_prefix: str,
) -> None:
    """
    Przyciski eksportu harmonogramu i podsumowania do pliku CSV i Excel.
    """
    df_harm = buduj_df_do_edycji(state, dni, swieta)
    df_sum = pd.DataFrame(oblicz_podsumowanie(state, swieta)).drop(columns=["Bilans_min"])

    # Eksport z pustymi komórkami jako "" (nie NaN)
    df_harm_exp = df_harm.fillna("")

    col1, col2 = st.columns(2)

    with col1:
        csv_harm = df_harm_exp.to_csv(index=False, encoding="utf-8-sig", na_rep="")
        st.download_button(
            label="Pobierz harmonogram (CSV)",
            data=csv_harm,
            file_name=f"harmonogram_{key_prefix}.csv",
            mime="text/csv",
            key=f"dl_harm_csv_{key_prefix}",
        )

    with col2:
        csv_sum = df_sum.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="Pobierz podsumowanie (CSV)",
            data=csv_sum,
            file_name=f"podsumowanie_{key_prefix}.csv",
            mime="text/csv",
            key=f"dl_sum_csv_{key_prefix}",
        )

    # Eksport Excel (oba arkusze w jednym pliku)
    try:
        import io
        import openpyxl
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_harm_exp.to_excel(writer, sheet_name="Harmonogram", index=False)
            df_sum.to_excel(writer, sheet_name="Podsumowanie", index=False)
        buf.seek(0)
        st.download_button(
            label="Pobierz Excel (harmonogram + podsumowanie)",
            data=buf,
            file_name=f"harmonogram_{key_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_excel_{key_prefix}",
        )
    except ImportError:
        st.warning("Brak biblioteki openpyxl – eksport Excel niedostępny.")
