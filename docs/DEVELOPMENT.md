# 👨‍💻 Guide de Développement - Ajouter des Endpoints

Guide pour étendre l'API Travliaq avec de nouveaux endpoints de scraping.

---

## 🎯 Objectif

Ajouter un nouvel endpoint pour scraper une autre partie de Google Flights (ex: détails de vols, prix historiques, etc.)

---

## 📁 Architecture du Projet
```
Travliaq-Google-Flights-Scrapper/
├── src/
│   ├── api/
│   │   └── main.py                 # ← Endpoints FastAPI
│   ├── scrapers/
│   │   ├── calendar_scraper.py     # ← Scraper calendrier
│   │   └── votre_nouveau_scraper.py # ← Nouveau scraper
│   ├── models/
│   │   └── schemas.py              # ← Modèles Pydantic
│   └── core/
│       ├── driver_manager.py       # ← Gestion Chrome
│       └── scraper_pool.py         # ← Pool de subprocess
```

---

## 🔧 Étape 1 : Créer un Nouveau Scraper

### 1.1 Template de base

Créer `src/scrapers/flight_details_scraper.py` :
```python
"""
Scraper pour récupérer les détails des vols
"""

import time
import random
from typing import Dict, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ..core.driver_manager import DriverManager
from ..core.config import settings
from ..core.exceptions import ScraperException
from ..utils.logger import get_logger
from ..utils.validators import Validators

logger = get_logger(__name__)


class FlightDetailsScraper:
    """
    Scraper pour récupérer les détails des vols pour une date spécifique
    """
    
    def __init__(self, headless: Optional[bool] = None):
        """Initialise le scraper"""
        self.driver_manager = DriverManager(headless=headless)
        self.driver = None
        self.wait = None
    
    def _build_url(self, origin: str, destination: str, date: str) -> str:
        """Construit l'URL Google Flights"""
        url = f"https://www.google.com/travel/flights"
        url += f"?q=Flights+from+{origin}+to+{destination}+on+{date}"
        url += "&curr=EUR&hl=fr"
        return url
    
    def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        """Délai aléatoire"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    def scrape(
        self,
        origin: str,
        destination: str,
        date: str
    ) -> List[Dict]:
        """
        Scrape les détails des vols pour une date
        
        Args:
            origin: Code IATA départ
            destination: Code IATA arrivée
            date: Date (YYYY-MM-DD)
            
        Returns:
            Liste de vols avec détails
        """
        # Validation
        origin, destination = Validators.validate_route(origin, destination)
        Validators.validate_date(date)
        
        logger.info(f"🕷️ Scraping flights: {origin}->{destination} on {date}")
        
        flights = []
        
        try:
            # Initialiser le driver
            self.driver = self.driver_manager.create_driver()
            self.wait = self.driver_manager.wait
            
            # Charger la page
            url = self._build_url(origin, destination, date)
            self.driver.get(url)
            time.sleep(5)
            
            # TODO: Implémenter la logique de scraping
            # 1. Attendre que les résultats se chargent
            # 2. Extraire les informations de chaque vol
            # 3. Parser et structurer les données
            
            # Exemple de structure de retour
            flights = [
                {
                    "airline": "Brussels Airlines",
                    "flight_number": "SN3175",
                    "departure_time": "10:30",
                    "arrival_time": "11:45",
                    "duration": "1h 15m",
                    "stops": 0,
                    "price": 149.00,
                    "aircraft": "A320",
                    "cabin_class": "Economy"
                }
            ]
            
            logger.info(f"✅ {len(flights)} vols trouvés")
            return flights
            
        except Exception as e:
            logger.error(f"❌ Erreur scraping: {e}", exc_info=True)
            raise ScraperException(f"Erreur lors du scraping: {e}")
        finally:
            self.close()
    
    def close(self):
        """Ferme le driver"""
        if self.driver_manager:
            self.driver_manager.close()
```

### 1.2 Conseils pour le scraping

**Identifier les sélecteurs CSS/XPath** :

1. Ouvrir Google Flights dans Chrome
2. F12 → Inspecter les éléments
3. Trouver les sélecteurs uniques
4. Tester dans la console :
```javascript
   document.querySelectorAll('[data-test-id="flight-card"]')
```

**Attendre le chargement** :
```python
# Attendre un élément spécifique
flight_cards = self.wait.until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".flight-card"))
)
```

**Extraire les données** :
```python
for card in flight_cards:
    try:
        airline = card.find_element(By.CSS_SELECTOR, ".airline-name").text
        price_text = card.find_element(By.CSS_SELECTOR, ".price").text
        price = float(re.sub(r'[^\d.]', '', price_text))
        
        flights.append({
            "airline": airline,
            "price": price,
            # ... autres champs
        })
    except Exception as e:
        logger.warning(f"Erreur extraction vol: {e}")
        continue
```

