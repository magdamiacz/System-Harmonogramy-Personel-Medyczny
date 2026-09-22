# Odczyt i zapis pracowników oraz nieobecności w bazie.
#
# Warstwa ta zwraca dokładnie te same obiekty Pracownik, które wcześniej
# powstawały z plików CSV – dzięki temu algorytm generowania grafiku pozostaje
# nietknięty, a zmienia się wyłącznie źródło danych.

import calendar
import datetime
from typing import Dict, List, Optional, Tuple

from config import get_schedule_key
from modules.data_loader import VALID_TYP_UMOWY, Pracownik
from modules.db import polaczenie

# Rodzaje wpisów w tabeli nieobecności
NIEDYSPOZYCJA = "niedyspozycja"
URLOP = "urlop"
PROSBA_WOLNE = "prosba_wolne"
PROSBA_DYZUR = "prosba_dyzur"

RODZAJE = (NIEDYSPOZYCJA, URLOP, PROSBA_WOLNE, PROSBA_DYZUR)

ETYKIETY_RODZAJOW = {
    NIEDYSPOZYCJA: "Niedyspozycja",
    URLOP: "Urlop",
    PROSBA_WOLNE: "Prośba o wolne",
    PROSBA_DYZUR: "Prośba o dyżur",
}

POLA_PRACOWNIKA = (
    "imie_nazwisko", "oddzial", "rola", "typ_umowy",
    "orzeczenie", "tylko_7h", "pracuje_w_weekendy",
)


def zakres_miesiaca(rok: int, miesiac: int) -> Tuple[datetime.date, datetime.date]:
    """Pierwszy i ostatni dzień miesiąca."""
    ostatni = calendar.monthrange(rok, miesiac)[1]
    return datetime.date(rok, miesiac, 1), datetime.date(rok, miesiac, ostatni)


# Odczyt

def wczytaj_pracownikow(
    rok: Optional[int] = None,
    miesiac: Optional[int] = None,
    tylko_aktywni: bool = True,
) -> Tuple[List[Pracownik], List[str]]:
    """Wczytuje pracowników wraz z nieobecnościami wskazanego miesiąca.

    Podanie roku i miesiąca dołącza niedyspozycje, urlopy i prośby z tego okresu.
    Bez nich wraca sama lista osób – przydatne na ekranie ewidencji.

    Zwraca (lista pracowników, lista ostrzeżeń) – tak samo jak dawne wczytywanie
    z pliku CSV, więc wywołujący nie musi rozróżniać źródła.
    """
    ostrzezenia: List[str] = []

    with polaczenie() as conn:
        with conn.cursor() as cur:
            warunek = "WHERE aktywny" if tylko_aktywni else ""
            cur.execute(f"""
                SELECT id, imie_nazwisko, oddzial, rola, typ_umowy,
                       orzeczenie, tylko_7h, pracuje_w_weekendy
                FROM pracownicy {warunek}
                ORDER BY imie_nazwisko
            """)
            wiersze = cur.fetchall()

            nieobecnosci: Dict[int, List[tuple]] = {}
            if rok and miesiac:
                od, do = zakres_miesiaca(rok, miesiac)
                cur.execute("""
                    SELECT pracownik_id, data, rodzaj, kod
                    FROM nieobecnosci
                    WHERE data BETWEEN %s AND %s
                """, (od, do))
                for pracownik_id, data, rodzaj, kod in cur.fetchall():
                    nieobecnosci.setdefault(pracownik_id, []).append((data, rodzaj, kod))

    pracownicy: List[Pracownik] = []
    for (pid, imie, oddzial, rola, typ_umowy,
         orzeczenie, tylko_7h, pracuje_w_weekendy) in wiersze:
        try:
            klucz = get_schedule_key(oddzial, rola)
        except ValueError as e:
            ostrzezenia.append(f"{imie}: {e} – pominięto.")
            continue

        pracownik = Pracownik(
            imie_nazwisko=imie,
            oddzial=oddzial,
            rola=rola,
            typ_umowy=typ_umowy,
            orzeczenie=orzeczenie,
            tylko_7h=tylko_7h,
            pracuje_w_weekendy=pracuje_w_weekendy,
            schedule_key=klucz,
        )

        for data, rodzaj, kod in nieobecnosci.get(pid, []):
            if rodzaj == NIEDYSPOZYCJA:
                pracownik.niedyspozycje.add(data)
            elif rodzaj == URLOP:
                pracownik.absencje[data] = kod or "U"
            elif rodzaj == PROSBA_WOLNE:
                pracownik.prosby[data] = "wolne"
            elif rodzaj == PROSBA_DYZUR:
                pracownik.prosby[data] = kod or "D"

        pracownicy.append(pracownik)

    return pracownicy, ostrzezenia


