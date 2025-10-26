# 🚀 Guide de Déploiement - Nouveau Calendar Scraper

## 📋 Pré-requis

### Système
- Python 3.9+
- Chrome/Chromium installé
- ChromeDriver compatible (fourni dans `drivers/`)

### Dépendances
Toutes les dépendances existantes sont conservées. Aucune nouvelle installation nécessaire.

```bash
# Vérifier les dépendances
pip install -r requirements.txt
```

## 🔧 Installation

### Option 1: Remplacement Direct (Recommandé)

```bash
# 1. Sauvegarder l'ancien scraper (optionnel)
cp src/scrapers/calendar_scraper.py src/scrapers/calendar_scraper.py.backup

# 2. Copier le nouveau scraper
cp calendar_scraper.py src/scrapers/calendar_scraper.py

# 3. Vérifier que tout fonctionne
python test_new_scraper.py
```

### Option 2: Déploiement avec Git

```bash
# 1. Créer une nouvelle branche
git checkout -b feature/new-calendar-scraper

# 2. Ajouter les fichiers
git add src/scrapers/calendar_scraper.py
git add test_new_scraper.py
git add test_api_endpoint.py
git add README_INTEGRATION.md

# 3. Commit
git commit -m "feat: Nouveau calendar scraper avec navigation intelligente"

# 4. Pousser et créer une PR
git push origin feature/new-calendar-scraper
```

## 🧪 Tests

### 1. Tests Unitaires

```bash
# Tester le scraper seul
python test_new_scraper.py
```

**Durée estimée:** 5-10 minutes  
**Tests effectués:**
- Scraping basique
- Intégration DB
- Multi-mois
- Gestion d'erreurs
- Compatibilité API

### 2. Tests d'Intégration API

```bash
# 1. Lancer l'API
python -m uvicorn src.api.main:app --reload

# 2. Dans un autre terminal, tester l'endpoint
python test_api_endpoint.py
```

**Durée estimée:** 3-5 minutes  
**Tests effectués:**
- Health check
- Nouveau scraping
- Lecture cache
- Stats cache
- Multi-routes
- Cas d'erreur

### 3. Test Manuel

```bash
# Mode visible (debug)
python -c "
from src.scrapers.calendar_scraper import CalendarScraper
scraper = CalendarScraper(headless=False)
prices = scraper.scrape('BRU', 'CDG', 3)
print(f'{len(prices)} prix récupérés')
"
```

## 🔄 Migration

### Étape 1: Backup de la Base de Données

```bash
# SQLite
cp data/flights.db data/flights.db.backup

# PostgreSQL (si applicable)
pg_dump -U user -d flights_db > backup.sql
```

### Étape 2: Nettoyer le Cache (Optionnel)

```bash
# Via l'API
curl -X DELETE "http://localhost:8000/api/v1/cache/clear?days=7"

# Ou via Python
python -c "
from src.database.manager import db_manager
db_manager.clear_old_cache(days=7)
print('Cache nettoyé')
"
```

### Étape 3: Test de Régression

```bash
# Comparer ancien vs nouveau scraper
# (Nécessite de garder l'ancien fichier)

python -c "
# Test avec ancien scraper
from src.scrapers.calendar_scraper_backup import CalendarScraper as OldScraper
old = OldScraper()
old_prices = old.scrape('BRU', 'CDG', 2)

# Test avec nouveau scraper  
from src.scrapers.calendar_scraper import CalendarScraper
new = CalendarScraper()
new_prices = new.scrape('BRU', 'CDG', 2)

print(f'Ancien: {len(old_prices)} prix')
print(f'Nouveau: {len(new_prices)} prix')
print(f'Différence: {len(new_prices) - len(old_prices)} prix')
"
```

## 🌐 Déploiement Production

### Configuration Production

**1. Variables d'Environnement**

Créer/modifier `.env.production`:

```env
# Environment
ENVIRONMENT=production
DEBUG=false

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Scraper
HEADLESS=true
SCREENSHOT_ON_ERROR=false  # Désactiver en prod pour économiser espace
TIMEOUT=30
MAX_RETRIES=3

# Database
DATABASE_URL=postgresql://user:pass@localhost/flights_db  # ou SQLite

# Cache
CACHE_TTL_MINUTES=120  # 2h en production

# Logs
LOG_LEVEL=INFO
LOG_FILE=logs/production.log

# Rate Limiting
REQUESTS_PER_HOUR=30
DELAY_BETWEEN_REQUESTS_MIN=3.0
DELAY_BETWEEN_REQUESTS_MAX=7.0

# Proxy (optionnel)
USE_PROXY=false
PROXY_URL=
```

