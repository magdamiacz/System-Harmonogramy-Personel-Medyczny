# Centralny system designu: paleta kolorów, CSS aplikacji i ekranu logowania, legenda kodów zmian.
#
# Jedno źródło prawdy dla kolorów używanych w modules/ui_components.py.
# Selektory CSS zweryfikowane dla Streamlit 1.32.0.

import html
from string import Template
from typing import Dict, Tuple

from modules.icons import icon_bg_url

# Paleta bazowa (kontrast tekstu zgodny z WCAG AA)

COLOR_BG = "#F4F8F8"            # tło strony
COLOR_SURFACE = "#FFFFFF"       # karty
COLOR_BORDER = "#E3EEEC"
COLOR_PRIMARY = "#0F766E"       # przyciski i turkusowy tekst (5.47:1 z bielą)
COLOR_PRIMARY_DARK = "#115E59"  # hover
COLOR_TEAL_50 = "#F0FDFA"
COLOR_TEAL_100 = "#CCFBF1"
COLOR_TEAL_300 = "#5EEAD4"      # dekoracyjne: gradienty, logo, chipy ikon
COLOR_TEAL_500 = "#14B8A6"
COLOR_TEAL_600 = "#0D9488"
COLOR_TEXT = "#1E293B"
COLOR_TEXT_MUTED = "#556477"    # 5.65:1 na tle strony

# Kolory typów zmian (kod -> kolor tła komórki w tabeli harmonogramu)

