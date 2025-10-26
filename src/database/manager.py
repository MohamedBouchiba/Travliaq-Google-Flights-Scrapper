"""
Gestionnaire de base de données avec système de cache intelligent
"""

from sqlalchemy import create_engine, and_, desc, func
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import json

from ..database.models import Base, CalendarPrice, Flight, ScrapeLog
from ..core.config import settings
from ..core.exceptions import DatabaseError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Gestionnaire centralisé de la base de données"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialise le gestionnaire
        
        Args:
            database_url: URL de connexion (None = utiliser config)
        """
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.SessionLocal = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialise la connexion et crée les tables"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Créer les tables
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"✓ Database initialisée: {self.database_url}")
            
        except Exception as e:
            logger.error(f"✗ Erreur initialisation database: {e}")
            raise DatabaseError(f"Impossible d'initialiser la database: {e}")
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager pour obtenir une session
        
        Usage:
            with db_manager.get_session() as session:
                session.query(...)
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur session database: {e}")
            raise
        finally:
            session.close()
    
    # ==================== CALENDAR PRICES ====================
    
    def get_cached_calendar_prices(
        self, 
        origin: str, 
        destination: str,
        max_age_minutes: Optional[int] = None
    ) -> Optional[Dict[str, float]]:
        """
        Récupère les prix du calendrier depuis le cache
        
        Args:
            origin: Code aéroport départ
            destination: Code aéroport arrivée
            max_age_minutes: Age maximum du cache (None = utiliser config)
            
        Returns:
            Dict {date: prix} ou None si pas de cache valide
        """
        max_age = max_age_minutes or settings.cache_ttl_minutes
        cutoff_time = datetime.now() - timedelta(minutes=max_age)
        
        try:
            with self.get_session() as session:
                prices = session.query(CalendarPrice).filter(
                    and_(
                        CalendarPrice.origin == origin,
                        CalendarPrice.destination == destination,
                        CalendarPrice.scraped_at >= cutoff_time
                    )
                ).all()
                
                if not prices:
                    logger.debug(f"Pas de cache valide pour {origin}-{destination}")
                    return None
                
                result = {p.date: p.price for p in prices}
                logger.info(f"✓ Cache hit: {len(result)} prix pour {origin}-{destination}")
                return result
                
        except Exception as e:
            logger.error(f"Erreur lecture cache: {e}")
            return None
    
    def save_calendar_prices(
        self, 
        origin: str, 
        destination: str, 
        prices: Dict[str, float]
    ) -> bool:
        """
        Sauvegarde les prix du calendrier
        
        Args:
            origin: Code aéroport départ
            destination: Code aéroport arrivée
            prices: Dict {date: prix}
            
        Returns:
            True si succès
        """
        try:
            with self.get_session() as session:
                # Supprimer les anciens prix pour cette route
                session.query(CalendarPrice).filter(
                    and_(
                        CalendarPrice.origin == origin,
                        CalendarPrice.destination == destination
                    )
                ).delete()
                
                # Insérer les nouveaux prix
                for date, price in prices.items():
                    calendar_price = CalendarPrice(
                        origin=origin,
                        destination=destination,
                        date=date,
                        price=price,
                        scraped_at=datetime.now()
                    )
                    session.add(calendar_price)
                
                session.commit()
                logger.info(f"✓ {len(prices)} prix sauvegardés pour {origin}-{destination}")
                return True
                
        except Exception as e:
            logger.error(f"Erreur sauvegarde prix: {e}")
            return False
    
    # ==================== FLIGHTS ====================
    
    def get_cached_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        max_age_minutes: Optional[int] = None
    ) -> Optional[List[Dict]]:
        """Récupère les vols depuis le cache"""
        max_age = max_age_minutes or settings.cache_ttl_minutes
        cutoff_time = datetime.now() - timedelta(minutes=max_age)
        
        try:
            with self.get_session() as session:
                query = session.query(Flight).filter(
                    and_(
                        Flight.origin == origin,
                        Flight.destination == destination,
                        Flight.departure_date == departure_date,
                        Flight.scraped_at >= cutoff_time
                    )
                )
                
                if return_date:
                    query = query.filter(Flight.return_date == return_date)
                
                flights = query.all()
                
                if not flights:
                    return None
                
                result = [f.to_dict() for f in flights]
                logger.info(f"✓ Cache hit: {len(result)} vols")
                return result
                
        except Exception as e:
            logger.error(f"Erreur lecture cache vols: {e}")
            return None
    
    def save_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        flights_data: List[Dict],
        return_date: Optional[str] = None
    ) -> bool:
        """Sauvegarde les vols"""
        try:
            with self.get_session() as session:
                # Supprimer anciens vols
                query = session.query(Flight).filter(
                    and_(
                        Flight.origin == origin,
                        Flight.destination == destination,
                        Flight.departure_date == departure_date
                    )
                )
                
                if return_date:
                    query = query.filter(Flight.return_date == return_date)
                
                query.delete()
                
                # Insérer nouveaux vols
                for flight_data in flights_data:
                    flight = Flight(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date,
                        return_date=return_date,
                        airline=flight_data.get('airline'),
                        departure_time=flight_data.get('departure_time'),
                        arrival_time=flight_data.get('arrival_time'),
                        duration=flight_data.get('duration'),
                        stops=flight_data.get('stops'),
                        price=flight_data.get('price'),
                        flight_index=flight_data.get('index'),
                        raw_text=flight_data.get('raw_text'),
                        raw_data=flight_data,
                        scraped_at=datetime.now()
                    )
                    session.add(flight)
                
                session.commit()
                logger.info(f"✓ {len(flights_data)} vols sauvegardés")
                return True
                
        except Exception as e:
            logger.error(f"Erreur sauvegarde vols: {e}")
            return False
    
    # ==================== LOGS ====================
    
    def log_scrape(
        self,
        scrape_type: str,
        origin: str,
        destination: str,
        success: bool,
        results_count: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        params: Optional[Dict] = None
    ):
        """Enregistre un log de scraping"""
        try:
            with self.get_session() as session:
                log = ScrapeLog(
                    scrape_type=scrape_type,
                    origin=origin,
                    destination=destination,
                    success=success,
                    results_count=results_count,
                    error_message=error_message,
                    started_at=started_at or datetime.now(),
                    completed_at=datetime.now(),
                    duration_seconds=duration_seconds,
                    params=params
                )
                session.add(log)
                session.commit()
                
        except Exception as e:
            logger.error(f"Erreur log scrape: {e}")
    
    # ==================== STATS ====================
    
    def get_cache_stats(self) -> Dict:
        """Récupère les statistiques du cache"""
        try:
            with self.get_session() as session:
                # Stats calendar prices
                total_prices = session.query(func.count(CalendarPrice.id)).scalar()
                oldest_price = session.query(func.min(CalendarPrice.scraped_at)).scalar()
                newest_price = session.query(func.max(CalendarPrice.scraped_at)).scalar()
                
                # Routes uniques
                unique_routes = session.query(
                    func.count(func.distinct(CalendarPrice.origin + CalendarPrice.destination))
                ).scalar()
                
                # Logs récents
                recent_logs = session.query(ScrapeLog).order_by(
                    desc(ScrapeLog.started_at)
                ).limit(10).all()
                
                return {
                    'total_entries': total_prices,
                    'oldest_entry': oldest_price,
                    'newest_entry': newest_price,
                    'total_routes': unique_routes,
                    'recent_scrapes': [
                        {
                            'type': log.scrape_type,
                            'route': f"{log.origin}-{log.destination}",
                            'success': log.success,
                            'started_at': log.started_at.isoformat()
                        }
                        for log in recent_logs
                    ]
                }
        except Exception as e:
            logger.error(f"Erreur stats cache: {e}")
            return {}
    
    def clear_old_cache(self, days: int = 7):
        """Supprime les données de cache anciennes"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            
            with self.get_session() as session:
                deleted_prices = session.query(CalendarPrice).filter(
                    CalendarPrice.scraped_at < cutoff
                ).delete()
                
                deleted_flights = session.query(Flight).filter(
                    Flight.scraped_at < cutoff
                ).delete()
                
                session.commit()
                
                logger.info(f"✓ Cache nettoyé: {deleted_prices} prix, {deleted_flights} vols supprimés")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage cache: {e}")


# Instance globale
db_manager = DatabaseManager()