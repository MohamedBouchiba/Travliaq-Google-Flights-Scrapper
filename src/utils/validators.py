"""
Validators pour les inputs du scraper
"""

import re
from datetime import datetime, date, timedelta
from typing import Optional
from src.core.exceptions import InvalidAirportCodeError, InvalidDateError


class Validators:
    """Classe de validation des données"""
    
    # Liste des codes IATA valides (les plus communs)
    # En production, charger depuis une base ou API
    VALID_AIRPORT_CODES = {
        # Europe
        'BRU', 'CDG', 'ORY', 'LHR', 'AMS', 'FRA', 'MAD', 'BCN', 'FCO', 
        'MXP', 'VIE', 'ZRH', 'CPH', 'OSL', 'ARN', 'DUB', 'LIS', 'OPO',
        'ATH', 'PRG', 'WAW', 'BUD', 'VCE', 'NAP', 'MUC', 'DUS', 'HAM',
        # Amérique du Nord
        'JFK', 'LAX', 'ORD', 'MIA', 'DFW', 'SFO', 'SEA', 'BOS', 'LAS',
        'ATL', 'DEN', 'PHX', 'IAH', 'YYZ', 'YVR', 'YUL', 'MEX',
        # Asie
        'DXB', 'HKG', 'SIN', 'ICN', 'NRT', 'HND', 'BKK', 'KUL', 'DEL',
        'PVG', 'PEK', 'CAN', 'TPE', 'MNL',
        # Océanie
        'SYD', 'MEL', 'BNE', 'AKL', 'CHC',
        # Afrique
        'CPT', 'JNB', 'CAI', 'CMN', 'TUN', 'ALG',
        # Moyen-Orient
        'DOH', 'AUH', 'TLV', 'AMM', 'BEY',
        # Amérique du Sud
        'GRU', 'GIG', 'EZE', 'SCL', 'BOG', 'LIM'
    }
    
    @staticmethod
    def validate_airport_code(code: str, strict: bool = False) -> str:
        """
        Valide un code aéroport IATA
        
        Args:
            code: Code IATA (3 lettres)
            strict: Si True, vérifie dans la liste des codes connus
            
        Returns:
            Code en majuscules si valide
            
        Raises:
            InvalidAirportCodeError: Si le code est invalide
        """
        if not code:
            raise InvalidAirportCodeError("Code vide")
        
        code = code.upper().strip()
        
        # Vérifier le format (3 lettres)
        if not re.match(r'^[A-Z]{3}$', code):
            raise InvalidAirportCodeError(code)
        
        # Vérification stricte (liste connue)
        if strict and code not in Validators.VALID_AIRPORT_CODES:
            raise InvalidAirportCodeError(code)
        
        return code
    
    @staticmethod
    def validate_date(date_str: str, 
                     min_date: Optional[date] = None,
                     max_date: Optional[date] = None) -> date:
        """
        Valide et parse une date au format YYYY-MM-DD
        
        Args:
            date_str: Date au format string
            min_date: Date minimum autorisée
            max_date: Date maximum autorisée
            
        Returns:
            Objet date si valide
            
        Raises:
            InvalidDateError: Si la date est invalide
        """
        if not date_str:
            raise InvalidDateError("", "Date vide")
        
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            raise InvalidDateError(date_str, "Format attendu: YYYY-MM-DD")
        
        # Date minimum par défaut: aujourd'hui
        if min_date is None:
            min_date = date.today()
        
        if parsed_date < min_date:
            raise InvalidDateError(
                date_str, 
                f"Date trop ancienne (minimum: {min_date.isoformat()})"
            )
        
        if max_date and parsed_date > max_date:
            raise InvalidDateError(
                date_str,
                f"Date trop éloignée (maximum: {max_date.isoformat()})"
            )
        
        return parsed_date
    
    @staticmethod
    def validate_months_ahead(months: int) -> int:
        """
        Valide le nombre de mois à scraper
        
        Args:
            months: Nombre de mois
            
        Returns:
            Nombre de mois si valide
            
        Raises:
            ValueError: Si invalide
        """
        if not isinstance(months, int):
            raise ValueError("months doit être un entier")
        
        if months < 1:
            raise ValueError("months doit être >= 1")
        
        if months > 12:
            raise ValueError("months ne peut pas dépasser 12")
        
        return months
    
    @staticmethod
    def validate_passengers(passengers: int) -> int:
        """
        Valide le nombre de passagers
        
        Args:
            passengers: Nombre de passagers
            
        Returns:
            Nombre si valide
            
        Raises:
            ValueError: Si invalide
        """
        if not isinstance(passengers, int):
            raise ValueError("passengers doit être un entier")
        
        if passengers < 1:
            raise ValueError("passengers doit être >= 1")
        
        if passengers > 9:
            raise ValueError("passengers ne peut pas dépasser 9")
        
        return passengers
    
    @staticmethod
    def validate_route(origin: str, destination: str) -> tuple[str, str]:
        """
        Valide une route complète
        
        Args:
            origin: Code aéroport de départ
            destination: Code aéroport d'arrivée
            
        Returns:
            Tuple (origin, destination) en majuscules
            
        Raises:
            InvalidAirportCodeError: Si un code est invalide
            ValueError: Si origin == destination
        """
        origin = Validators.validate_airport_code(origin)
        destination = Validators.validate_airport_code(destination)
        
        if origin == destination:
            raise ValueError("L'origine et la destination doivent être différentes")
        
        return origin, destination