---

## 📊 Étape 2 : Créer les Modèles Pydantic

### 2.1 Ajouter dans `src/models/schemas.py`
```python
# Request model
class FlightDetailsRequest(BaseModel):
    """Requête pour obtenir les détails des vols"""
    origin: str = Field(..., description="Code IATA départ", example="BRU")
    destination: str = Field(..., description="Code IATA arrivée", example="CDG")
    date: str = Field(..., description="Date (YYYY-MM-DD)", example="2025-11-15")
    force_refresh: bool = Field(default=False, description="Forcer le re-scraping")
    
    @validator('origin', 'destination')
    def validate_airport_codes(cls, v):
        return Validators.validate_airport_code(v)
    
    @validator('date')
    def validate_date(cls, v):
        Validators.validate_date(v)
        return v


# Response models
class FlightDetail(BaseModel):
    """Détails d'un vol"""
    airline: str
    flight_number: Optional[str] = None
    departure_time: str
    arrival_time: str
    duration: str
    stops: int
    price: float
    aircraft: Optional[str] = None
    cabin_class: Optional[str] = None


class FlightDetailsResponse(BaseModel):
    """Réponse avec les détails des vols"""
    origin: str
    destination: str
    date: str
    flights: List[FlightDetail]
    total_flights: int
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    scraped_at: datetime = Field(default_factory=datetime.now)
    from_cache: bool = False
    
    @classmethod
    def from_flights_list(
        cls,
        origin: str,
        destination: str,
        date: str,
        flights: List[Dict],
        from_cache: bool = False
    ):
        """Factory pour créer la réponse"""
        if not flights:
            return cls(
                origin=origin,
                destination=destination,
                date=date,
                flights=[],
                total_flights=0,
                from_cache=from_cache
            )
        
        prices = [f["price"] for f in flights if "price" in f]
        
        return cls(
            origin=origin,
            destination=destination,
            date=date,
            flights=[FlightDetail(**f) for f in flights],
            total_flights=len(flights),
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            from_cache=from_cache
        )
```

---

## 🌐 Étape 3 : Ajouter l'Endpoint dans l'API

### 3.1 Ajouter dans `src/api/main.py`
```python
# En haut du fichier, ajouter l'import
from ..scrapers.flight_details_scraper import FlightDetailsScraper
from ..models.schemas import FlightDetailsRequest, FlightDetailsResponse

# Ajouter l'endpoint
@app.get(
    f"{API_PREFIX}/flight-details",
    response_model=FlightDetailsResponse,
    tags=["Scraping"],
    summary="Récupère les détails des vols",
    description="Récupère tous les vols disponibles pour une date spécifique"
)
async def get_flight_details(
    origin: str = Query(..., description="Code IATA départ"),
    destination: str = Query(..., description="Code IATA arrivée"),
    date: str = Query(..., description="Date (YYYY-MM-DD)"),
    force_refresh: bool = Query(False, description="Forcer le re-scraping"),
):
    """Endpoint pour récupérer les détails des vols"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    start_time = time.time()
    
    logger.info(f"📥 Requête flight-details: {origin}->{destination} on {date}")
    
    # Normaliser
    origin = origin.upper()
    destination = destination.upper()
    
    # TODO: Vérifier le cache si implémenté
    # if not force_refresh:
    #     cached = db_manager.get_cached_flights(origin, destination, date)
    #     if cached:
    #         return FlightDetailsResponse.from_flights_list(...)
    
    # Scraping
    try:
        logger.info(f"🕷️  Lancement scraping...")
        
        # Créer une fonction wrapper pour le subprocess
        def scrape_wrapper():
            scraper = FlightDetailsScraper(headless=settings.headless)
            return scraper.scrape(origin, destination, date)
        
        # Exécuter de manière asynchrone
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor()
        
        flights = await loop.run_in_executor(
            executor,
            scrape_wrapper
        )
        
        if not flights:
            raise HTTPException(
                status_code=404,
                detail="Aucun vol trouvé"
            )
        
        # TODO: Sauvegarder en cache
        # db_manager.save_flights(origin, destination, date, flights)
        
        duration = time.time() - start_time
        logger.info(f"✓ Scraping terminé ({duration:.1f}s)")
        
        return FlightDetailsResponse.from_flights_list(
            origin=origin,
            destination=destination,
            date=date,
            flights=flights,
            from_cache=False
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        if SENTRY_AVAILABLE and settings.sentry_dsn and sentry_sdk:
            sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🧪 Étape 4 : Tester le Nouvel Endpoint

### 4.1 Script de test

Créer `tests/test_flight_details.py` :
```python
"""
Test du nouvel endpoint flight-details
"""

