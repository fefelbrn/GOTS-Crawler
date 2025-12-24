"""
GOTS Certification Crawler - MCP Server
Utilise fastmcp pour compatibilité native avec Dust
"""

from fastmcp import FastMCP
from gots_crawler import GOTSCrawler
from typing import Optional
import json
import logging
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialiser le serveur MCP avec fastmcp
mcp = FastMCP(
    name="GOTS Certification Crawler",
    version="1.0.0"
)


@mcp.tool()
def search_gots_certification(
    certification_number: str,
    headless: Optional[bool] = True
) -> str:
    """
    Recherche et vérifie une certification GOTS (Global Organic Textile Standard) sur le site officiel.
    
    Retourne les détails complets de la certification incluant :
    - Nom de l'entreprise
    - Pays
    - Domaine d'opération
    - Catégorie de produit
    - Numéro client CB
    - Organisme de certification
    - Date d'expiration du certificat
    - Adresse
    - Détails des produits
    
    Args:
        certification_number: Le numéro de certification GOTS à rechercher (ex: '21205', 'GOTS-21205')
        headless: Si True, le navigateur s'exécute en mode headless (invisible). Par défaut: True
    
    Returns:
        JSON string contenant les détails de la certification ou un message d'erreur si non trouvée
    """
    logger.info(f"🔍 Recherche de la certification: {certification_number}")
    
    crawler = None
    try:
        # Initialiser le crawler Selenium
        crawler = GOTSCrawler(headless=headless)
        
        # Effectuer la recherche
        result = crawler.search_certification(certification_number)
        
        # Logger le résultat
        if result.get('found', False):
            logger.info(f"✅ Certification trouvée: {result.get('company_name', 'N/A')}")
        else:
            logger.info(f"❌ Certification non trouvée: {certification_number}")
        
        # Retourner le résultat en JSON formaté
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la recherche: {e}")
        
        # Retourner une erreur en JSON
        error_result = {
            "found": False,
            "certification_number": certification_number,
            "error": str(e)
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)
        
    finally:
        # Toujours fermer le crawler pour libérer les ressources
        if crawler:
            try:
                crawler.close()
                logger.info("🔒 Crawler fermé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur lors de la fermeture du crawler: {e}")


if __name__ == "__main__":
    # Configuration depuis variables d'environnement
    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    logger.info("=" * 70)
    logger.info("🚀 Démarrage du serveur MCP GOTS Crawler")
    logger.info("=" * 70)
    logger.info(f"📍 Host: {HOST}")
    logger.info(f"📍 Port: {PORT}")
    logger.info(f"🌐 URL locale: http://localhost:{PORT}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("💡 Pour exposer via ngrok: ngrok http 8000")
    logger.info("💡 Dans Dust, utilise l'URL ngrok directement (sans /sse)")
    logger.info("")
    logger.info("🛑 Appuie sur Ctrl+C pour arrêter")
    logger.info("=" * 70)
    
    # Lancer le serveur avec transport HTTP
    mcp.run(transport="http", host=HOST, port=PORT)