-- Schemat bazy danych aplikacji (PostgreSQL / Neon).
-- Zakładany raz; wszystkie polecenia są bezpieczne przy ponownym uruchomieniu.

CREATE TABLE IF NOT EXISTS pracownicy (
    id                 SERIAL PRIMARY KEY,
    -- Imię i nazwisko jest kluczem biznesowym: algorytm i grafiki identyfikują
    -- pracownika po tym polu, więc musi być unikalne.
    imie_nazwisko      TEXT NOT NULL UNIQUE,
    oddzial            TEXT NOT NULL,
    rola               TEXT NOT NULL,
    typ_umowy          TEXT NOT NULL
                       CHECK (typ_umowy IN ('etat', 'duzy_kontrakt', 'maly_kontrakt')),
    orzeczenie         BOOLEAN NOT NULL DEFAULT FALSE,
    tylko_7h           BOOLEAN NOT NULL DEFAULT FALSE,
    pracuje_w_weekendy BOOLEAN NOT NULL DEFAULT TRUE,
    -- Miękkie usuwanie: pracownik znika z list, ale dawne grafiki zostają czytelne.
    aktywny            BOOLEAN NOT NULL DEFAULT TRUE,
    utworzono          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nieobecnosci (
    id           SERIAL PRIMARY KEY,
    pracownik_id INTEGER NOT NULL REFERENCES pracownicy(id) ON DELETE CASCADE,
    data         DATE NOT NULL,
    rodzaj       TEXT NOT NULL
                 CHECK (rodzaj IN ('niedyspozycja', 'urlop', 'prosba_wolne', 'prosba_dyzur')),
    -- Znaczenie zależy od rodzaju:
    --   urlop        -> kod urlopu z godzinami, np. 'U12' albo 'U'
    --   prosba_dyzur -> kod żądanej zmiany, np. 'D' lub 'N'
    --   pozostałe    -> NULL
    -- Godziny trzymamy wewnątrz kodu, żeby nie mieć dwóch źródeł prawdy;
    -- rozszyfrowuje go modules/absences.py.
    kod          TEXT,
    utworzono    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Jeden wpis danego rodzaju na osobę i dzień; ponowne zaznaczenie nadpisuje.
    UNIQUE (pracownik_id, data, rodzaj)
);

-- Grafik generujemy zawsze dla jednego miesiąca, więc filtrujemy po dacie.
CREATE INDEX IF NOT EXISTS idx_nieobecnosci_data ON nieobecnosci (data);
CREATE INDEX IF NOT EXISTS idx_nieobecnosci_pracownik ON nieobecnosci (pracownik_id);
