# scripts/scraper_worker.py - VERSION COMPLÈTE

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Setup path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def log_with_time(job_id, message):
    """Log avec timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [Worker-{job_id}] {message}", flush=True)


def main():
    """Point d'entrée du worker"""
    if len(sys.argv) != 7:
        print(f"ERROR: Mauvais nombre d'arguments: {len(sys.argv)}")
        print("Usage: scraper_worker.py <origin> <dest> <start> <end> <result_file> <job_id>")
        sys.exit(1)

    origin = sys.argv[1]
    destination = sys.argv[2]
    start_date = sys.argv[3]
    end_date = sys.argv[4]
    result_file = Path(sys.argv[5])
    job_id = sys.argv[6]

    log_with_time(job_id, f"DÉMARRAGE: {origin}->{destination} ({start_date} to {end_date})")
    start_time = time.time()

    try:
        # Import ici pour éviter problèmes de sérialisation
        from src.scrapers.calendar_scraper import CalendarScraper
        from src.utils.logger import get_logger

        logger = get_logger(f"worker_{job_id}")

        log_with_time(job_id, "Initialisation du scraper...")
        scraper = CalendarScraper(headless=True)

        log_with_time(job_id, "Scraping en cours...")
        prices = scraper.scrape_date_range(origin, destination, start_date, end_date)

        duration = time.time() - start_time
        log_with_time(job_id, f"TERMINÉ: {len(prices)} prix en {duration:.1f}s")

        # Sauvegarder le résultat
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(prices, f, ensure_ascii=False, indent=2)

        log_with_time(job_id, f"Résultat sauvegardé: {result_file}")
        sys.exit(0)

    except Exception as e:
        duration = time.time() - start_time
        log_with_time(job_id, f"ÉCHEC après {duration:.1f}s: {e}")

        # Logger détaillé
        import traceback
        traceback.print_exc()

        # Sauvegarder l'erreur
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "error": str(e),
                "traceback": traceback.format_exc()
            }, f, ensure_ascii=False, indent=2)

        sys.exit(1)


if __name__ == "__main__":
    main()