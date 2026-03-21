# modules/data_loader.py
# Wczytywanie danych personelu oraz niedyspozycji z plików CSV.
# Walidacja struktury pliku i typów pól.

import datetime
import io
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from config import get_schedule_key


# ---------------------------------------------------------------------------
# Model danych pracownika
# ---------------------------------------------------------------------------

@dataclass
class Pracownik:
    """Reprezentacja jednego pracownika."""
    imie_nazwisko: str
    oddzial: str
    rola: str
    typ_umowy: str          # "etat", "duzy_kontrakt", "maly_kontrakt"
    orzeczenie: bool        # True = skrócony czas pracy (7h/dobę)
    tylko_7h: bool          # True = pracuje wyłącznie na zmianie R (7h35)
    pracuje_w_weekendy: bool
    schedule_key: str       # klucz harmonogramu, np. "gastro_piel"

    # Niedyspozycje (daty, kiedy pracownik jest niedostępny)
    niedyspozycje: Set[datetime.date] = field(default_factory=set)

    def __hash__(self):
        return hash(self.imie_nazwisko)

    def __eq__(self, other):
        if isinstance(other, Pracownik):
            return self.imie_nazwisko == other.imie_nazwisko
        return False

    @property
    def is_etat(self) -> bool:
        return self.typ_umowy == "etat"

    @property
    def is_kontrakt(self) -> bool:
        return self.typ_umowy in ("duzy_kontrakt", "maly_kontrakt")

    @property
    def is_duzy_kontrakt(self) -> bool:
        return self.typ_umowy == "duzy_kontrakt"

    @property
    def is_maly_kontrakt(self) -> bool:
        return self.typ_umowy == "maly_kontrakt"


# ---------------------------------------------------------------------------
# Wczytywanie pliku personelu
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS_PERSONEL = {
    "imie_nazwisko", "oddzial", "rola", "typ_umowy",
    "orzeczenie", "tylko_7h", "pracuje_w_weekendy"
}

VALID_TYP_UMOWY = {"etat", "duzy_kontrakt", "maly_kontrakt"}
VALID_BOOL_VALUES = {"tak", "nie"}


def _parse_bool(val: str, kolumna: str, wiersz: int) -> bool:
    """Konwertuje 'tak'/'nie' na True/False z czytelnym komunikatem błędu."""
    v = str(val).strip().lower()
    if v not in VALID_BOOL_VALUES:
        raise ValueError(
            f"Wiersz {wiersz}: kolumna '{kolumna}' ma wartość '{val}', "
            f"oczekiwano 'tak' lub 'nie'."
        )
    return v == "tak"


def wczytaj_personel(source) -> Tuple[List[Pracownik], List[str]]:
    """
    Wczytuje plik CSV z danymi personelu.

    Parametry:
        source: ścieżka do pliku (str) lub obiekt BytesIO/StringIO.

    Zwraca:
        (lista pracowników, lista komunikatów ostrzeżeń)
    """
    bledy: List[str] = []

    # Wczytaj DataFrame
    try:
        df = pd.read_csv(source, encoding="utf-8", sep=",", skipinitialspace=True)
    except Exception as e:
        raise ValueError(f"Nie można wczytać pliku personelu: {e}")

    # Sprawdź kolumny
    brakujace = REQUIRED_COLUMNS_PERSONEL - set(df.columns)
    if brakujace:
        raise ValueError(f"Brakujące kolumny w pliku personelu: {brakujace}")

    pracownicy: List[Pracownik] = []

    for idx, row in df.iterrows():
        nr = idx + 2  # Numer wiersza w CSV (1 = nagłówek)

        # Walidacja typu umowy
        typ = str(row["typ_umowy"]).strip().lower()
        if typ not in VALID_TYP_UMOWY:
            bledy.append(
                f"Wiersz {nr} ({row['imie_nazwisko']}): "
                f"nieznany typ_umowy '{row['typ_umowy']}' – pominięto."
            )
            continue

        # Walidacja booleanów
        try:
            orzeczenie = _parse_bool(row["orzeczenie"], "orzeczenie", nr)
            tylko_7h = _parse_bool(row["tylko_7h"], "tylko_7h", nr)
            pracuje_w_weekendy = _parse_bool(row["pracuje_w_weekendy"], "pracuje_w_weekendy", nr)
        except ValueError as e:
            bledy.append(str(e) + " – pominięto.")
            continue

        # Ustalenie klucza harmonogramu
        try:
            sched_key = get_schedule_key(str(row["oddzial"]), str(row["rola"]))
        except ValueError as e:
            bledy.append(f"Wiersz {nr} ({row['imie_nazwisko']}): {e} – pominięto.")
            continue

        pracownicy.append(Pracownik(
            imie_nazwisko=str(row["imie_nazwisko"]).strip(),
            oddzial=str(row["oddzial"]).strip(),
            rola=str(row["rola"]).strip(),
            typ_umowy=typ,
            orzeczenie=orzeczenie,
            tylko_7h=tylko_7h,
            pracuje_w_weekendy=pracuje_w_weekendy,
            schedule_key=sched_key,
        ))

    return pracownicy, bledy


