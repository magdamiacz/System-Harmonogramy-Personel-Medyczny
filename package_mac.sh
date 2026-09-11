#!/bin/bash
# Tworzy plik Harmonogramy-Mac.zip gotowy do przekazania użytkownikowi.
# Uruchom na Macu: ./package_mac.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Upewnij się, że skrypty są wykonywalne
chmod +x start.command 2>/dev/null || true
chmod +x "Harmonogramy.app/Contents/MacOS/Harmonogramy" 2>/dev/null || true
chmod +x prepare_mac.sh 2>/dev/null || true

OUTPUT="Harmonogramy-Mac.zip"
STAGING=".package_staging"

echo "==> Pakowanie aplikacji do $OUTPUT ..."

rm -rf "$STAGING"
mkdir -p "$STAGING/Harmonogramy"

# Skopiuj pliki aplikacji (bez cache, venv, git)
cp app.py config.py requirements.txt start.command README_MAC.md "$STAGING/Harmonogramy/"
cp personel_wlasciwy.csv niedyspozycje.csv "$STAGING/Harmonogramy/" 2>/dev/null || true
cp -R modules "$STAGING/Harmonogramy/"
cp -R "Harmonogramy.app" "$STAGING/Harmonogramy/"

# Usuń cache Pythona ze stagingu
find "$STAGING" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$STAGING" -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf "$STAGING/Harmonogramy/.venv" 2>/dev/null || true

rm -f "$OUTPUT"
(cd "$STAGING" && zip -r "../$OUTPUT" Harmonogramy)

rm -rf "$STAGING"

echo "==> Gotowe: $DIR/$OUTPUT"
echo "    Przekaż ten plik zip użytkownikowi MacBooka."
