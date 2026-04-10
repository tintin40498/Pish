#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛡️ Pish - Anti-Phishing Intelligence"
echo "===================================="

# Verificar licencia
python3 "$BASE_DIR/core/verify_license.py"
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ No se pudo verificar la licencia."
    echo "   Visitá https://tintin40498.github.io/pish/ para obtener una."
    exit 1
fi

echo ""
echo "✅ Licencia válida. Iniciando Pish..."
echo ""

# Iniciar API y dashboard
python3 api/web_api.py &
python3 -m http.server 8080 --directory dashboard &

wait
