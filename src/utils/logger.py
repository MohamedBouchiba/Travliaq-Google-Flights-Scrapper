# src/utils/logger.py - VERSION MINIMALISTE

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from ..core.config import settings


class ProductionLogger:
    """Logger optimisé pour production (minimal)"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Obtient un logger configuré"""
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(settings.log_level)

        if logger.handlers:
            return logger

        # En production: seulement fichier rotatif, pas de console
        if settings.environment == "production":
            # Fichier avec rotation stricte
            file_handler = logging.handlers.RotatingFileHandler(
                settings.log_file,
                maxBytes=settings.log_rotation_size * 1024 * 1024,  # MB en bytes
                backupCount=2,  # Garder 2 backups max
                encoding='utf-8'
            )
            file_handler.setLevel(logging.WARNING)  # Seulement WARNING et plus

            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        else:
            # Dev: console colorée
            import colorlog
            console_handler = colorlog.StreamHandler()
            console_handler.setLevel(settings.log_level)

            color_formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
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

        cls._loggers[name] = logger
        return logger


def get_logger(name: str) -> logging.Logger:
    """Helper pour obtenir un logger"""
    return ProductionLogger.get_logger(name)