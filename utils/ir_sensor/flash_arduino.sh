#!/usr/bin/env bash
# flash_arduino.sh — Compile & upload IR sensor sketch to Arduino Nano
#
# Usage: ./flash_arduino.sh [--port /dev/ttyUSB0] [--fqbn arduino:avr:nano]
#
# Requires: arduino-cli installed and in PATH.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKETCH="$SCRIPT_DIR/ir-read.ino"
PORT="${PORT:-/dev/ttyUSB0}"
FQBN="${FQBN:-arduino:avr:nano:cpu=atmega168}"

# ── colour helpers ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ── detect board ────────────────────────────────────────────────
info "Looking for Arduino on $PORT ..."
if [ ! -e "$PORT" ]; then
    # try auto-detect
    PORT=$(arduino-cli board list --format json 2>/dev/null | python3 -c "
import json,sys
data=json.load(sys.stdin)
for d in data:
    if d.get('boards'):
        print(d['boards'][0].get('address',''))
        sys.exit(0)
print('')
" 2>/dev/null || echo "")
    if [ -z "$PORT" ]; then
        err "No Arduino found. Is it plugged in?"
        err "Try: arduino-cli board list"
        exit 1
    fi
    info "Auto-detected board at $PORT"
fi

# ── compile ─────────────────────────────────────────────────────
info "Compiling sketch ..."
arduino-cli compile \
    --fqbn "$FQBN" \
    "$SKETCH"

# ── upload ──────────────────────────────────────────────────────
info "Uploading to $PORT ..."
arduino-cli upload \
    --fqbn "$FQBN" \
    --port "$PORT" \
    "$SKETCH"

info "Flash complete! Board should start sending data at 9600 baud."
info "Test with: python3 -c 'import serial; s=serial.Serial(\"$PORT\",9600,timeout=2); print(s.readline())'"
