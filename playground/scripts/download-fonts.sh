#!/bin/bash
# Download Inter font for embedded resources (TC01)
# Run once: ./scripts/download-fonts.sh

FONT_DIR="$(dirname "$0")/../frontend/public/fonts"
mkdir -p "$FONT_DIR"

echo "Downloading Inter font..."
curl -L -o "$FONT_DIR/inter.woff2" \
  "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuLyfAZ9hiA.woff2"

if [ -f "$FONT_DIR/inter.woff2" ] && [ -s "$FONT_DIR/inter.woff2" ]; then
    echo "OK - Inter font downloaded to $FONT_DIR/inter.woff2"
else
    echo "WARN - Download may have failed. The app will work without it (falls back to system fonts)."
fi
