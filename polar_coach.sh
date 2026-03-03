#!/bin/bash
# =============================================================================
# POLAR COACH - Script de lancement
# Récupère les nouvelles séances et ouvre l'interface
# =============================================================================

POLAR_DIR="/home/datascientest/cde/polar"
PYTHON="$POLAR_DIR/pol/bin/python3"

# IP dynamique
IP=$(hostname -I | awk '{print $1}')
URL_COACH="http://$IP:5001"
URL_GRAFANA="http://$IP:3000"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          🏋️  POLAR COACH LAUNCHER         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Récupérer les nouvelles séances ───────────────────────────────────────
echo "📡 Récupération des nouvelles séances Polar..."
cd "$POLAR_DIR"
$PYTHON api/polar_exercises.py

echo ""

# ── 2. Ouvrir le navigateur ───────────────────────────────────────────────────
echo "🌐 Ouverture de l'interface Coach..."

if grep -qi microsoft /proc/version 2>/dev/null; then
    cmd.exe /c start "$URL_COACH" 2>/dev/null
elif [ -n "$DISPLAY" ]; then
    xdg-open "$URL_COACH" 2>/dev/null &
else
    echo "💡 Ouvre manuellement dans ton navigateur"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  ✅ Polar Coach prêt !                    ║"
echo "║                                          ║"
echo "║  🤖 Coach IA  : $URL_COACH  ║"
echo "║  📊 Grafana   : $URL_GRAFANA  ║"
echo "╚══════════════════════════════════════════╝"
echo ""
