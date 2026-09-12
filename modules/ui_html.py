# Buildery fragmentów HTML dla st.markdown(..., unsafe_allow_html=True).
#
# Każdy fragment jest jednoliniowy: w Markdownie Streamlit pusta linia kończy blok HTML,
# a wcięcie o 4 spacje zamienia resztę w blok kodu. Wartości dynamiczne są escapowane.

import datetime
import html
from typing import Iterable, Optional, Sequence, Tuple

from modules.icons import icon, logo_svg


def _e(value: object) -> str:
    return html.escape(str(value))


def brand_html() -> str:
    return (
        '<div class="hp-brand">'
        f'<span class="hp-logo">{logo_svg(42, "brand")}</span>'
        '<div><span class="hp-brand-name">Harmonogram pracy</span>'
        '<span class="hp-brand-sub">Personel medyczny</span></div>'
        "</div>"
    )


def login_head_html() -> str:
    return (
        '<div class="hp-login-head">'
        f'<span class="hp-logo hp-logo--lg">{logo_svg(76, "login")}</span>'
        '<div class="hp-login-title">Harmonogram pracy</div>'
        '<div class="hp-login-sub">Zautomatyzowany System Generowania Harmonogramów</div>'
        "</div>"
    )


def hero_html(title: str, subtitle: str) -> str:
    return (
        '<div class="hp-hero">'
        f'<span class="hp-hero-icon">{icon("heart-pulse", 28)}</span>'
        f'<div><div class="hp-hero-title">{_e(title)}</div>'
        f'<div class="hp-hero-sub">{_e(subtitle)}</div></div>'
        "</div>"
    )


def card_head_html(icon_name: str, title: str, subtitle: Optional[str] = None) -> str:
    """Nagłówek karty; klasa .hp-card-head jest też markerem, po którym CSS stylizuje kontener."""
    sub = f'<div class="hp-card-sub">{_e(subtitle)}</div>' if subtitle else ""
    return (
        '<div class="hp-card-head">'
        f'<span class="hp-ico-chip">{icon(icon_name, 18)}</span>'
        f'<div><div class="hp-card-title">{_e(title)}</div>{sub}</div>'
        "</div>"
    )


def section_title_html(icon_name: str, title: str) -> str:
    return (
        '<div class="hp-section-title">'
        f'<span class="hp-ico-chip">{icon(icon_name, 18)}</span>'
        f"<span>{_e(title)}</span></div>"
    )


def stat_cards_html(items: Sequence[Tuple[str, str, object]]) -> str:
    """Karty statystyk: (ikona, etykieta, wartość)."""
    cards = "".join(
        '<div class="hp-stat">'
        f'<span class="hp-ico-chip">{icon(icon_name, 20)}</span>'
        f'<div><div class="hp-stat-label">{_e(label)}</div>'
        f'<div class="hp-stat-value">{_e(value)}</div></div></div>'
        for icon_name, label, value in items
    )
    return f'<div class="hp-stat-grid">{cards}</div>'


def date_chips_html(label: str, dates: Iterable[datetime.date]) -> str:
    chips = "".join(f'<span class="hp-chip">{d.strftime("%d.%m")}</span>' for d in dates)
    return (
        '<div class="hp-dates">'
        f'<span class="hp-dates-label">{icon("calendar-heart", 16)}{_e(label)}</span>'
        f"{chips}</div>"
    )


def normatyw_grid_html(items: Sequence[Tuple[str, str, str]]) -> str:
    """Siatka pozycji normatywu: (ikona, etykieta, wartość jako gotowy, escapowany HTML)."""
    cells = "".join(
        '<div class="hp-norm-item">'
        f'<span class="hp-norm-ico">{icon(icon_name, 16)}</span>'
        f'<div><div class="hp-norm-label">{_e(label)}</div>'
        f'<div class="hp-norm-value">{value_html}</div></div></div>'
        for icon_name, label, value_html in items
    )
    return f'<div class="hp-norm-grid">{cells}</div>'
