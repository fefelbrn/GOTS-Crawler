# 🌿 GOTS Certification Crawler

Service de vérification automatique des certifications GOTS (Global Organic Textile Standard) via Selenium et serveur MCP pour Dust.

## 🎯 Fonctionnalités

- **Recherche automatique** de certifications sur la base de données officielle GOTS
- **Extraction complète** des données : entreprise, pays, domaine d'opération, produits, dates d'expiration
- **Intégration Dust** via serveur MCP (FastMCP)
- **Mode headless** pour exécution en background
- **Optimisé** pour des réponses < 30 secondes

## 📦 Installation

```bash
# Installer les dépendances
pip install -r requirements.txt
```

**Dépendances principales :**
- `selenium` : Automatisation du navigateur
- `webdriver-manager` : Gestion automatique de ChromeDriver
- `fastmcp` : Serveur MCP pour Dust

## 🚀 Utilisation

### Mode MCP Server (pour Dust)

```bash
# Démarrer le serveur
./start_mcp_server.sh

# Ou directement
python mcp_server.py
```

Le serveur démarre sur `http://0.0.0.0:8000` et expose la fonction :
- `search_gots_certification(certification_number, headless=True)`

**Pour exposer publiquement :**
```bash
ngrok http 8000
# Puis utiliser l'URL ngrok dans Dust
```

### Mode standalone (Python)

```python
from gots_crawler import GOTSCrawler
import json

crawler = GOTSCrawler(headless=True)

try:
    result = crawler.search_certification("21205")
    print(json.dumps(result, indent=2, ensure_ascii=False))
finally:
    crawler.close()
```

## 📊 Structure des données retournées

```json
{
  "found": true,
  "company_name": "Example Company",
  "certification_number": "21205",
  "country": "Netherlands",
  "field_of_operation": "Manufacturing",
  "product_category": "Textiles",
  "cb_client_number": "12345",
  "certification_body": "Control Union",
  "certificate_expiry_date": "2025-12-31",
  "address": "Street 123",
  "state": "North Holland",
  "postcode": "1033 MZ",
  "city": "Amsterdam",
  "product_details": "Cotton (PC0001); Knitted fabric (PD0002)..."
}
```

## 🏗️ Architecture

```
Crawler/
├── gots_crawler.py         # Classe principale Selenium
├── mcp_server.py          # Serveur MCP pour Dust
├── start_mcp_server.sh    # Script de démarrage
├── requirements.txt       # Dépendances Python
├── .gitignore            # Fichiers exclus
└── README.md             # Documentation
```

## ⚙️ Configuration

Variables d'environnement disponibles :

```bash
export PORT=8000           # Port du serveur MCP
export HOST=0.0.0.0       # Host du serveur
```

## 🛠️ Optimisations techniques

- **Chargement eager** : Ne pas attendre le chargement complet des pages
- **Images désactivées** : Réduction du temps de chargement
- **Timeouts réduits** : 8s max pour les éléments critiques
- **JavaScript injection** : Pour les clics et la suppression des popups cookies
- **Multi-stratégie** : Plusieurs méthodes de fallback pour l'extraction de données

## 🔍 Gestion des cas limites

- **Plusieurs résultats** : Sélection du premier résultat par défaut si aucun match exact
- **Popups cookies** : Masquage automatique via JavaScript
- **Données manquantes** : Champs vides si non trouvés
- **Timeouts** : Gestion des erreurs avec messages explicites

## 💡 Tips

- Utiliser `headless=False` pour déboguer visuellement
- Le crawler log toutes les étapes importantes
- Les logs externes (Selenium, WDM) sont réduits au niveau WARNING