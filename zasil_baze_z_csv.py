"""Jednorazowe przeniesienie danych z plików CSV do bazy.

Uruchomienie:  python zasil_baze_z_csv.py

Skrypt można uruchamiać wielokrotnie – pracownicy są dopisywani lub
aktualizowani po imieniu i nazwisku, a nieobecności po dniu.

Po udanym przeniesieniu pliki CSV z danymi osobowymi personelu należy usunąć
z repozytorium; ten skrypt przestaje być wtedy potrzebny.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modules import repository as repo
from modules.data_loader import wczytaj_niedyspozycje, wczytaj_personel
from modules.db import zaloz_schemat

KATALOG = Path(__file__).resolve().parent
PLIK_PERSONEL = KATALOG / "personel_wlasciwy.csv"
PLIK_NIEDYSPOZYCJE = KATALOG / "niedyspozycje.csv"


def main() -> int:
    if not PLIK_PERSONEL.exists():
        print(f"Brak pliku {PLIK_PERSONEL.name} – nie ma czego przenosić.")
        return 1

    zaloz_schemat()

    pracownicy, ostrzezenia = wczytaj_personel(str(PLIK_PERSONEL))
    for uwaga in ostrzezenia:
        print("  uwaga:", uwaga)

    zapisani = 0
    for p in pracownicy:
        repo.zapisz_pracownika({
            "imie_nazwisko": p.imie_nazwisko,
            "oddzial": p.oddzial,
            "rola": p.rola,
            "typ_umowy": p.typ_umowy,
            "orzeczenie": p.orzeczenie,
            "tylko_7h": p.tylko_7h,
            "pracuje_w_weekendy": p.pracuje_w_weekendy,
        })
        zapisani += 1
    print(f"Pracownicy: zapisano {zapisani}.")

    if PLIK_NIEDYSPOZYCJE.exists():
        wczytaj_niedyspozycje(str(PLIK_NIEDYSPOZYCJE), pracownicy)
        wpisy = 0
        for p in pracownicy:
            for data in sorted(p.niedyspozycje):
                repo.zapisz_nieobecnosc(p.imie_nazwisko, data, repo.NIEDYSPOZYCJA)
                wpisy += 1
        print(f"Niedyspozycje: zapisano {wpisy}.")
    else:
        print("Brak pliku niedyspozycji – pomijam.")

    w_bazie, _ = repo.wczytaj_pracownikow()
    print(f"\nW bazie jest teraz {len(w_bazie)} aktywnych pracowników.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
