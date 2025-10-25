"""
Script de test du scraper
Usage: python scripts/test_scraper.py
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.scrapers.calendar_scraper import CalendarScraper
from src.database.db_manager import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_calendar_scraper():
    """Test du scraper calendrier"""
    
    print("\n" + "="*60)
    print("🧪 TEST DU SCRAPER CALENDRIER")
    print("="*60 + "\n")
    
    # Configuration du test
    ORIGIN = "BRU"
    DESTINATION = "CDG"
    MONTHS = 2
    
    print(f"📍 Route: {ORIGIN} → {DESTINATION}")
    print(f"📅 Mois à scraper: {MONTHS}")
    print(f"\n{'='*60}\n")
    
    scraper = CalendarScraper(headless=False)
    
    try:
        print("🕷️  Lancement du scraping...\n")
        
        prices = scraper.scrape(
            origin=ORIGIN,
            destination=DESTINATION,
            months_ahead=MONTHS
        )
        
        if prices:
            print(f"\n{'='*60}")
            print(f"✅ SUCCÈS!")
            print(f"{'='*60}")
            print(f"Dates trouvées: {len(prices)}")
            
            price_values = list(prices.values())
            print(f"Prix minimum: {min(price_values)}€")
            print(f"Prix maximum: {max(price_values)}€")
            print(f"Prix moyen: {sum(price_values)/len(price_values):.2f}€")
            
            # Top 5
            sorted_prices = sorted(prices.items(), key=lambda x: x[1])
            print(f"\n🏆 Top 5 meilleurs prix:")
            for date, price in sorted_prices[:5]:
                print(f"  {date}: {price}€")
            
            # Test sauvegarde en DB
            print(f"\n💾 Sauvegarde dans la DB...")
            db_manager.save_calendar_prices(ORIGIN, DESTINATION, prices)
            print("✓ Données sauvegardées")
            
            # Test lecture du cache
            print(f"\n📦 Test lecture du cache...")
            cached = db_manager.get_cached_calendar_prices(ORIGIN, DESTINATION)
            if cached:
                print(f"✓ Cache hit: {len(cached)} prix")
            
            print(f"\n{'='*60}\n")
            return True
            
        else:
            print("\n❌ Aucun prix trouvé\n")
            return False
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}\n")
        logger.error(f"Erreur test: {e}", exc_info=True)
        return False
    finally:
        scraper.close()


def test_cache_stats():
    """Test des stats du cache"""
    
    print("\n" + "="*60)
    print("📊 STATISTIQUES DU CACHE")
    print("="*60 + "\n")
    
    stats = db_manager.get_cache_stats()
    
    print(f"Entrées totales: {stats.get('total_entries', 0)}")
    print(f"Routes uniques: {stats.get('total_routes', 0)}")
    
    if stats.get('oldest_entry'):
        print(f"Plus ancienne: {stats['oldest_entry']}")
    if stats.get('newest_entry'):
        print(f"Plus récente: {stats['newest_entry']}")
    
    recent = stats.get('recent_scrapes', [])
    if recent:
        print(f"\n📝 Derniers scraping:")
        for scrape in recent[:5]:
            status = "✓" if scrape.get('success') else "✗"
            print(f"  {status} {scrape.get('type')} {scrape.get('route')}")
    
    print(f"\n{'='*60}\n")


def main():
    """Fonction principale"""
    
    print("\n" + "="*60)
    print("🧪 SUITE DE TESTS - TRAVLIAQ SCRAPER")
    print("="*60)
    
    # Test 1: Scraper
    success = test_calendar_scraper()
    
    # Test 2: Cache stats
    test_cache_stats()
    
    # Résumé
    print("="*60)
    if success:
        print("✅ Tests terminés avec succès!")
    else:
        print("❌ Tests échoués")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()