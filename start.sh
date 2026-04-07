#!/bin/bash
echo "🛡️ PhishDNS - Intelligence Platform"
echo "==================================="
echo ""

# Crear directorios
mkdir -p db logs

# Iniciar API
echo "[*] Iniciando API server en puerto 5000..."
python3 api/server.py &
API_PID=$!

# Servir dashboard (usando python http.server)
echo "[*] Iniciando Dashboard en puerto 8080..."
cd dashboard
python3 -m http.server 8080 &
DASH_PID=$!
cd ..

echo ""
echo "✅ PhishDNS activo"
echo "   Dashboard: http://localhost:8080"
echo "   API: http://localhost:5000"
echo ""
echo "Presiona Ctrl+C para detener"

# Manejar cierre
trap "kill $API_PID $DASH_PID 2>/dev/null; exit" INT

wait
