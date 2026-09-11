#!/bin/bash
# Uruchamia aplikację Streamlit – tworzy venv przy pierwszym starcie.
# Dwuklik: Harmonogramy.app  lub  ten plik start.command

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

alert() {
  osascript -e "display alert \"Harmonogramy\" message \"$1\" as critical"
}

info() {
  osascript -e "display notification \"$1\" with title \"Harmonogramy\""
}

# Szukaj Pythona 3.10 (preferowany) lub dowolnego python3
PY=""
for candidate in python3.10 python3.11 python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$PY" ]; then
  alert "Brak Pythona na tym komputerze.

Zainstaluj Python 3.10 z python.org/downloads/macos/
(pobierz plik .pkg, dwuklik, Zainstaluj).

Potem uruchom aplikację ponownie."
  exit 1
fi

# Pierwsze uruchomienie – utwórz środowisko i zainstaluj pakiety
if [ ! -d ".venv" ]; then
  info "Pierwsze uruchomienie – instalacja pakietów (2–4 min)..."
  "$PY" -m venv .venv
  ./.venv/bin/pip install --upgrade pip --quiet
  ./.venv/bin/pip install -r requirements.txt --quiet
  info "Instalacja zakończona. Uruchamiam aplikację..."
fi

# Port już zajęty – prawdopodobnie aplikacja już działa
if lsof -i :8501 -sTCP:LISTEN >/dev/null 2>&1; then
  open "http://localhost:8501"
  exit 0
fi

# Uruchom serwer Streamlit w tle
./.venv/bin/streamlit run app.py \
  --server.headless=true \
  --server.port=8501 \
  --browser.gatherUsageStats=false &
STREAMLIT_PID=$!

cleanup() {
  kill "$STREAMLIT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Poczekaj aż serwer będzie gotowy (max ~30 s)
for i in $(seq 1 30); do
  if curl -sf "http://localhost:8501/_stcore/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open "http://localhost:8501"

# Trzymaj proces – zamknięcie okna Terminala zatrzymuje serwer
wait "$STREAMLIT_PID"
