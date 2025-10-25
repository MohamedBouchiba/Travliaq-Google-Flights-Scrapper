# 🛫 Travliaq - Google Flights Scraper

API REST pour scraper les prix des vols Google Flights.

## Installation

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Utilisation

```bash
python scripts/run_api.py
```

Documentation: http://localhost:8000/api/v1/docs

## Endpoints

### GET /api/v1/calendar-prices
Récupère les prix du calendrier.

Paramètres:
- origin: Code IATA départ
- destination: Code IATA arrivée  
- months: Nombre de mois (défaut: 3)
- force_refresh: Forcer re-scraping (défaut: false)

Exemple:
```bash
curl "http://localhost:8000/api/v1/calendar-prices?origin=BRU&destination=CDG&months=3"
```
