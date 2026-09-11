# Komponenty interfejsu użytkownika Streamlit:
#   - renderowanie tabeli harmonogramu (edytowalna)
#   - tabela podsumowań
#   - kolorowanie komórek przez CSS

import datetime
from typing import Dict, List, Optional, Set

import pandas as pd
import streamlit as st

from config import (
    FULL_SHIFT_MINUTES,
    SHIFT_DURATIONS,
    WORK_MINUTES_PER_DAY_DISABILITY,
    WORK_MINUTES_PER_DAY_STANDARD,
    WORKING_SHIFTS,
)
from modules.data_loader import Pracownik
from modules.holidays import czy_swieto, czy_weekend, czy_niedziela
from modules.normative import _minuty_na_str
from modules.scheduler import HarmonogramState, oblicz_podsumowanie
from modules.theme import (
    BALANCE_COLORS,
    COLUMN_HIGHLIGHTS,
    SHIFT_COLORS,
    build_legend_chips_html,
    get_text_color,
)


# Budowanie DataFrame harmonogramu

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
    pokazuj_niedyspozycje: bool = False,
) -> pd.DataFrame:
    """
    Tworzy DataFrame z harmonogramem z prostymi nagłówkami numerycznymi
    dla komponentu st.data_editor (edycja użytkownika).
    Puste komórki = "" (nigdy NaN/None).
    Gdy pokazuj_niedyspozycje=True, puste komórki w dniach niedyspozycji
    wypełniane są jako "X" (tylko do widoku – nie edytor).
    """
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    naglowki_display = [f"{NAZWY_DNI[d.weekday()]} {d.day}" for d in dni]

    dane = {}
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        row = {}
        for d in dni:
            val = state.get_przydzial(imie, d)
            if val:
                row[f"{NAZWY_DNI[d.weekday()]} {d.day}"] = val
            elif pokazuj_niedyspozycje and d in p.niedyspozycje:
                row[f"{NAZWY_DNI[d.weekday()]} {d.day}"] = "X"
            else:
                row[f"{NAZWY_DNI[d.weekday()]} {d.day}"] = ""
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


# Nagłówek normatywu i końcówki

def _buduj_styled_df(
    df: pd.DataFrame,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
) -> "pd.io.formats.style.Styler":
    """
    Tworzy Pandas Styler z kolorowaniem:
      - komórki weekendów (So/Nd): bordowe tło
      - komórki świąt: czerwone tło
      - komórki ze zmianą (D/N/DN/R/DK/U/UM/W): kolor według typu zmiany
    Kolor typu zmiany ma priorytet nad kolorem kolumny.
    Dla ciemnych tła: jasny tekst dla czytelności.
    """
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    col_to_date: Dict[str, datetime.date] = {
        f"{NAZWY_DNI[d.weekday()]} {d.day}": d for d in dni
    }

    def style_col(col: pd.Series) -> List[str]:
        if col.name not in col_to_date:
            return [""] * len(col)
        d = col_to_date[col.name]
        if d in swieta:
            col_bg = COLUMN_HIGHLIGHTS["holiday"]["bg"]
        elif d.weekday() >= 5:
            col_bg = COLUMN_HIGHLIGHTS["weekend"]["bg"]
        else:
            col_bg = ""

        styles = []
        for val in col:
            v = str(val).strip() if val else ""
            shift_bg = SHIFT_COLORS.get(v, "") if v else ""
            bg = shift_bg if shift_bg else col_bg
            if bg:
                txt = f"color: {get_text_color(bg)};"
                styles.append(f"background-color: {bg}; {txt}")
            else:
                styles.append("")
        return styles

    data_cols = [c for c in df.columns if c != "Imię i nazwisko"]
    return df.style.apply(style_col, axis=0, subset=pd.IndexSlice[:, data_cols])


def buduj_tekst_normatywu(
    state: HarmonogramState,
    liczba_dni_roboczych: int,
) -> str:
    """
    Zwraca tekst do nagłówka nad tabelą: jak obliczany jest normatyw
    i jaka wychodzi końcówka do przypisania.
    """
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


# Rekalkulacja po edycji

