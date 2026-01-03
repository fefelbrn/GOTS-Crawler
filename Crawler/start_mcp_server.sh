#!/bin/bash

echo ""
echo "================================================================"
echo "🚀 Démarrage du serveur MCP GOTS Crawler"
echo "================================================================"
echo ""

# Vérifier si le venv existe (Windows a .venv au lieu de venv parfois)
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
else
    echo "❌ Erreur: venv introuvable"
    echo "💡 Crée d'abord le venv: python -m venv venv"
    exit 1
fi

# Activer le venv (syntaxe Windows Git Bash)
echo "🔧 Activation du venv..."
source "\$VENV_PATH/Scripts/activate"

# Vérifier que le venv est activé
if [ -z "\$VIRTUAL_ENV" ]; then
    echo "❌ Erreur: venv non activé"
    exit 1
fi

echo "✅ Venv activé: \$VIRTUAL_ENV"
echo ""

# Vérifier que fastmcp est installé
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "⚠️  fastmcp non installé, installation en cours..."
    pip install fastmcp
fi

# Démarrer le serveur MCP en arrière-plan
echo "📡 Lancement du serveur MCP sur le port 8000..."
python mcp_server.py &
SERVER_PID=\$!

# Attendre que le serveur démarre
echo "⏳ Attente du démarrage du serveur (7 secondes)..."
sleep 7

# Vérifier que le serveur est lancé (sur /mcp maintenant)
if curl -s http://localhost:8000/mcp > /dev/null 2>&1; then
    echo "✅ Serveur MCP actif"
else
    echo "⚠️  Serveur en cours de démarrage..."
    sleep 3
fi

# Démarrer ngrok en arrière-plan
echo "🌐 Lancement du tunnel ngrok..."
ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=\$!

# Attendre que ngrok démarre
sleep 4

echo ""
echo "================================================================"
echo "✅ SERVEUR MCP DÉMARRÉ"
echo "================================================================"
echo ""
echo "📍 URL locale:        http://localhost:8000/mcp"
echo "🌐 Dashboard ngrok:   http://localhost:4040"
echo ""
echo "🔍 Récupération de l'URL publique ngrok..."
echo ""

# Attendre que ngrok soit prêt
sleep 2

# Récupérer l'URL ngrok (version compatible Windows)
NGROK_URL=""
for i in {1..5}; do
    NGROK_URL=\$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | head -n 1 | cut -d'"' -f4)
    if [ -n "\$NGROK_URL" ]; then
        break
    fi
    sleep 1
done

if [ -n "\$NGROK_URL" ]; then
    echo "🌍 URL publique ngrok: \$NGROK_URL"
    echo ""
    echo "📋 Configuration Dust MCP:"
    echo "   1. Va dans Dust → Settings → MCP Servers"
    echo "   2. Clique sur 'Add MCP Server'"
    echo "   3. URL: \$NGROK_URL"
    echo "   4. Authentication: Automatic"
    echo "   5. Clique sur 'Connect'"
    echo ""
    echo "✅ Ton tool 'search_gots_certification' sera disponible"
    echo ""
else
    echo "⚠️  URL ngrok non récupérée automatiquement"
    echo "📍 Ouvre http://localhost:4040 et copie l'URL 'Forwarding'"
    echo ""
fi

echo "================================================================"
echo ""
echo "🛑 Pour arrêter: Ctrl+C"
echo ""
echo "PIDs: Serveur=\$SERVER_PID, ngrok=\$NGROK_PID"
echo ""

# Fonction de nettoyage
cleanup() {
    echo ""
    echo "🛑 Arrêt des serveurs..."
    kill \$SERVER_PID 2>/dev/null
    kill \$NGROK_PID 2>/dev/null
    pkill -f "python mcp_server.py" 2>/dev/null
    pkill -f "ngrok" 2>/dev/null
    echo "✅ Serveurs arrêtés"
    exit 0
}

# Capturer Ctrl+C
trap cleanup SIGINT SIGTERM

# Attendre (garder le script actif)
wait