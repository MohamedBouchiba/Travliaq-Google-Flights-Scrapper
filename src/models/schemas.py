"""
Modèles Pydantic pour validation et sérialisation des données API
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List
from datetime import date, datetime
from src.utils.validators import Validators


class CalendarPricesRequest(BaseModel):
    """Requête pour obtenir les prix du calendrier"""
    origin: str = Field(..., description="Code IATA aéroport de départ", example="BRU")
    destination: str = Field(..., description="Code IATA aéroport d'arrivée", example="CDG")
    months: int = Field(default=3, ge=1, le=12, description="Nombre de mois à scraper")
    force_refresh: bool = Field(default=False, description="Forcer le re-scraping même si cache valide")
    
    @validator('origin', 'destination')
    def validate_airport_codes(cls, v):
        return Validators.validate_airport_code(v)
    
    @validator('destination')
    def validate_different_airports(cls, v, values):
        if 'origin' in values and v == values['origin']:
            raise ValueError("Origine et destination doivent être différentes")
        return v


class FlightsRequest(BaseModel):
    """Requête pour obtenir la liste des vols"""
    origin: str = Field(..., description="Code IATA aéroport de départ", example="BRU")
    destination: str = Field(..., description="Code IATA aéroport d'arrivée", example="CDG")
    departure_date: str = Field(..., description="Date de départ (YYYY-MM-DD)", example="2025-12-15")
    return_date: Optional[str] = Field(None, description="Date de retour (YYYY-MM-DD)", example="2025-12-20")
    passengers: int = Field(default=1, ge=1, le=9, description="Nombre de passagers")
    force_refresh: bool = Field(default=False, description="Forcer le re-scraping")
    
    @validator('origin', 'destination')
    def validate_airport_codes(cls, v):
        return Validators.validate_airport_code(v)
    
    @validator('departure_date', 'return_date')
    def validate_dates(cls, v):
        if v:
            Validators.validate_date(v)
        return v


class PricePoint(BaseModel):
    """Un point de prix pour une date donnée"""
    date: str = Field(..., description="Date au format ISO")
    price: float = Field(..., description="Prix minimum en EUR")


class CalendarPricesResponse(BaseModel):
    """Réponse avec les prix du calendrier"""
    origin: str
    destination: str
    prices: Dict[str, float] = Field(..., description="Dict {date: prix}")
    total_dates: int = Field(..., description="Nombre de dates avec prix")
    min_price: Optional[float] = Field(None, description="Prix minimum trouvé")
    max_price: Optional[float] = Field(None, description="Prix maximum trouvé")
    avg_price: Optional[float] = Field(None, description="Prix moyen")
    best_dates: List[PricePoint] = Field(default=[], description="Top 5 meilleures dates")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Timestamp du scraping")
    from_cache: bool = Field(default=False, description="Données issues du cache")
    
    @classmethod
    def from_prices_dict(cls, 
                        origin: str, 
                        destination: str, 
                        prices: Dict[str, float],
                        from_cache: bool = False):
        """Factory pour créer une réponse depuis un dict de prix"""
        if not prices:
            return cls(
                origin=origin,
                destination=destination,
                prices={},
                total_dates=0,
                from_cache=from_cache
            )
        
        price_values = list(prices.values())
        sorted_prices = sorted(prices.items(), key=lambda x: x[1])
        
        return cls(
            origin=origin,
            destination=destination,
            prices=prices,
            total_dates=len(prices),
            min_price=min(price_values),
            max_price=max(price_values),
            avg_price=sum(price_values) / len(price_values),
            best_dates=[
                PricePoint(date=date, price=price) 
                for date, price in sorted_prices[:5]
            ],
            from_cache=from_cache
        )


class FlightDetails(BaseModel):
    """Détails d'un vol"""
    index: int
    airline: Optional[str] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    duration: Optional[str] = None
    stops: Optional[int] = None
    price: Optional[float] = None
    raw_text: Optional[str] = None


class FlightsResponse(BaseModel):
    """Réponse avec la liste des vols"""
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    passengers: int
    flights: List[FlightDetails]
    total_flights: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    scraped_at: datetime = Field(default_factory=datetime.now)
    from_cache: bool = Field(default=False)


class HealthResponse(BaseModel):
    """Réponse pour le healthcheck"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    database: str = "ok"


class ErrorResponse(BaseModel):
    """Réponse d'erreur standardisée"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class CacheInfo(BaseModel):
    """Informations sur le cache"""
    total_entries: int
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None
    total_routes: int


class CacheStatsResponse(BaseModel):
    """Statistiques du cache"""
    cache_info: CacheInfo
    recent_scrapes: List[Dict] = Field(default=[])
    popular_routes: List[Dict] = Field(default=[])