def rekalkuluj_state_po_edycji(
    state: HarmonogramState,
    df_edytowany: pd.DataFrame,
    dni: List[datetime.date],
) -> HarmonogramState:
    """
    Aktualizuje HarmonogramState na podstawie edytowanej tabeli.
    Zeruje przepracowane minuty i liczy od nowa z nowych przydziałów.
    """
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    col_to_date = {f"{NAZWY_DNI[d.weekday()]} {d.day}": d for d in dni}

    # Zeruj liczniki
    for p in state.pracownicy:
        imie = p.imie_nazwisko
        state.przydzial[imie] = {}
        for attr in ("przepracowane", "liczba_nocnych", "liczba_weekendowych",
                     "liczba_swiatecznych", "liczba_dziennych"):
            getattr(state, attr)[imie] = 0

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


# Renderowanie tabeli harmonogramu

def renderuj_harmonogram(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    label: str,
    key_prefix: str,
    liczba_dni_roboczych: int = 0,
) -> Optional[HarmonogramState]:
    """
    Wyświetla tabelę harmonogramu z kolorowaniem oraz edytor poniżej.
    Górna tabela (st.dataframe) pokazuje kolory: szary = weekend, czerwony = święto.
    Edytor (st.data_editor) umożliwia ręczne poprawki.
    Po edycji zwraca zaktualizowany HarmonogramState, w przeciwnym razie None.
    """
    st.subheader(label)

    # Nagłówek: normatyw i końcówka
    if liczba_dni_roboczych > 0:
        with st.container(border=True):
            st.markdown(buduj_tekst_normatywu(state, liczba_dni_roboczych))

    # Legenda kolorów
    st.caption("Kolor komórki pokazuje typ zmiany — szczegóły w legendzie poniżej.")
    with st.expander("Legenda kodów zmian"):
        st.markdown(build_legend_chips_html(), unsafe_allow_html=True)

    df = buduj_df_do_edycji(state, dni, swieta)
    df_widok = buduj_df_do_edycji(state, dni, swieta, pokazuj_niedyspozycje=True)

    # ─Kolorowana tabela (tylko do odczytu)
    styled = _buduj_styled_df(df_widok, dni, swieta)
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
    )

    # Edytor (bez kolorów, ale z możliwością edycji)
    NAZWY_DNI = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    col_config = {
        "Imię i nazwisko": st.column_config.TextColumn(
            "Imię i nazwisko",
            disabled=True,
            width="medium",
        )
    }
    for d in dni:
        col_name = f"{NAZWY_DNI[d.weekday()]} {d.day}"
        col_config[col_name] = st.column_config.SelectboxColumn(
            label=col_name,
            options=["", "D", "N", "DN", "R", "DK", "U", "UM", "W"],
            width="small",
        )

    with st.expander("✏️ Edytuj harmonogram", expanded=False):
        st.caption(
            "Ta tabela nie pokazuje kolorów. Wpisz kod zmiany w wybranej komórce — "
            "kolorowana tabela powyżej odświeży się automatycznie po zatwierdzeniu zmiany."
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


# Tabela podsumowania

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
                c = BALANCE_COLORS["nadgodziny"]
                return f"background-color: {c['bg']}; color: {c['fg']};"
            elif "niedobór" in val:
                c = BALANCE_COLORS["niedobor"]
                return f"background-color: {c['bg']}; color: {c['fg']};"
        return ""

    styled = df.drop(columns=["Bilans_min"]).style.map(
        koloruj_bilans, subset=["Bilans"]
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
    )


# Eksport do CSV/Excel

def eksportuj_harmonogram(
    state: HarmonogramState,
    dni: List[datetime.date],
    swieta: Set[datetime.date],
    label: str,
    key_prefix: str,
) -> None:
    """
    Przycisk eksportu harmonogramu i podsumowania do pliku Excel (dwa arkusze).
    """
    df_harm = buduj_df_do_edycji(state, dni, swieta)
    df_sum = pd.DataFrame(oblicz_podsumowanie(state, swieta)).drop(columns=["Bilans_min"])

    # Eksport z pustymi komórkami jako "" (nie NaN)
    df_harm_exp = df_harm.fillna("")

    try:
        import io
        import openpyxl
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_harm_exp.to_excel(writer, sheet_name="Harmonogram", index=False)
            df_sum.to_excel(writer, sheet_name="Podsumowanie", index=False)
        buf.seek(0)
        st.download_button(
            label="📊 Pobierz Excel (harmonogram + podsumowanie)",
            data=buf,
            file_name=f"harmonogram_{key_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_excel_{key_prefix}",
            use_container_width=True,
        )
    except ImportError:
        st.warning("Brak biblioteki openpyxl – eksport Excel niedostępny.")
