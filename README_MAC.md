# Harmonogramy – instrukcja dla MacBooka (Apple Silicon)

Aplikacja do generowania harmonogramów personelu medycznego.  
Działa **offline** – dane nie wychodzą z komputera.

---

## Szybki start (3 kroki)

### Krok 1: Zainstaluj Pythona (tylko raz)

1. Otwórz w przeglądarce: **https://www.python.org/downloads/macos/**
2. Pobierz **Python 3.10** (plik `.pkg`, np. `python-3.10.14-macos11.pkg`).
3. Dwuklik na pobrany plik → **Kontynuuj** → **Zainstaluj** → wpisz hasło Maca.
4. Po instalacji możesz zamknąć instalator.

> Python jest potrzebny tylko przy pierwszej konfiguracji. Nie musisz go uruchamiać ręcznie.

---

### Krok 2: Skopiuj folder aplikacji

1. Rozpakuj plik **`Harmonogramy-Mac.zip`** (dwuklik).
2. Przeciągnij folder **`Harmonogramy`** do **Programy** (`Aplikacje` / `Applications`).

Folder powinien zawierać m.in.:
- `app.py`
- `start.command`
- `Harmonogramy.app`

---

### Krok 3: Ikona na pulpicie

1. Otwórz folder **`Harmonogramy`** (w Programach).
2. Przeciągnij **`Harmonogramy.app`** na **Pulpit**.
3. **Dwuklik** na ikonę na pulpicie.

Przy **pierwszym uruchomieniu** aplikacja pobierze potrzebne pakiety – to trwa **2–4 minuty**.  
Kolejne uruchomienia trwają kilka sekund.

Aplikacja otworzy się w przeglądarce (Safari lub Chrome) pod adresem `http://localhost:8501`.

---

## Pierwsze uruchomienie – komunikat macOS (Gatekeeper)

macOS może pokazać: *„Nie można otworzyć, ponieważ pochodzi od niezidentyfikowanego dewelopera”*.

**Rozwiązanie (jednorazowo):**

1. **Prawy klik** (lub Ctrl + klik) na ikonę **`Harmonogramy`** na pulpicie.
2. Wybierz **Otwórz**.
3. Kliknij **Otwórz** w oknie dialogowym.

Przy następnych uruchomieniach wystarczy zwykły dwuklik.

---

## Jak korzystać z aplikacji

1. W panelu bocznym wgraj plik **personelu (CSV)**.
2. Opcjonalnie wgraj plik **niedyspozycji (CSV)**.
3. Wybierz **rok** i **miesiąc**.
4. Kliknij **Generuj harmonogram**.
5. Przejrzyj zakładki z harmonogramami i eksportuj wynik.

Przykładowe pliki CSV są w folderze aplikacji: `personel_wlasciwy.csv`, `niedyspozycje.csv`.

---

## Zamykanie aplikacji

- Zamknij kartę w przeglądarce.
- **Zatrzymaj aplikację:** kliknij ikonę **Harmonogramy** na Docku (pasek u dołu) prawym przyciskiem → **Zakończ** (Quit).  
  Albo: **Cmd + Q** gdy ikona aplikacji jest aktywna.
- Jeśli otworzyło się okno Terminala – zamknij je czerwonym przyciskiem.

---

## Rozwiązywanie problemów

| Problem | Co zrobić |
|--------|-----------|
| Komunikat „Brak Pythona” | Zainstaluj Python 3.10 z python.org (Krok 1) i uruchom ponownie. |
| Długo nic się nie dzieje | Pierwsze uruchomienie trwa 2–4 min – poczekaj. |
| Strona się nie otwiera | Otwórz ręcznie: **http://localhost:8501** |
| Port zajęty / aplikacja „wisi” | Uruchom ponownie – skrypt sam wykryje działającą instancję. |
| Błąd uprawnień | W Terminalu: `chmod +x ~/Applications/Harmonogramy/start.command` |

---

## Aktualizacja aplikacji

1. Zamknij aplikację.
2. Zastąp folder `Harmonogramy` nową wersją z zipa.
3. Usuń podfolder `.venv` w folderze aplikacji (jeśli istnieje) – wymusi ponowną instalację pakietów.
4. Uruchom **`Harmonogramy.app`** ponownie.

---

## Kontakt techniczny

W razie problemów skontaktuj się z osobą, która przekazała Ci tę aplikację.
