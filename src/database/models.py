"""
Modèles SQLAlchemy pour la base de données
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class CalendarPrice(Base):
    """Table des prix du calendrier"""
    __tablename__ = 'calendar_prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # Format YYYY-MM-DD
    price = Column(Float, nullable=False)
    currency = Column(String(3), default='EUR')
    
    scraped_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Métadonnées
    scraper_version = Column(String(20), default='1.0.0')
    raw_data = Column(JSON, nullable=True)
    
    # Index composé pour les recherches rapides
    __table_args__ = (
        UniqueConstraint('origin', 'destination', 'date', name='uix_route_date'),
        Index('idx_route', 'origin', 'destination'),
        Index('idx_scraped_at', 'scraped_at'),
    )
    
    def __repr__(self):
        return f"<CalendarPrice(route={self.origin}-{self.destination}, date={self.date}, price={self.price}€)>"
    
    def to_dict(self):
        """Convertit en dictionnaire"""
        return {
            'id': self.id,
            'origin': self.origin,
            'destination': self.destination,
            'date': self.date,
            'price': self.price,
            'currency': self.currency,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
        }


class Flight(Base):
    """Table des vols détaillés"""
    __tablename__ = 'flights'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    departure_date = Column(String(10), nullable=False, index=True)
    return_date = Column(String(10), nullable=True)
    
    # Détails du vol
    airline = Column(String(100), nullable=True)
    departure_time = Column(String(10), nullable=True)
    arrival_time = Column(String(10), nullable=True)
    duration = Column(String(20), nullable=True)
    stops = Column(Integer, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(3), default='EUR')
    
    # Métadonnées
    flight_index = Column(Integer, nullable=True)  # Position dans les résultats
    raw_text = Column(String(1000), nullable=True)
    raw_data = Column(JSON, nullable=True)
    
    scraped_at = Column(DateTime, default=datetime.now, nullable=False)
    
    __table_args__ = (
        Index('idx_flight_route', 'origin', 'destination', 'departure_date'),
        Index('idx_scraped_at', 'scraped_at'),
    )
    
    def __repr__(self):
        return f"<Flight(route={self.origin}-{self.destination}, date={self.departure_date}, price={self.price}€)>"
    
    def to_dict(self):
        """Convertit en dictionnaire"""
        return {
            'id': self.id,
            'origin': self.origin,
            'destination': self.destination,
            'departure_date': self.departure_date,
            'return_date': self.return_date,
            'airline': self.airline,
            'departure_time': self.departure_time,
            'arrival_time': self.arrival_time,
            'duration': self.duration,
            'stops': self.stops,
            'price': self.price,
            'currency': self.currency,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
        }


class ScrapeLog(Base):
    """Log des scraping effectués"""
    __tablename__ = 'scrape_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    scrape_type = Column(String(20), nullable=False)  # 'calendar' ou 'flights'
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    
    # Résultats
    success = Column(Boolean, default=True)
    results_count = Column(Integer, default=0)
    error_message = Column(String(500), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    
    # Contexte
    params = Column(JSON, nullable=True)
    
    __table_args__ = (
        Index('idx_scrape_route', 'origin', 'destination'),
        Index('idx_started_at', 'started_at'),
    )
    
    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"<ScrapeLog({status} {self.scrape_type} {self.origin}-{self.destination})>"