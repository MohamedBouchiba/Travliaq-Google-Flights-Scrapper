# src/api/middleware/rate_limiter.py
"""
Rate limiter pour éviter les abus
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict
import time


class RateLimiter:
    """Rate limiter simple en mémoire"""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Vérifie si la requête est autorisée"""
        now = time.time()
        window_start = now - self.window_seconds

        # Nettoyer les vieilles requêtes
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]

        # Vérifier la limite
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        # Ajouter la nouvelle requête
        self.requests[client_id].append(now)
        return True


# Instance globale
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


async def rate_limit_middleware(request: Request, call_next):
    """Middleware de rate limiting"""

    # Ignorer les endpoints système
    if request.url.path in ["/api/v1/health", "/", "/api/v1/docs"]:
        return await call_next(request)

    # Identifier le client (IP)
    client_ip = request.client.host

    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests",
                "detail": "Rate limit exceeded. Try again later."
            }
        )

    return await call_next(request)