SHIFT_COLORS: Dict[str, str] = {
    "D": "#0F766E",    # Dyżur dzienny – turkus
    "N": "#1E3A5F",    # Dyżur nocny – granat
    "DN": "#6D5BD0",   # Dyżur całodobowy (kontrakt) – fiolet
    "R": "#2563EB",    # Zmiana robocza – niebieski
    "DK": "#B45309",   # Końcówka – bursztyn
    "U": "#F9A8D4",    # Urlop – róż
    "UM": "#DDD6FE",   # Urlop macierzyński – lawenda
    "W": "#CBD5E1",    # Wolne za niedzielę/święto – szaroniebieski
    "X": "#DC2626",    # Niedyspozycja – czerwony (tylko podgląd)
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

# Jasne tinty kolumn weekend/święto – nie konkurują z kolorem typu zmiany (priorytetowym)

COLUMN_HIGHLIGHTS: Dict[str, Dict[str, str]] = {
    "weekend": {"bg": "#EEF4F3"},
    "holiday": {"bg": "#FEE2E2"},
}

_COLUMN_LABELS: Tuple[Tuple[str, str], ...] = (
    ("weekend", "Weekend (So/Nd)"),
    ("holiday", "Święto"),
)

# Kolory bilansu w tabeli podsumowania

BALANCE_COLORS: Dict[str, Dict[str, str]] = {
    "nadgodziny": {"bg": "#FDE2E2", "fg": "#991B1B"},
    "niedobor": {"bg": "#FEF3C7", "fg": "#92400E"},
}


def get_text_color(bg_hex: str) -> str:
    """Zwraca czytelny kolor tekstu (ciemny/biały) na podstawie luminancji tła (YIQ)."""
    if not bg_hex:
        return COLOR_TEXT
    h = bg_hex.lstrip("#")
    if len(h) != 6:
        return COLOR_TEXT
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    return COLOR_TEXT if yiq >= 150 else "#FFFFFF"


def _chip_html(tekst: str, bg: str) -> str:
    return (
        f'<span class="legend-chip" style="background-color:{bg}; color:{get_text_color(bg)};">'
        f"{html.escape(tekst)}</span>"
    )


def build_legend_chips_html() -> str:
    """Plakietki legendy budowane z SHIFT_COLORS/COLUMN_HIGHLIGHTS – nie rozjadą się z tabelą."""
    chips = []
    for kod, (nazwa, godziny) in SHIFT_LABELS.items():
        tekst = f"{kod} – {nazwa}" + (f" ({godziny})" if godziny != "—" else "")
        chips.append(_chip_html(tekst, SHIFT_COLORS[kod]))
    for klucz, nazwa in _COLUMN_LABELS:
        chips.append(_chip_html(nazwa, COLUMN_HIGHLIGHTS[klucz]["bg"]))
    return '<div class="legend-chip-row">' + "".join(chips) + "</div>"


_TOKENS: Dict[str, str] = {
    "bg": COLOR_BG,
    "surface": COLOR_SURFACE,
    "border": COLOR_BORDER,
    "primary": COLOR_PRIMARY,
    "primary_dark": COLOR_PRIMARY_DARK,
    "teal50": COLOR_TEAL_50,
    "teal100": COLOR_TEAL_100,
    "teal300": COLOR_TEAL_300,
    "teal500": COLOR_TEAL_500,
    "teal600": COLOR_TEAL_600,
    "text": COLOR_TEXT,
    "muted": COLOR_TEXT_MUTED,
    # Ikony jako background-image (nie mask-image): szersze i bardziej jednolite wsparcie
    # przeglądarek, mniej podatne na różnice w CSP niż maski. Kolor jest zapisany na sztywno
    # w SVG dopasowanym do tła, na którym dana ikona się pojawia.
    "i_logout": icon_bg_url("log-out", COLOR_TEXT),
    "i_login": icon_bg_url("log-in", "#FFFFFF"),
    "i_generate": icon_bg_url("sparkles", "#FFFFFF"),
    "i_excel": icon_bg_url("file-spreadsheet", COLOR_PRIMARY),
    "i_error": icon_bg_url("circle-alert", "#B3261E"),
    "i_warning": icon_bg_url("triangle-alert", "#92400E"),
    "i_info": icon_bg_url("info", "#1D4ED8"),
    "i_success": icon_bg_url("circle-check", "#15803D"),
}

_BG_ICON = """
    content: "";
    width: 18px;
    height: 18px;
    flex: 0 0 18px;
    background-image: var(--hp-i);
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
"""

_GLOBAL_CSS = Template("""
:root {
    --hp-i-logout: $i_logout;
    --hp-i-login: $i_login;
    --hp-i-generate: $i_generate;
    --hp-i-excel: $i_excel;
    --hp-i-error: $i_error;
    --hp-i-warning: $i_warning;
    --hp-i-info: $i_info;
    --hp-i-success: $i_success;
}

/* Tło, odstępy, typografia */
[data-testid="stAppViewContainer"] { background: $bg; }
.block-container { padding-top: 3rem; padding-bottom: 4rem; }
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4 { color: $text; letter-spacing: -0.01em; }
hr { border-color: $border; }

/* Ukrycie elementów interfejsu Streamlit (menu, Deploy, pasek dekoracyjny) */
[data-testid="stHeader"] { background: transparent; pointer-events: none; }
[data-testid="stStatusWidget"] { pointer-events: auto; }
#MainMenu,
[data-testid="stMainMenu"],
[data-testid="stDeployButton"],
.stDeployButton,
[data-testid="stToolbarActions"],
[data-testid="stDecoration"] { display: none !important; }

/* Elementy zawierające wyłącznie CSS nie zajmują miejsca */
[data-testid="element-container"]:has([data-testid="stMarkdownContainer"] style) { display: none; }

/* Sidebar */
[data-testid="stSidebar"] { border-right: 1px solid $border; }

/* Karty (znacznik .hp-card-head w pierwszym elemencie karty, wykrywany przez :has()) */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="element-container"] .hp-card-head) {
    background: $surface;
    border: 1px solid $border;
    border-radius: 20px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 12px 32px -18px rgba(15, 118, 110, 0.35);
}

/* Pola formularzy */
[data-testid="stTextInput"] [data-baseweb="input"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div { border-radius: 12px !important; }
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
    border-color: $primary !important;
    box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.2);
}
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed $teal300;
    border-radius: 14px;
    background: $teal50;
}

/* Przyciski */
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
    border-radius: 999px;
    font-weight: 600;
    min-height: 2.75rem;
    gap: 0.5rem;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
[data-testid="baseButton-primary"] {
    background: $primary;
    border-color: $primary;
    color: #FFFFFF;
    box-shadow: 0 10px 22px -12px rgba(15, 118, 110, 0.8);
}
[data-testid="baseButton-primary"]:hover,
[data-testid="baseButton-primary"]:focus:not(:active) {
    background: $primary_dark;
    border-color: $primary_dark;
    color: #FFFFFF;
}
[data-testid="baseButton-secondary"] { background: $surface; border-color: $border; color: $text; }
[data-testid="baseButton-secondary"]:hover { background: $teal50; border-color: $teal500; color: $primary; }
[data-testid="stDownloadButton"] button { background: $teal50; border-color: $teal100; color: $primary; }
[data-testid="stDownloadButton"] button:hover {
    background: $teal100;
    border-color: $teal500;
    color: $primary_dark;
}
button:focus-visible { outline: 3px solid rgba(20, 184, 166, 0.45); outline-offset: 2px; }

/* Ikony na przyciskach (etykiety przycisków w Streamlit to czysty tekst) */
[data-testid="stSidebar"] [data-testid="stButton"] [data-testid="baseButton-secondary"] {
    --hp-i: var(--hp-i-logout);
}
[data-testid="stSidebar"] [data-testid="stButton"] [data-testid="baseButton-primary"] {
    --hp-i: var(--hp-i-generate);
}
[data-testid="stDownloadButton"] button { --hp-i: var(--hp-i-excel); }
[data-testid="stSidebar"] [data-testid="stButton"] button::before,
[data-testid="stDownloadButton"] button::before {$bg_icon}

/* Komunikaty: ikona zależna od typu */
[data-testid="stNotification"] { border-radius: 14px; }
[data-testid="stNotificationContentError"] { --hp-i: var(--hp-i-error); }
[data-testid="stNotificationContentWarning"] { --hp-i: var(--hp-i-warning); }
[data-testid="stNotificationContentInfo"] { --hp-i: var(--hp-i-info); }
[data-testid="stNotificationContentSuccess"] { --hp-i: var(--hp-i-success); }
[data-testid="stNotificationContentError"] > div::before,
[data-testid="stNotificationContentWarning"] > div::before,
[data-testid="stNotificationContentInfo"] > div::before,
[data-testid="stNotificationContentSuccess"] > div::before {$bg_icon}

/* Zakładki jako segmentowane pigułki */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.35rem;
    background: $surface;
    border: 1px solid $border;
    border-radius: 16px;
    padding: 0.35rem;
    margin-bottom: 0.75rem;
    flex-wrap: nowrap;
    overflow-x: auto;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stTabs"] [data-baseweb="tab"] {
    height: auto;
    padding: 0.5rem 1rem;
    border-radius: 12px;
    background: transparent;
    white-space: nowrap;
}
[data-testid="stTabs"] [data-baseweb="tab"] p { font-weight: 600; color: $muted; }
[data-testid="stTabs"] [data-baseweb="tab"]:hover p { color: $primary; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    background: $teal50;
    box-shadow: inset 0 0 0 1px $teal100;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] p { color: $primary; }
[data-testid="stTabs"] [data-baseweb="tab"]:focus-visible { outline: 2px solid $teal500; outline-offset: 1px; }

/* Expandery */
[data-testid="stExpander"] details {
    background: $surface;
    border: 1px solid $border;
    border-radius: 16px;
}
[data-testid="stExpander"] summary { font-weight: 600; }

/* Komponenty HTML */
.hp-ico { display: inline-block; vertical-align: middle; flex: none; }
.hp-ico-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 12px;
    background: $teal50;
    color: $primary;
    box-shadow: inset 0 0 0 1px $teal100;
    flex: none;
}
.hp-logo { display: inline-flex; filter: drop-shadow(0 8px 14px rgba(13, 148, 136, 0.28)); }

.hp-brand { display: flex; align-items: center; gap: 0.75rem; padding: 0 0.25rem 0.5rem; }
.hp-brand-name { display: block; font-weight: 800; font-size: 1.05rem; line-height: 1.2; color: $text; }
.hp-brand-sub { display: block; font-size: 0.82rem; color: $muted; }

.hp-hero {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.4rem 1.6rem;
    margin-bottom: 0.25rem;
    border-radius: 24px;
    color: #FFFFFF;
    background:
        radial-gradient(90% 140% at 100% 0%, rgba(94, 234, 212, 0.55) 0%, rgba(94, 234, 212, 0) 60%),
        linear-gradient(110deg, $primary 0%, $primary 40%, $teal600 78%, $teal500 100%);
    box-shadow: 0 18px 40px -20px rgba(15, 118, 110, 0.7);
}
.hp-hero-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.16);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.3);
    flex: none;
}
.hp-hero-title { font-size: 1.45rem; font-weight: 800; line-height: 1.25; }
.hp-hero-sub { font-size: 0.95rem; margin-top: 0.15rem; }

.hp-card-head { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.25rem; }
.hp-card-title { font-weight: 700; font-size: 1.02rem; line-height: 1.25; color: $text; }
.hp-card-sub { font-size: 0.82rem; color: $muted; }

.hp-section-title {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin: 0.4rem 0 0.5rem;
    font-size: 1.2rem;
    font-weight: 800;
    color: $text;
}

.hp-stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin: 0.25rem 0 0.25rem;
}
.hp-stat {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding: 1rem 1.15rem;
    background: $surface;
    border: 1px solid $border;
    border-radius: 20px;
    box-shadow: 0 12px 32px -18px rgba(15, 118, 110, 0.35);
}
.hp-stat .hp-ico-chip { width: 46px; height: 46px; border-radius: 14px; }
.hp-stat-label { font-size: 0.82rem; font-weight: 600; color: $muted; }
.hp-stat-value { font-size: 1.35rem; font-weight: 800; line-height: 1.2; color: $text; }

.hp-dates { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; margin: 0.1rem 0 0.5rem; }
.hp-dates-label {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    margin-right: 0.2rem;
    font-size: 0.88rem;
    font-weight: 600;
    color: $muted;
}
.hp-chip {
    display: inline-flex;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    background: #FEE2E2;
    color: #991B1B;
    font-size: 0.82rem;
    font-weight: 700;
}

.hp-norm-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.75rem;
    margin-top: 0.25rem;
}
.hp-norm-item {
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    padding: 0.7rem 0.85rem;
    border-radius: 14px;
    background: $bg;
}
.hp-norm-ico { color: $primary; margin-top: 0.1rem; }
.hp-norm-label { font-size: 0.78rem; font-weight: 600; color: $muted; }
.hp-norm-value { font-size: 0.92rem; color: $text; }
.hp-norm-value strong { color: $primary; }

.legend-chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.25rem 0; }
.legend-chip {
    display: inline-flex;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}
""")

_LOGIN_CSS = Template("""
/* Ekran logowania: turkusowy gradient z delikatnymi łukami */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(55% 45% at 0% 0%, rgba(240, 253, 250, 0.85) 0%, rgba(240, 253, 250, 0) 70%),
        linear-gradient(150deg, $teal300 0%, $teal500 45%, $teal600 100%);
}
[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after {
    content: "";
    position: fixed;
    z-index: 0;
    border-radius: 50%;
    border: 56px solid rgba(255, 255, 255, 0.1);
    pointer-events: none;
}
[data-testid="stAppViewContainer"]::before { width: 760px; height: 760px; left: -300px; bottom: -380px; }
[data-testid="stAppViewContainer"]::after {
    width: 520px;
    height: 520px;
    right: -200px;
    top: -240px;
    border-width: 40px;
}
.block-container { padding-top: 9vh; }

/* Karta logowania: stylowana przez pozycję środkowej z 3 kolumn (st.columns([1, 2, 1])),
   NIE przez :has() + znacznik. st.columns() to jedyne miejsce w aplikacji używające kolumn
   na tym poziomie, więc :nth-of-type(2) jednoznacznie wskazuje środkową kolumnę – rozwiązanie
   odporne nawet w przeglądarkach bez obsługi :has() lub przy nieco innej strukturze DOM. */
[data-testid="stAppViewContainer"] [data-testid="column"]:nth-of-type(2) {
    position: relative;
    z-index: 1;
    max-width: 440px;
    margin-inline: auto;
    padding: 2.25rem 2rem 1.75rem;
    background: $surface;
    border-radius: 28px;
    box-shadow: 0 32px 70px -24px rgba(4, 47, 46, 0.55);
}
.hp-login-head {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
    margin-bottom: 0.5rem;
    text-align: center;
}
.hp-logo--lg { margin-bottom: 0.75rem; }
.hp-login-title { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.01em; color: $text; }
.hp-login-sub { font-size: 0.93rem; color: $muted; }

[data-testid="stButton"] [data-testid="baseButton-primary"] { --hp-i: var(--hp-i-login); margin-top: 0.5rem; }
[data-testid="stButton"] [data-testid="baseButton-primary"]::before {$bg_icon}
""")


def _style(template: Template, **extra: str) -> str:
    return "<style>" + template.substitute(_TOKENS, bg_icon=_BG_ICON, **extra) + "</style>"


def inject_global_css() -> None:
    """Wstrzykuje statyczny, autorski CSS aplikacji (bez danych użytkownika – brak ryzyka XSS)."""
    import streamlit as st

    st.markdown(_style(_GLOBAL_CSS), unsafe_allow_html=True)


def inject_login_css() -> None:
    """CSS wyłącznie dla ekranu logowania; znika przy kolejnym przebiegu skryptu."""
    import streamlit as st

    st.markdown(_style(_LOGIN_CSS), unsafe_allow_html=True)
