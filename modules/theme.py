# Centralny system designu: paleta kolorów, wstrzykiwanie CSS, legenda kodów zmian.
#
# Jedno źródło prawdy dla kolorów używanych w modules/ui_components.py –
# zastępuje wcześniej rozproszone stałe i ręcznie utrzymywany zbiór "ciemnych" kolorów.

from typing import Dict, Tuple

# Paleta bazowa

COLOR_BACKGROUND = "#FFFFFF"
COLOR_SURFACE = "#F4F7FA"       # sidebar, karty
COLOR_BORDER = "#E1E8EE"
COLOR_PRIMARY = "#1565C0"       # kliniczny błękit – przyciski, nagłówki
COLOR_PRIMARY_DARK = "#0D47A1"  # hover/active
COLOR_SUCCESS = "#2E7D32"
COLOR_WARNING = "#B8791C"
COLOR_DANGER = "#B3261E"
COLOR_TEXT = "#1B2733"
COLOR_TEXT_MUTED = "#57606B"

# Kolory typów zmian (kod -> kolor tła komórki w tabeli harmonogramu)

SHIFT_COLORS: Dict[str, str] = {
    "D": "#2E7D32",    # Dyżur dzienny – zielony
    "N": "#1E3A5F",    # Dyżur nocny – granatowy
    "DN": "#5B4B8A",   # Dyżur całodobowy (kontrakt) – fioletowy
    "R": "#6B7A3F",    # Zmiana robocza – oliwkowy
    "DK": "#B8791C",   # Końcówka – bursztynowy
    "U": "#F3C6CB",    # Urlop – pastelowy róż
    "UM": "#F3CFE3",   # Urlop macierzyński – pastelowy lawendowy róż
    "W": "#E9EDF0",    # Wolne za niedzielę/święto – jasny szaroniebieski
    "X": "#B3261E",    # Niedyspozycja – czerwony (tylko podgląd)
    "": "",
}

# Etykiety i godziny dla legendy (kod -> (nazwa, opis godzin))

SHIFT_LABELS: Dict[str, Tuple[str, str]] = {
    "D": ("Dyżur dzienny", "7:00–19:00"),
    "N": ("Dyżur nocny", "19:00–7:00"),
    "DN": ("Dyżur całodobowy", "7:00–7:00, kontrakty"),
    "R": ("Zmiana robocza", "7:00–14:35"),
    "DK": ("Końcówka", "reszta do normatywu"),
    "U": ("Urlop", "—"),
    "UM": ("Urlop macierzyński", "—"),
    "W": ("Wolne za niedzielę/święto", "—"),
    "X": ("Niedyspozycja", "—"),
}

# Kolory drugorzędnych wskazówek kolumnowych (weekend/święto) – jasne tinty,
# żeby nie konkurowały wizualnie z kolorem typu zmiany (priorytetowym).

COLUMN_HIGHLIGHTS: Dict[str, Dict[str, str]] = {
    "weekend": {"bg": "#E8EEF3", "fg": COLOR_TEXT},
    "holiday": {"bg": "#F4C7C7", "fg": "#7A1F1F"},
}

# Kolory bilansu w tabeli podsumowania – spójne z resztą palety (czerwień/bursztyn)

BALANCE_COLORS: Dict[str, Dict[str, str]] = {
    "nadgodziny": {"bg": "#F8D7DA", "fg": "#7A1F1F"},
    "niedobor": {"bg": "#FCE8C8", "fg": "#7A4A0B"},
}


def get_text_color(bg_hex: str) -> str:
    """Zwraca czytelny kolor tekstu (ciemny/biały) na podstawie luminancji tła (YIQ).

    Zastępuje wcześniejszy ręcznie utrzymywany zbiór "ciemnych" kolorów, który
    łatwo rozjeżdżał się z faktyczną paletą przy każdej zmianie koloru.
    """
    if not bg_hex:
        return COLOR_TEXT
    h = bg_hex.lstrip("#")
    if len(h) != 6:
        return COLOR_TEXT
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    return COLOR_TEXT if yiq >= 150 else "#FFFFFF"


def build_legend_chips_html() -> str:
    """Buduje HTML z kolorowymi plakietkami (chips) dla każdego kodu zmiany.

    Kolory pochodzą bezpośrednio z SHIFT_COLORS/SHIFT_LABELS, więc legenda
    nie może się rozjechać z rzeczywistymi kolorami w tabeli harmonogramu.
    """
    chips = []
    for kod, (nazwa, godziny) in SHIFT_LABELS.items():
        bg = SHIFT_COLORS.get(kod, "")
        fg = get_text_color(bg)
        opis = f"{godziny}" if godziny != "—" else ""
        tekst = f"{kod} – {nazwa}" + (f" ({opis})" if opis else "")
        chips.append(
            f'<span class="legend-chip" style="background-color:{bg}; color:{fg};">{tekst}</span>'
        )
    return '<div class="legend-chip-row">' + "".join(chips) + "</div>"


def inject_global_css() -> None:
    """Wstrzykuje jednorazowo statyczny, autorski CSS (bez danych użytkownika –
    zero ryzyka XSS) nadający aplikacji spójny, czysty/medyczny wygląd."""
    import streamlit as st

    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background-color: {COLOR_SURFACE};
            border-right: 1px solid {COLOR_BORDER};
        }}

        .stButton > button {{
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 600;
        }}

        .stButton > button[kind="primary"] {{
            background-color: {COLOR_PRIMARY};
            border-color: {COLOR_PRIMARY};
        }}

        .stButton > button[kind="primary"]:hover {{
            background-color: {COLOR_PRIMARY_DARK};
            border-color: {COLOR_PRIMARY_DARK};
        }}

        [data-testid="stExpander"] {{
            border: 1px solid {COLOR_BORDER};
            border-radius: 8px;
        }}

        [data-testid="stAlert"] {{
            border-radius: 8px;
        }}

        [data-testid="stMetricLabel"] {{
            color: {COLOR_TEXT_MUTED};
        }}

        hr {{
            border-color: {COLOR_BORDER};
        }}

        .legend-chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 4px 0;
        }}

        .legend-chip {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
