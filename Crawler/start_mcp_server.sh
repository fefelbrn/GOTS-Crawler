#!/bin/bash

echo "🚀 Démarrage du serveur MCP GOTS Crawler..."

# Démarrer le serveur FastAPI en arrière-plan
echo "📡 Lancement du serveur FastAPI sur le port 8000..."
python mcp_server.py &
SERVER_PID=\$!

# Attendre que le serveur démarre
sleep 3

# Démarrer ngrok
echo "🌐 Lancement du tunnel ngrok..."
ngrok http 8000 --log=stdout > ngrok.log &
NGROK_PID=\$!

# Attendre que ngrok démarre
sleep 2

# Récupérer l'URL publique ngrok
echo ""
echo "✅ Serveur MCP démarré !"
echo ""
echo "📍 URL locale: http://localhost:8000"
echo "📍 Documentation: http://localhost:8000/docs"
echo ""
echo "🌍 Récupération de l'URL publique ngrok..."

# Récupérer l'URL via l'API ngrok
NGROK_URL=\$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.app')

if [ -n "\$NGROK_URL" ]; then
    echo "🌐 URL publique ngrok: \$NGROK_URL"
    echo ""
    echo "📋 Utilise cette URL dans Dust MCP:"
    echo "   \$NGROK_URL/mcp/tools"
    echo ""
else
    echo "⚠️  Impossible de récupérer l'URL ngrok automatiquement"
    echo "📍 Consulte: http://localhost:4040 pour voir l'URL"
fi

echo ""
echo "🛑 Pour arrêter les serveurs: Ctrl+C puis exécute 'kill \$SERVER_PID \$NGROK_PID'"
echo ""

# Attendre que l'utilisateur arrête
wait