# Ikony liniowe (Lucide, licencja ISC) jako inline SVG, maski CSS oraz logo aplikacji.

from typing import Dict
from urllib.parse import quote

_ICONS: Dict[str, str] = {
    "heart-pulse": (
        '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2'
        'A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/>'
    ),
    "calendar-days": (
        '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/>'
        '<path d="M3 10h18"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/>'
        '<path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>'
    ),
    "folder-up": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4'
        'a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/><path d="M12 10v6"/><path d="m9 13 3-3 3 3"/>'
    ),
    "log-out": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>'
    ),
    "log-in": (
        '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/>'
    ),
    "sparkles": (
        '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5'
        'l1.58-6.14a.5.5 0 0 1 .96 0l1.58 6.14a2 2 0 0 0 1.44 1.44l6.14 1.58a.5.5 0 0 1 0 .96L15.5 14.06'
        'a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/>'
    ),
    "circle-alert": (
        '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>'
    ),
    "triangle-alert": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/>'
    ),
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "clipboard-list": (
        '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6'
        'a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/>'
        '<path d="M8 16h.01"/>'
    ),
    "calendar-heart": (
        '<path d="M3 10h18V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h7"/><path d="M8 2v4"/>'
        '<path d="M16 2v4"/><path d="M21.29 14.7a2.43 2.43 0 0 0-2.65-.52c-.3.12-.57.3-.8.53l-.34.34'
        '-.35-.34a2.43 2.43 0 0 0-2.65-.53c-.3.12-.56.3-.79.53-.95.94-1 2.53.2 3.74L17.5 22l3.6-3.55'
        'c1.2-1.21 1.14-2.8.19-3.74Z"/>'
    ),
    "users": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "briefcase": (
        '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>'
    ),
    "clipboard-check": (
        '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6'
        'a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>'
    ),
    "file-spreadsheet": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/>'
        '<path d="M14 17h2"/>'
    ),
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
}

_SVG_ATTRS = (
    'viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
)

_HEART_PATH = (
    "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2"
    "A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"
)
_PULSE_PATH = "M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"


def icon(name: str, size: int = 18, cls: str = "hp-ico") -> str:
    """Inline SVG ikony (kolor dziedziczony przez currentColor)."""
    return (
        f'<svg class="{cls}" width="{size}" height="{size}" {_SVG_ATTRS} stroke="currentColor" '
        f'aria-hidden="true" focusable="false">{_ICONS[name]}</svg>'
    )


def icon_mask_url(name: str) -> str:
    """Ikona jako data-URI do CSS mask-image (kolor nadaje background-color)."""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" {_SVG_ATTRS} stroke="#000">{_ICONS[name]}</svg>'
    return f'url("data:image/svg+xml,{quote(svg, safe="")}")'


def logo_svg(size: int = 48, uid: str = "logo") -> str:
    """Logo: biała płytka z turkusową krawędzią, serce w gradiencie i biała linia pulsu.

    Zaczyna się dokładnie od '<svg ', więc nadaje się też jako page_icon.
    uid musi być unikalny w obrębie strony (id gradientu jest globalne).
    """
    gid = f"hp-g-{uid}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 48 48" '
        'role="img" aria-label="Harmonogram pracy">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#5EEAD4"/><stop offset="0.55" stop-color="#14B8A6"/>'
        '<stop offset="1" stop-color="#0D9488"/></linearGradient></defs>'
        '<rect x="1" y="3" width="46" height="44" rx="14" fill="#14B8A6"/>'
        '<rect x="1" y="1" width="46" height="44" rx="14" fill="#FFFFFF"/>'
        '<g transform="translate(9 8) scale(1.25)">'
        f'<path d="{_HEART_PATH}" fill="url(#{gid})"/>'
        f'<path d="{_PULSE_PATH}" fill="none" stroke="#FFFFFF" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</g></svg>"
    )
