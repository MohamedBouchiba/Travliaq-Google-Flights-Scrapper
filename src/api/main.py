"""
API FastAPI pour Travliaq Google Flights Scraper
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import time

from ..models.schemas import (
    CalendarPricesRequest,
    CalendarPricesResponse,
    FlightsRequest,
    FlightsResponse,
    HealthResponse,
    ErrorResponse,
    CacheStatsResponse
)
from ..scrapers.calendar_scraper import CalendarScraper
from ..database.manager import db_manager
from ..core.config import settings, PROJECT_NAME, API_VERSION, API_PREFIX
from ..core.exceptions import ScraperException
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    logger.info(f"🚀 Démarrage {PROJECT_NAME}")
    logger.info(f"   Version API: {API_VERSION}")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Database: {settings.database_url}")
    
    # Nettoyage du cache au démarrage si nécessaire
    if settings.environment == "production":
        db_manager.clear_old_cache(days=7)
    
    yield
    
    logger.info(f"🛑 Arrêt {PROJECT_NAME}")


# Créer l'application
app = FastAPI(
    title=PROJECT_NAME,
    description="API pour scraper les prix des vols Google Flights",
    version=API_VERSION,
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod: spécifier les origines autorisées
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(ScraperException)
async def scraper_exception_handler(request, exc: ScraperException):
    """Handler pour les exceptions du scraper"""
    logger.error(f"ScraperException: {exc.message}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=exc.message,
            detail=str(exc.details) if exc.details else None
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handler général pour toutes les exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.debug else None
        ).dict()
    )


# ==================== HEALTH CHECK ====================

@app.get(
    f"{API_PREFIX}/health",
    response_model=HealthResponse,
    tags=["System"]
)
async def health_check():
    """
    Vérifie l'état de santé de l'API
    """
    try:
        # Tester la connexion DB
        with db_manager.get_session() as session:
            session.execute("SELECT 1")
        
        return HealthResponse(
            status="healthy",
            version=API_VERSION,
            database="ok"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version=API_VERSION,
            database="error"
        )


# ==================== CALENDAR PRICES ====================

@app.get(
    f"{API_PREFIX}/calendar-prices",
    response_model=CalendarPricesResponse,
    tags=["Scraping"],
    summary="Récupère les prix du calendrier",
    description="Récupère tous les prix minimum par jour sur plusieurs mois. Utilise le cache si disponible."
)
async def get_calendar_prices(
    origin: str = Query(..., description="Code IATA aéroport de départ", example="BRU"),
    destination: str = Query(..., description="Code IATA aéroport d'arrivée", example="CDG"),
    months: int = Query(3, ge=1, le=12, description="Nombre de mois à scraper"),
    force_refresh: bool = Query(False, description="Forcer le re-scraping même si cache valide"),
    background_tasks: BackgroundTasks = None
):
    """
    Endpoint principal pour récupérer les prix du calendrier
    
    **Logique:**
    1. Vérifie le cache (si force_refresh=false)
    2. Si cache valide → retourne immédiatement
    3. Sinon → lance le scraping
    4. Sauvegarde en cache
    5. Retourne les résultats
    """
    start_time = time.time()
    
    logger.info(f"📥 Requête calendar-prices: {origin}-{destination}, {months} mois")
    
    # Normaliser les codes aéroports
    origin = origin.upper()
    destination = destination.upper()
    
    # Vérifier le cache si pas de force_refresh
    if not force_refresh:
        cached_prices = db_manager.get_cached_calendar_prices(origin, destination)
        if cached_prices:
            duration = time.time() - start_time
            logger.info(f"✓ Cache hit ({duration:.2f}s)")
            
            return CalendarPricesResponse.from_prices_dict(
                origin=origin,
                destination=destination,
                prices=cached_prices,
                from_cache=True
            )
    
    # Pas de cache ou force_refresh → scraper
    logger.info(f"🕷️  Lancement scraping...")
    
    try:
        scraper = CalendarScraper(headless=settings.headless)
        prices = scraper.scrape(origin, destination, months_ahead=months)
        
        if not prices:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun prix trouvé pour {origin}-{destination}"
            )
        
        # Sauvegarder en cache
        db_manager.save_calendar_prices(origin, destination, prices)
        
        # Logger le scraping
        duration = time.time() - start_time
        db_manager.log_scrape(
            scrape_type="calendar",
            origin=origin,
            destination=destination,
            success=True,
            results_count=len(prices),
            started_at=datetime.fromtimestamp(start_time),
            duration_seconds=duration,
            params={"months": months}
        )
        
        logger.info(f"✓ Scraping terminé ({duration:.2f}s)")
        
        return CalendarPricesResponse.from_prices_dict(
            origin=origin,
            destination=destination,
            prices=prices,
            from_cache=False
        )
        
    except ScraperException as e:
        # Logger l'échec
        db_manager.log_scrape(
            scrape_type="calendar",
            origin=origin,
            destination=destination,
            success=False,
            error_message=str(e),
            started_at=datetime.fromtimestamp(start_time),
            duration_seconds=time.time() - start_time
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CACHE MANAGEMENT ====================

@app.get(
    f"{API_PREFIX}/cache/stats",
    response_model=CacheStatsResponse,
    tags=["Cache"]
)
async def get_cache_stats():
    """
    Récupère les statistiques du cache
    """
    stats = db_manager.get_cache_stats()
    
    from src.models.schemas import CacheInfo
    
    cache_info = CacheInfo(
        total_entries=stats.get('total_entries', 0),
        oldest_entry=stats.get('oldest_entry'),
        newest_entry=stats.get('newest_entry'),
        total_routes=stats.get('total_routes', 0)
    )
    
    return CacheStatsResponse(
        cache_info=cache_info,
        recent_scrapes=stats.get('recent_scrapes', [])
    )


@app.delete(
    f"{API_PREFIX}/cache/clear",
    tags=["Cache"]
)
async def clear_cache(
    days: int = Query(7, ge=1, description="Supprimer les entrées plus vieilles que N jours")
):
    """
    Nettoie le cache
    """
    try:
        db_manager.clear_old_cache(days=days)
        return {"message": f"Cache nettoyé (> {days} jours)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROOT ====================

@app.get("/", tags=["System"])
async def root():
    """
    Endpoint racine
    """
    return {
        "name": PROJECT_NAME,
        "version": API_VERSION,
        "status": "running",
        "docs": f"{API_PREFIX}/docs",
        "health": f"{API_PREFIX}/health"
    }