# ---------------------------------------------------------------------------
# Wczytywanie niedyspozycji
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS_NIEDYSP = {"imie_nazwisko", "data"}


def wczytaj_niedyspozycje(
    source,
    pracownicy: List[Pracownik]
) -> Tuple[Dict[str, Set[datetime.date]], List[str]]:
    """
    Wczytuje CSV z niedyspozycjami i przypisuje je do pracowników.

    Format CSV:
        imie_nazwisko,data
        Adamczyk Halina,2026-01-05

    Zwraca:
        (słownik {imie_nazwisko: {daty}}, lista ostrzeżeń)
    """
    bledy: List[str] = []
    niedyspozycje: Dict[str, Set[datetime.date]] = {}

    known_names = {p.imie_nazwisko for p in pracownicy}

    try:
        df = pd.read_csv(source, encoding="utf-8", sep=",", skipinitialspace=True)
    except Exception as e:
        raise ValueError(f"Nie można wczytać pliku niedyspozycji: {e}")

    brakujace = REQUIRED_COLUMNS_NIEDYSP - set(df.columns)
    if brakujace:
        raise ValueError(f"Brakujące kolumny w pliku niedyspozycji: {brakujace}")

    for idx, row in df.iterrows():
        nr = idx + 2
        imie = str(row["imie_nazwisko"]).strip()

        if imie not in known_names:
            bledy.append(
                f"Wiersz {nr}: pracownik '{imie}' nie istnieje w pliku personelu – pominięto."
            )
            continue

        try:
            data = datetime.date.fromisoformat(str(row["data"]).strip())
        except ValueError:
            bledy.append(
                f"Wiersz {nr}: nieprawidłowy format daty '{row['data']}' "
                f"(oczekiwano YYYY-MM-DD) – pominięto."
            )
            continue

        if imie not in niedyspozycje:
            niedyspozycje[imie] = set()
        niedyspozycje[imie].add(data)

    # Przypisz niedyspozycje do obiektów Pracownik
    for p in pracownicy:
        if p.imie_nazwisko in niedyspozycje:
            p.niedyspozycje = niedyspozycje[p.imie_nazwisko]

    return niedyspozycje, bledy


# ---------------------------------------------------------------------------
# Grupowanie pracowników wg harmonogramu
# ---------------------------------------------------------------------------

def grupuj_wg_harmonogramu(
    pracownicy: List[Pracownik],
) -> Dict[str, List[Pracownik]]:
    """
    Zwraca słownik {schedule_key: [pracownicy]}.
    """
    grupy: Dict[str, List[Pracownik]] = {}
    for p in pracownicy:
        grupy.setdefault(p.schedule_key, []).append(p)
    return grupy