import requests
import time

BASE_URL = "http://localhost:8000/api/v1"


def test_flight_details():
    """Test du scraping de détails de vols"""
    print("\n" + "="*70)
    print("🧪 TEST FLIGHT DETAILS")
    print("="*70)
    
    params = {
        "origin": "BRU",
        "destination": "CDG",
        "date": "2025-11-15",
        "force_refresh": True
    }
    
    print(f"\n📍 Route: {params['origin']} → {params['destination']}")
    print(f"📅 Date: {params['date']}")
    print("\n⏳ Scraping en cours...\n")
    
    start = time.time()
    
    try:
        response = requests.get(
            f"{BASE_URL}/flight-details",
            params=params,
            timeout=120
        )
        
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Succès en {duration:.1f}s")
            print(f"\n📊 Résultats:")
            print(f"   Vols trouvés: {data['total_flights']}")
            
            if data['min_price']:
                print(f"   Prix min: {data['min_price']}€")
            if data['max_price']:
                print(f"   Prix max: {data['max_price']}€")
            
            print(f"\n✈️  Détails des vols:")
            for flight in data['flights'][:5]:  # Top 5
                print(f"\n   {flight['airline']}")
                print(f"      Départ: {flight['departure_time']} → Arrivée: {flight['arrival_time']}")
                print(f"      Durée: {flight['duration']} | Escales: {flight['stops']}")
                print(f"      Prix: {flight['price']}€")
        else:
            print(f"❌ Erreur {response.status_code}")
            print(f"   {response.text}")
            
    except requests.Timeout:
        print("⏰ Timeout!")
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    test_flight_details()
    input("\n⏸️  Appuyez sur ENTRÉE...")
```

### 4.2 Tester
```bash
# Terminal 1: Lancer l'API
python scripts/run_api.py

# Terminal 2: Tester
python tests/test_flight_details.py
```

---

## 📝 Étape 5 : Documenter

### 5.1 Mettre à jour le README
```markdown
## Nouveaux Endpoints

### GET /api/v1/flight-details

Récupère les détails des vols pour une date spécifique.

**Paramètres** :
- `origin` (string) : Code IATA départ
- `destination` (string) : Code IATA arrivée
- `date` (string) : Date au format YYYY-MM-DD
- `force_refresh` (bool) : Forcer le re-scraping

**Exemple** :
\`\`\`bash
curl "http://localhost:8000/api/v1/flight-details?origin=BRU&destination=CDG&date=2025-11-15"
\`\`\`
```

---

## ✅ Checklist pour Ajouter un Endpoint

- [ ] Créer le scraper dans `src/scrapers/`
- [ ] Ajouter les modèles Pydantic dans `src/models/schemas.py`
- [ ] Ajouter l'endpoint dans `src/api/main.py`
- [ ] Implémenter le cache (optionnel)
- [ ] Créer un script de test dans `tests/`
- [ ] Tester en local
- [ ] Documenter dans README.md
- [ ] Commit et push

---

## 🎯 Bonnes Pratiques

### 1. Anti-détection
```python
# Toujours utiliser des délais aléatoires
self._random_delay(2, 5)

# Simuler un comportement humain
self.driver_manager.simulate_human_behavior()

# Varier les user agents
# (déjà géré par DriverManager)
```

### 2. Gestion d'erreurs
```python
try:
    element = self.wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".selector"))
    )
except TimeoutException:
    logger.warning("Élément non trouvé")
    # Fallback ou skip
```

### 3. Logging approprié
```python
logger.info("Action importante")     # Info générale
logger.debug("Détail technique")    # Debug seulement
logger.warning("Problème mineur")   # Attention
logger.error("Erreur critique")     # Erreur
```

### 4. Validation des inputs
```python
# Toujours valider avec les Validators
origin, destination = Validators.validate_route(origin, destination)
date = Validators.validate_date(date)
```

---

## 🆘 Aide au Debugging

### Scraper ne trouve pas les éléments
```python
# Sauvegarder une capture d'écran
self.driver.save_screenshot("debug.png")

# Logger le HTML
html = self.driver.page_source
logger.debug(f"HTML: {html[:500]}")

# Tester en mode non-headless
# Mettre HEADLESS=false dans .env
```

### Performances lentes
```python
# Désactiver le chargement des images
options.add_experimental_option('prefs', {
    'profile.managed_default_content_settings.images': 2
})

# Utiliser des attentes explicites au lieu de time.sleep()
self.wait.until(EC.presence_of_element_located(...))
```

---

## 📚 Ressources

- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Chrome DevTools](https://developer.chrome.com/docs/devtools/)

---

**Bon développement ! 🚀**