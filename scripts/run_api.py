"""
Script pour lancer l'API FastAPI
Usage: python scripts/run_api.py
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import uvicorn
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Lance le serveur API"""
    
    logger.info("="*60)
    logger.info("🚀 Démarrage de l'API Travliaq Google Flights Scraper")
    logger.info("="*60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Host: {settings.api_host}")
    logger.info(f"Port: {settings.api_port}")
    logger.info(f"Headless mode: {settings.headless}")
    logger.info(f"Debug: {settings.debug}")
    logger.info("="*60)
    logger.info("")
    logger.info(f"📖 Documentation: http://{settings.api_host}:{settings.api_port}/api/v1/docs")
    logger.info(f"❤️  Health check: http://{settings.api_host}:{settings.api_port}/api/v1/health")
    logger.info("")
    logger.info("Appuyez sur CTRL+C pour arrêter")
    logger.info("="*60)
    
    try:
        uvicorn.run(
            "src.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur lors du démarrage: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()