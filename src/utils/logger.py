"""
Configuration avancée du logging avec colorlog
Logs colorés dans la console et fichiers rotatifs
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import colorlog
from src.core.config import settings


class Logger:
    """Gestionnaire de logging centralisé"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        Obtient ou crée un logger
        
        Args:
            name: Nom du logger (généralement __name__)
            log_file: Fichier de log spécifique (optionnel)
            
        Returns:
            Logger configuré
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(settings.log_level)
        
        # Éviter les doublons de handlers
        if logger.handlers:
            return logger
        
        # Format des logs
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # Handler console avec couleurs
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(settings.log_level)
        
        color_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)
        
        # Handler fichier avec rotation
        log_file_path = log_file or settings.log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Toujours DEBUG dans les fichiers
        
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler fichier d'erreurs séparé
        error_log_file = Path(log_file_path).parent / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            str(error_log_file),
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        cls._loggers[name] = logger
        return logger


def get_logger(name: str) -> logging.Logger:
    """
    Fonction helper pour obtenir un logger
    
    Usage:
        from src.utils.logger import get_logger
        logger = get_logger(__name__)
    """
    return Logger.get_logger(name)


# Logger par défaut pour l'application
app_logger = get_logger("travliaq.scraper")