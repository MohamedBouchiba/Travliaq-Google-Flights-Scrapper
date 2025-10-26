from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.config import settings, PROJECT_NAME, API_VERSION, API_PREFIX
from ..core.scraper_pool import scraper_pool
from ..database.manager import db_manager
from ..models.schemas import (
    CalendarPricesResponse,
    HealthResponse,
    ErrorResponse,
    CacheStatsResponse
)
from ..utils.logger import get_logger
from .middleware.rate_limiter import rate_limit_middleware

# Après la création de l'app

logger = get_logger(__name__)


# Imports conditionnels pour Sentry
SENTRY_AVAILABLE = False
sentry_sdk = None

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    pass


# Initialiser Sentry si DSN est défini ET si sentry est disponible
if SENTRY_AVAILABLE and settings.sentry_dsn and settings.sentry_dsn.strip():
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=0.0,
        send_default_pii=False,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        before_send=lambda event, hint: event if settings.environment == "production" else None,
        ignore_errors=[
            KeyboardInterrupt,
            "TimeoutError",
        ],
    )
    logger.info("✓ Sentry initialisé")
else:
    logger.info("ℹ️  Sentry désactivé (pas de DSN ou module non installé)")


# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie"""
    logger.warning(f"🚀 Démarrage {PROJECT_NAME}")
    logger.info(f"   Version: {API_VERSION}")
    logger.info(f"   Environment: {settings.environment}")

    # Nettoyage au démarrage
    if settings.environment == "production":
        db_manager.clear_old_cache(days=7)

    yield

    # Arrêt propre
    logger.warning(f"🛑 Arrêt {PROJECT_NAME}")
    scraper_pool.shutdown()


# Créer l'app
app = FastAPI(
    title=PROJECT_NAME,
    description="API pour scraper les prix des vols Google Flights",
    version=API_VERSION,
    lifespan=lifespan,
    docs_url=f"{API_PREFIX}/docs" if settings.environment != "production" else None,
    redoc_url=None,
    openapi_url=f"{API_PREFIX}/openapi.json" if settings.environment != "production" else None,
)

app.middleware("http")(rate_limit_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handler général avec logging détaillé"""
    import traceback

    # Logger l'erreur complète
    logger.error(f"Exception non gérée: {exc}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")

    # Envoyer à Sentry si disponible
    if SENTRY_AVAILABLE and settings.sentry_dsn and sentry_sdk:
        sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.debug else "Une erreur est survenue"
        ).model_dump()
    )


# ==================== HEALTH CHECK ====================

@app.get(
    f"{API_PREFIX}/health",
    response_model=HealthResponse,
    tags=["System"]
)
async def health_check():
    """Vérifie l'état de santé de l'API"""
    try:
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
)
async def get_calendar_prices(
    origin: str = Query(..., description="Code IATA aéroport de départ"),
    destination: str = Query(..., description="Code IATA aéroport d'arrivée"),
    start_date: str = Query(..., description="Date début (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Date fin (YYYY-MM-DD)"),
    force_refresh: bool = Query(False, description="Forcer le re-scraping"),
):
    """Endpoint asynchrone pour scraping parallèle"""

    start_time = time.time()

    logger.info(f"📥 Requête: {origin}->{destination}, {start_date} -> {end_date}")

    # Normaliser
    origin = origin.upper()
    destination = destination.upper()

    # Vérifier cache
    if not force_refresh:
        cached_prices = db_manager.get_cached_calendar_prices(
            origin, destination, start_date, end_date
        )

        if cached_prices:
            duration = time.time() - start_time
            logger.info(f"✓ Cache hit ({duration:.2f}s)")

            return CalendarPricesResponse.from_prices_dict(
                origin=origin,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                prices=cached_prices,
                from_cache=True
            )

    # Scraping
    logger.info(f"🕷️  Soumission job scraping...")

    try:
        job_id = scraper_pool.submit_scrape(origin, destination, start_date, end_date)

        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor()

        # Attendre avec timeout de 5 minutes
        prices = await loop.run_in_executor(
            executor,
            scraper_pool.wait_for_job,
            job_id,
            300  # 5 minutes
        )

        if not prices:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun prix trouvé"
            )

        # Sauvegarder
        db_manager.save_calendar_prices(origin, destination, prices)

        # Logger
        duration = time.time() - start_time
        db_manager.log_scrape(
            scrape_type="calendar",
            origin=origin,
            destination=destination,
            success=True,
            results_count=len(prices),
            started_at=datetime.fromtimestamp(start_time),
            duration_seconds=duration,
            params={"start_date": start_date, "end_date": end_date}
        )

        logger.info(f"✓ Scraping terminé ({duration:.1f}s)")

        return CalendarPricesResponse.from_prices_dict(
            origin=origin,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            prices=prices,
            from_cache=False
        )

    except TimeoutError:
        logger.error(f"⏰ Timeout pour {origin}->{destination}")
        raise HTTPException(
            status_code=504,
            detail="Scraping timeout - le serveur a mis trop de temps"
        )
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        db_manager.log_scrape(
            scrape_type="calendar",
            origin=origin,
            destination=destination,
            success=False,
            error_message=str(e),
            started_at=datetime.fromtimestamp(start_time),
            duration_seconds=time.time() - start_time
        )

        # Envoyer à Sentry si configuré
        if SENTRY_AVAILABLE and settings.sentry_dsn and sentry_sdk:
            sentry_sdk.capture_exception(e)

        raise HTTPException(status_code=500, detail=str(e))


# ==================== CACHE MANAGEMENT ====================

@app.get(
    f"{API_PREFIX}/cache/stats",
    response_model=CacheStatsResponse,
    tags=["Cache"]
)
async def get_cache_stats():
    """Récupère les statistiques du cache"""
    stats = db_manager.get_cache_stats()

    from ..models.schemas import CacheInfo

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
    """Nettoie le cache"""
    try:
        db_manager.clear_old_cache(days=days)
        return {"message": f"Cache nettoyé (> {days} jours)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ROOT ====================

@app.get("/", tags=["System"])
async def root():
    """Endpoint racine"""
    return {
        "name": PROJECT_NAME,
        "version": API_VERSION,
        "status": "running",
        "docs": f"{API_PREFIX}/docs" if settings.environment != "production" else None,
        "health": f"{API_PREFIX}/health"
    }