def wczytaj_nieobecnosci(rok: int, miesiac: int) -> List[dict]:
    """Nieobecności miesiąca wraz z nazwiskami – na potrzeby ekranu zaznaczania."""
    od, do = zakres_miesiaca(rok, miesiac)
    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.imie_nazwisko, n.data, n.rodzaj, n.kod
                FROM nieobecnosci n
                JOIN pracownicy p ON p.id = n.pracownik_id
                WHERE n.data BETWEEN %s AND %s
                ORDER BY p.imie_nazwisko, n.data
            """, (od, do))
            return [
                {"imie_nazwisko": imie, "data": data, "rodzaj": rodzaj, "kod": kod}
                for imie, data, rodzaj, kod in cur.fetchall()
            ]


# Zapis pracowników

def waliduj_pracownika(dane: dict) -> List[str]:
    """Sprawdza dane z formularza. Zwraca listę błędów (pusta = w porządku)."""
    bledy: List[str] = []

    imie = str(dane.get("imie_nazwisko") or "").strip()
    if not imie:
        bledy.append("Imię i nazwisko jest wymagane.")

    typ = str(dane.get("typ_umowy") or "").strip().lower()
    if typ not in VALID_TYP_UMOWY:
        bledy.append(
            f"Nieznany typ umowy '{dane.get('typ_umowy')}'. "
            f"Dozwolone: {', '.join(sorted(VALID_TYP_UMOWY))}."
        )

    try:
        get_schedule_key(str(dane.get("oddzial") or ""), str(dane.get("rola") or ""))
    except ValueError as e:
        bledy.append(str(e))

    return bledy


def zapisz_pracownika(dane: dict) -> None:
    """Dodaje pracownika lub aktualizuje istniejącego (klucz: imię i nazwisko)."""
    bledy = waliduj_pracownika(dane)
    if bledy:
        raise ValueError(" ".join(bledy))

    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pracownicy
                    (imie_nazwisko, oddzial, rola, typ_umowy,
                     orzeczenie, tylko_7h, pracuje_w_weekendy, aktywny)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (imie_nazwisko) DO UPDATE SET
                    oddzial            = EXCLUDED.oddzial,
                    rola               = EXCLUDED.rola,
                    typ_umowy          = EXCLUDED.typ_umowy,
                    orzeczenie         = EXCLUDED.orzeczenie,
                    tylko_7h           = EXCLUDED.tylko_7h,
                    pracuje_w_weekendy = EXCLUDED.pracuje_w_weekendy,
                    aktywny            = TRUE
            """, (
                str(dane["imie_nazwisko"]).strip(),
                str(dane["oddzial"]).strip(),
                str(dane["rola"]).strip(),
                str(dane["typ_umowy"]).strip().lower(),
                bool(dane.get("orzeczenie", False)),
                bool(dane.get("tylko_7h", False)),
                bool(dane.get("pracuje_w_weekendy", True)),
            ))


def usun_pracownika(imie_nazwisko: str) -> None:
    """Miękkie usunięcie – wpis zostaje, ale znika z list i z generowania."""
    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pracownicy SET aktywny = FALSE WHERE imie_nazwisko = %s",
                (imie_nazwisko,),
            )


# Zapis nieobecności

def zapisz_nieobecnosc(
    imie_nazwisko: str,
    data: datetime.date,
    rodzaj: str,
    kod: Optional[str] = None,
) -> None:
    """Zapisuje nieobecność. Ponowne zaznaczenie tego samego dnia nadpisuje wpis."""
    if rodzaj not in RODZAJE:
        raise ValueError(f"Nieznany rodzaj nieobecności: {rodzaj}")

    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO nieobecnosci (pracownik_id, data, rodzaj, kod)
                SELECT id, %s, %s, %s FROM pracownicy WHERE imie_nazwisko = %s
                ON CONFLICT (pracownik_id, data, rodzaj) DO UPDATE SET kod = EXCLUDED.kod
            """, (data, rodzaj, kod, imie_nazwisko))


def usun_nieobecnosc(imie_nazwisko: str, data: datetime.date, rodzaj: str) -> None:
    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM nieobecnosci
                WHERE data = %s AND rodzaj = %s AND pracownik_id = (
                    SELECT id FROM pracownicy WHERE imie_nazwisko = %s
                )
            """, (data, rodzaj, imie_nazwisko))


def zapisz_zakres_nieobecnosci(
    imie_nazwisko: str,
    od: datetime.date,
    do: datetime.date,
    rodzaj: str,
    kod: Optional[str] = None,
) -> int:
    """Zaznacza nieobecność dla każdego dnia zakresu. Zwraca liczbę dni.

    Całość idzie jednym połączeniem: baza stoi za oceanem, więc osobne
    połączenie na każdy dzień urlopu zauważalnie by spowalniało zapis.
    """
    if rodzaj not in RODZAJE:
        raise ValueError(f"Nieznany rodzaj nieobecności: {rodzaj}")
    if do < od:
        raise ValueError("Data końcowa jest wcześniejsza niż początkowa.")

    dni = [od + datetime.timedelta(days=n) for n in range((do - od).days + 1)]
    with polaczenie() as conn:
        with conn.cursor() as cur:
            cur.executemany("""
                INSERT INTO nieobecnosci (pracownik_id, data, rodzaj, kod)
                SELECT id, %s, %s, %s FROM pracownicy WHERE imie_nazwisko = %s
                ON CONFLICT (pracownik_id, data, rodzaj) DO UPDATE SET kod = EXCLUDED.kod
            """, [(dzien, rodzaj, kod, imie_nazwisko) for dzien in dni])
    return len(dni)