**2. Lancer en Production**

```bash
# Avec Uvicorn (développement/staging)
uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --env-file .env.production

# Avec Gunicorn (production)
gunicorn src.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 180 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Docker Deployment

**Dockerfile** (à créer si nécessaire):

```dockerfile
FROM python:3.11-slim

# Installer Chrome et ChromeDriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copier requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Créer les répertoires
RUN mkdir -p data logs screenshots

# Variables d'environnement
ENV HEADLESS=true
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./screenshots:/app/screenshots
    restart: unless-stopped
    
  # PostgreSQL (optionnel)
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: flights_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

**Déploiement:**

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs
docker-compose logs -f api

# Stop
docker-compose down
```

## 📊 Monitoring

### 1. Logs

```bash
# Logs en temps réel
tail -f logs/production.log

# Erreurs uniquement
tail -f logs/errors.log

# Rechercher des erreurs
grep "ERROR" logs/production.log | tail -20
```

### 2. Health Check

```bash
# Vérifier que l'API répond
curl http://localhost:8000/api/v1/health

# Avec watch (toutes les 10s)
watch -n 10 'curl -s http://localhost:8000/api/v1/health | jq'
```

### 3. Métriques

```bash
# Stats du cache
curl http://localhost:8000/api/v1/cache/stats | jq

# Tester une route
curl "http://localhost:8000/api/v1/calendar-prices?origin=BRU&destination=CDG&months=2"
```

### 4. Alertes (Optionnel)

Configurer des alertes avec un service externe:

```python
# exemple_alert.py
import requests
import time

def check_health():
    try:
        r = requests.get('http://localhost:8000/api/v1/health', timeout=5)
        if r.status_code != 200:
            send_alert(f"API unhealthy: {r.status_code}")
    except Exception as e:
        send_alert(f"API down: {e}")

def send_alert(message):
    # Slack, email, SMS, etc.
    pass

if __name__ == "__main__":
    while True:
        check_health()
        time.sleep(300)  # Check every 5 minutes
```

## 🔄 Rollback

En cas de problème:

### Rollback Rapide

```bash
# 1. Restaurer l'ancien scraper
cp src/scrapers/calendar_scraper.py.backup src/scrapers/calendar_scraper.py

# 2. Redémarrer l'API
# Avec systemd
sudo systemctl restart flights-api

# Avec Docker
docker-compose restart api

# Manuel
pkill -f uvicorn && uvicorn src.api.main:app
```

### Rollback Git

```bash
# Trouver le commit
git log --oneline | grep calendar

# Revert
git revert <commit-hash>

# Ou reset (attention!)
git reset --hard HEAD~1
```

## 📝 Checklist de Déploiement

- [ ] Backup de la base de données effectué
- [ ] Tests unitaires passés (test_new_scraper.py)
- [ ] Tests API passés (test_api_endpoint.py)
- [ ] Configuration production vérifiée (.env.production)
- [ ] Logs configurés correctement
- [ ] Screenshots désactivés en production
- [ ] Health check fonctionnel
- [ ] Cache nettoyé si nécessaire
- [ ] Documentation mise à jour
- [ ] Rollback plan ready
- [ ] Monitoring configuré
- [ ] Équipe notifiée du déploiement

## 🆘 Troubleshooting

### Problème: "ChromeDriver introuvable"

```bash
# Vérifier ChromeDriver
ls -la drivers/chromedriver.exe

# Télécharger si nécessaire
# https://chromedriver.chromium.org/downloads
```

### Problème: "Impossible d'ouvrir le calendrier"

```bash
# Tester en mode visible
python -c "
from src.scrapers.calendar_scraper import CalendarScraper
scraper = CalendarScraper(headless=False)
# Observer ce qui se passe
"
```

### Problème: "Timeout constant"

```env
# Augmenter les timeouts dans .env
TIMEOUT=45
DELAY_BETWEEN_REQUESTS_MAX=10.0
```

### Problème: "Rate limit Google"

```env
# Réduire la fréquence
REQUESTS_PER_HOUR=20
DELAY_BETWEEN_REQUESTS_MIN=5.0
DELAY_BETWEEN_REQUESTS_MAX=10.0

# Activer un proxy
USE_PROXY=true
PROXY_URL=http://proxy:port
```

## 📞 Support

- **Documentation:** README_INTEGRATION.md
- **Tests:** test_new_scraper.py, test_api_endpoint.py
- **Logs:** logs/production.log, logs/errors.log
- **Screenshots:** screenshots/ (si activé)

---

**Version:** 2.0.0  
**Date:** Octobre 2025  
**Status:** ✅ Production Ready
