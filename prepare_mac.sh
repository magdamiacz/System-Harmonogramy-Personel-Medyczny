#!/bin/bash
# Przygotowanie paczki Mac: uprawnienia wykonywania + opcjonalnie ikona.
# Uruchom na Macu w folderze projektu: ./prepare_mac.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Ustawianie uprawnień wykonywania..."
chmod +x start.command
chmod +x "Harmonogramy.app/Contents/MacOS/Harmonogramy"

echo "==> Gotowe."
echo ""
echo "Opcjonalnie – własna ikona:"
echo "  1. Przygotuj plik PNG 512×512 (np. ikona szpitala / kalendarza)."
echo "  2. Prawy klik na Harmonogramy.app → Pobierz informacje (Get Info)."
echo "  3. Przeciągnij PNG na małą ikonę w lewym górnym rogu okna."
echo ""
echo "Alternatywa (Automator):"
echo "  Automator → Aplikacja → Run Shell Script → exec \"\$DIR/start.command\""
echo "  (Obecny Harmonogramy.app działa bez Automatora – to gotowy bundle.)"
echo ""
echo "Następny krok: ./package_mac.sh"
