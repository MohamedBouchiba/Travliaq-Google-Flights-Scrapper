"""
Exceptions personnalisées pour le scraper Google Flights
"""


class ScraperException(Exception):
    """Exception de base pour tous les scrapers"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DriverInitializationError(ScraperException):
    """Erreur lors de l'initialisation du WebDriver"""
    pass


class PageLoadError(ScraperException):
    """Erreur lors du chargement d'une page"""
    pass


class ElementNotFoundError(ScraperException):
    """Élément non trouvé sur la page"""
    pass


class CalendarNotFoundError(ScraperException):
    """Calendrier des prix non trouvé"""
    pass


class PriceExtractionError(ScraperException):
    """Erreur lors de l'extraction des prix"""
    pass


class ValidationError(ScraperException):
    """Erreur de validation des données"""
    pass


class RateLimitError(ScraperException):
    """Limite de requêtes atteinte"""
    pass


class CacheError(ScraperException):
    """Erreur liée au cache"""
    pass


class DatabaseError(ScraperException):
    """Erreur liée à la base de données"""
    pass


class InvalidAirportCodeError(ValidationError):
    """Code aéroport invalide"""
    def __init__(self, code: str):
        super().__init__(
            f"Code aéroport invalide: {code}",
            details={"code": code}
        )


class InvalidDateError(ValidationError):
    """Date invalide"""
    def __init__(self, date: str, reason: str = ""):
        super().__init__(
            f"Date invalide: {date}. {reason}",
            details={"date": date, "reason": reason}
        )


class ScrapingTimeoutError(ScraperException):
    """Timeout lors du scraping"""
    pass