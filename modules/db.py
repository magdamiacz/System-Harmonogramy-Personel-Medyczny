# Połączenie z bazą danych (PostgreSQL na Neon).
#
# Świadomie otwieramy ŚWIEŻE połączenie na każdą operację, zamiast trzymać jedno
# w st.cache_resource. Neon usypia bazę przy bezczynności, a uchwyt zapamiętany
# między odświeżeniami strony bywa wtedy martwy i sypie błędami. Przy obciążeniu
# tej aplikacji (kilka zapytań na wejście) narzut jest bez znaczenia.

import contextlib
import os
import pathlib
from typing import Iterator, Optional

import psycopg

# Pierwsze zapytanie po przerwie budzi uśpioną bazę – to potrafi potrwać.
CZAS_OCZEKIWANIA_S = 20


class BrakKonfiguracjiBazy(RuntimeError):
    """Adres bazy nie został nigdzie ustawiony."""


def _z_sekretow_streamlita() -> Optional[str]:
    """Adres z sekretów Streamlita – dostępny tylko wewnątrz działającej aplikacji."""
    try:
        import streamlit as st

        return st.secrets.get("DATABASE_URL")
    except Exception:
        # Poza aplikacją (skrypty, testy) sekrety nie istnieją i to normalne.
        return None


def _z_pliku_env() -> Optional[str]:
    """Adres z .env.local, który tworzy `neon link` – wygoda przy skryptach."""
    plik = pathlib.Path(__file__).resolve().parent.parent / ".env.local"
    if not plik.exists():
        return None
    for linia in plik.read_text(encoding="utf-8").splitlines():
        if linia.startswith("DATABASE_URL="):
            return linia.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def adres_bazy() -> str:
    """Adres połączenia. Kolejność: zmienna środowiskowa, sekrety, .env.local."""
    for zrodlo in (
        lambda: os.environ.get("DATABASE_URL"),
        _z_sekretow_streamlita,
        _z_pliku_env,
    ):
        adres = zrodlo()
        if adres:
            return adres

    raise BrakKonfiguracjiBazy(
        "Brak adresu bazy danych. Ustaw DATABASE_URL w .streamlit/secrets.toml "
        "(lokalnie) oraz w ustawieniach aplikacji na Streamlit Cloud."
    )


@contextlib.contextmanager
def polaczenie() -> Iterator[psycopg.Connection]:
    """Świeże połączenie z bazą, zamykane po wyjściu z bloku.

    prepare_threshold=None wyłącza instrukcje przygotowywane: adres wskazuje na
    pulę połączeń (PgBouncer w trybie transakcyjnym), która ich nie obsługuje.
    """
    with psycopg.connect(
        adres_bazy(),
        prepare_threshold=None,
        connect_timeout=CZAS_OCZEKIWANIA_S,
    ) as conn:
        yield conn


def zaloz_schemat() -> None:
    """Tworzy tabele, jeśli ich jeszcze nie ma. Bezpieczne przy ponownym wywołaniu."""
    plik = pathlib.Path(__file__).resolve().parent.parent / "schema.sql"
    sql = plik.read_text(encoding="utf-8")
    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)


def czy_baza_dostepna() -> bool:
    """Szybkie sprawdzenie łączności – do komunikatów w interfejsie."""
    try:
        with polaczenie() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception:
        return False
