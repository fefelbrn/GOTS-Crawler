"""
MCP Server pour le GOTS Crawler
Expose le crawler via HTTP pour Dust
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import logging
from gots_crawler import GOTSCrawler
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GOTS Certification MCP Server",
    description="Serveur MCP pour vérifier les certifications GOTS",
    version="1.0.0"
)

# CORS pour permettre les requêtes depuis Dust
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modèles Pydantic
class CertificationRequest(BaseModel):
    certification_number: str
    headless: Optional[bool] = True

class CertificationResponse(BaseModel):
    found: bool
    certification_number: str
    company_name: Optional[str] = None
    country: Optional[str] = None
    field_of_operation: Optional[str] = None
    product_category: Optional[str] = None
    cb_client_number: Optional[str] = None
    certification_body: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    address: Optional[str] = None
    product_details: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    message: str


# Endpoints

@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint racine"""
    return {
        "service": "GOTS Certification MCP Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "search": "/search_certification",
            "mcp_tools": "/mcp/tools"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="GOTS Crawler MCP Server is running"
    )


@app.post("/search_certification", response_model=CertificationResponse)
async def search_certification(request: CertificationRequest):
    """
    Recherche une certification GOTS
    
    Args:
        request: Objet contenant le numéro de certification
        
    Returns:
        Résultats de la recherche
    """
    logger.info(f"🔍 Requête reçue pour certification: {request.certification_number}")
    
    crawler = None
    try:
        # Initialiser le crawler
        crawler = GOTSCrawler(headless=request.headless)
        
        # Effectuer la recherche
        result = crawler.search_certification(request.certification_number)
        
        logger.info(f"✅ Recherche terminée - Found: {result.get('found', False)}")
        
        return CertificationResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la recherche: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la recherche: {str(e)}"
        )
    finally:
        if crawler:
            crawler.close()


@app.get("/mcp/tools")
async def get_mcp_tools():
    """
    Retourne la liste des tools disponibles au format MCP
    Compatible avec Dust MCP
    """
    return {
        "tools": [
            {
                "name": "search_gots_certification",
                "description": "Recherche et vérifie une certification GOTS (Global Organic Textile Standard) sur le site officiel. Retourne les détails de la certification si trouvée.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "certification_number": {
                            "type": "string",
                            "description": "Le numéro de certification GOTS à rechercher (ex: '21205', 'GOTS-21205')"
                        },
                        "headless": {
                            "type": "boolean",
                            "description": "Si true, le navigateur s'exécute en mode headless (sans interface graphique). Par défaut: true",
                            "default": True
                        }
                    },
                    "required": ["certification_number"]
                }
            }
        ]
    }


@app.post("/mcp/tools/search_gots_certification")
async def mcp_search_gots_certification(request: Dict[str, Any]):
    """
    Endpoint MCP pour rechercher une certification GOTS
    Format compatible avec Dust MCP
    """
    logger.info(f"🔍 MCP Tool appelé avec: {request}")
    
    try:
        # Extraire les paramètres
        cert_number = request.get("certification_number")
        headless = request.get("headless", True)
        
        if not cert_number:
            raise HTTPException(
                status_code=400,
                detail="Le paramètre 'certification_number' est requis"
            )
        
        # Créer une requête standard
        cert_request = CertificationRequest(
            certification_number=cert_number,
            headless=headless
        )
        
        # Appeler la fonction de recherche
        result = await search_certification(cert_request)
        
        # Retourner au format MCP
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result.dict(), indent=2, ensure_ascii=False)
                }
            ]
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Erreur MCP: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur MCP: {str(e)}"
        )


if __name__ == "__main__":
    logger.info("🚀 Démarrage du serveur MCP GOTS Crawler...")
    logger.info("📍 Serveur disponible sur: http://localhost:8000")
    logger.info("📖 Documentation API: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )