# 🚀 Instrukcja Deploymentu Aplikacji Streamlit

## Krok 1: Przygotowanie danych lokalnych

### Zmiana hasła logowania (WAŻNE!)

Otwórz plik `.streamlit/secrets.toml` i zmień domyślne hasło na swoje:

```toml
USERNAME = "pielegniarki"
PASSWORD = "TwojeMocneHasło123!"  # ← Zmień tutaj
```

### Testowanie aplikacji lokalnie

```bash
# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie aplikacji
streamlit run app.py
```

Aplikacja otworzy się na `http://localhost:8501`

**Login:** `pielegniarki`  
**Hasło:** (to co wstawiłeś w secrets.toml)

---

## Krok 2: Przygotowanie GitHub

### 2.1. Inicjalizacja Git (jeśli nie zrobiony)

```bash
git init
git add .
git commit -m "Initial commit: dodanie logowania i deployment config"
```

### 2.2. Stworzenie repozytorium na GitHub

1. Przejdź do https://github.com/new
2. Wpisz nazwę: `harmonogramy-personel`
3. **NIE** inicjalizuj z README
4. Kliknij "Create repository"

### 2.3. Push na GitHub

```bash
git remote add origin https://github.com/TwojaLogin/harmonogramy-personel.git
git branch -M main
git push -u origin main
```

---

## Krok 3: Deploy na Streamlit Cloud (DARMOWE)

### 3.1. Zalogowanie na Streamlit Cloud

1. Przejdź do https://streamlit.io/cloud
2. Kliknij "Sign up"
3. Zaloguj się przez GitHub (najprościej)

### 3.2. Deploy aplikacji

1. Po zalogowaniu, kliknij **"New app"**
2. Podaj dane:
   - **Repository:** `TwojaLogin/harmonogramy-personel`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Kliknij **"Deploy"**

Aplikacja będzie dostępna na:
```
https://harmonogramy-personel.streamlit.app
```

### 3.3. Ustawienie SECRET (hasła) na Streamlit Cloud

Po deploymencie:

1. Otwórz aplikację na https://harmonogramy-personel.streamlit.app
2. Kliknij menu (3 kreski) → **Settings**
3. Przejdź do zakładki **Secrets**
4. Wklej treść pliku `.streamlit/secrets.toml`:

```toml
USERNAME = "pielegniarki"
PASSWORD = "TwojeMocneHasło123!"
```

5. Kliknij **Save** → aplikacja się restartuje automatycznie

---

## Krok 4: Użytkowanie

### Dla Ciebie (administratora):
- Login: `pielegniarki`
- Hasło: (to co ustawiłeś)

### Dla pielęgniarki:
Podaj jej link i dane logowania:
```
Link: https://harmonogramy-personel.streamlit.app
Login: pielegniarki
Hasło: (to co ustawiłeś)
```

---

## 📋 LISTA KONTROLNA

- [ ] Zmienisz hasło w `.streamlit/secrets.toml`
- [ ] Aplikacja działa lokalnie (`streamlit run app.py`)
- [ ] Dodałeś plik `.gitignore` (patrz niżej)
- [ ] Pushowałeś do GitHub
- [ ] Deployowałeś na Streamlit Cloud
- [ ] Ustawiłeś Secrets w Streamlit Cloud
- [ ] Testujesz login na https://harmonogramy-personel.streamlit.app

---

## ⚠️ Ważne: .gitignore

Dodaj do pliku `.gitignore` (lub utwórz nowy):

```
.streamlit/secrets.toml
__pycache__/
*.pyc
.env
.DS_Store
```

**Nigdy nie commituj `secrets.toml`!** Tylko ustawiasz go w Streamlit Cloud UI.

---

## 🆘 Troubleshooting

### Problemy z logowaniem?
- Sprawdź czy Secrets ustawiłeś w Streamlit Cloud (Settings → Secrets)
- Upewnij się że hasło jest dokładnie takie jak w secrets.toml

### Aplikacja nie pokazuje dane?
- Sprawdź czy pliki CSV (personel, niedyspozycje) są dostępne
- Log błędów: kliknij menu → "Manage app" → "Logs"

### Chcesz zmienić hasło?
- Zmień wartość w Streamlit Cloud (Settings → Secrets)
- Aplikacja się restartuje automatycznie

---

## 💡 Opcjonalnie: Własna domena

Jeśli chcesz harmonogramy.tvoja-domena.pl zamiast streamlit.app:

1. Kup domenę (Namecheap, GoDaddy, etc.) - koszt ~1-2$/rok
2. W Streamlit Cloud (Settings → Custom domain) dodaj domenę
3. Skonfiguruj DNS (instrukcje w Streamlit Cloud)

Koszt: ~2$/rok za domenę + 0$ za hosting = prawie gratis! ✅

---

## 📞 Potrzebujesz pomocy?

- Streamlit docs: https://docs.streamlit.io
- Claude Code: zawsze mogę pomóc w modyfikacji aplikacji
