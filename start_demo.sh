#!/usr/bin/env bash
# SmartPark Vision AI - Linux / macOS Launcher

set -e

echo "==============================================================================="
echo "  SmartPark Vision AI - Centre de Contrôle Souverain (Algérie)"
echo "  Conforme Loi 18-07 & Loi 25-11 (ANPDP) - Zéro Transfert Étranger"
echo "==============================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 introuvable. Ouvrez directement static/index.html dans votre navigateur."
    exit 1
fi

if ! python3 -c "import fastapi, uvicorn, numpy" &> /dev/null; then
    echo "[*] Installation des dépendances (FastAPI, Uvicorn, NumPy)..."
    python3 -m pip install -r requirements.txt
fi

echo "[*] Démarrage du serveur sur http://127.0.0.1:8080 ..."
(sleep 2 && (command -v xdg-open &> /dev/null && xdg-open "http://127.0.0.1:8080" || open "http://127.0.0.1:8080")) &
python3 run_demo.py
