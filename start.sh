#!/usr/bin/env bash
# ==========================================================
# AirChat Quick Start Script (macOS / Linux)
# ==========================================================

set -e

PORT=8000
HOST="0.0.0.0"

# Detect Python interpreter
if [ -f "/Users/asper/miniforge3/envs/python314_Demos/bin/python" ]; then
    PYTHON_BIN="/Users/asper/miniforge3/envs/python314_Demos/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
else
    echo "❌ Error: No se encontró Python instalado."
    exit 1
fi

# Detectar y liberar el puerto si ya está en uso (evitar [Errno 48] Address already in use)
OCCUPIED_PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$OCCUPIED_PIDS" ]; then
    echo "⚠️  El puerto $PORT está ocupado por los procesos: $OCCUPIED_PIDS"
    echo "🧹 Liberando puerto $PORT..."
    for pid in $OCCUPIED_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 1
    echo "✅ Puerto $PORT liberado exitosamente."
fi

echo "🚀 Iniciando AirChat con $PYTHON_BIN..."
echo "📍 Dirección local: http://localhost:$PORT"
echo "⚙️  Presiona Ctrl+C para detener el servidor."
echo "----------------------------------------------------------"

exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT" --reload
