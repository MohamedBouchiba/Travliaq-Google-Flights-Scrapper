"""
🧪 Script de Test pour le Nouveau Calendar Scraper
Test l'intégration avec l'API FastAPI existante
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Ajouter le chemin src au PYTHONPATH
script_dir = Path(__file__).parent
if script_dir.name == "tests":
    root_dir = script_dir.parent  # Remonte à la racine
else:
    root_dir = script_dir
sys.path.insert(0, str(root_dir))

from src.scrapers.calendar_scraper import CalendarScraper
from src.database.manager import db_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_basic_scraping():
    """Test 1: Scraping basique"""
    print("\n" + "="*70)
    print("TEST 1: Scraping Basique (BRU → CDG, 2 mois)")
    print("="*70 + "\n")
    
    try:
        scraper = CalendarScraper(headless=False)  # Visible pour debug
        prices = scraper.scrape("BRU", "CDG", months_ahead=2)
        
        if prices:
            print(f"✅ Succès: {len(prices)} prix récupérés")
            print(f"   Dates: {min(prices.keys())} → {max(prices.keys())}")
            print(f"   Prix: {min(prices.values()):.0f}€ → {max(prices.values()):.0f}€")
            print(f"   Moyenne: {sum(prices.values())/len(prices):.0f}€")
            
            # Sauvegarder les résultats
            output_file = Path("test_results_basic.json")
            output_file.write_text(
                json.dumps({
                    "test": "basic",
                    "origin": "BRU",
                    "destination": "CDG",
                    "months": 2,
                    "timestamp": datetime.now().isoformat(),
                    "total_prices": len(prices),
                    "prices": prices
                }, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"\n   📁 Résultats: {output_file}")
            return True
        else:
            print("❌ Échec: Aucun prix trouvé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_integration():
    """Test 2: Intégration avec la base de données"""
    print("\n" + "="*70)
    print("TEST 2: Intégration Base de Données")
    print("="*70 + "\n")
    
    try:
        # Scraper
        scraper = CalendarScraper(headless=True)
        prices = scraper.scrape("AMS", "BCN", months_ahead=1)
        
        if not prices:
            print("❌ Échec scraping")
            return False
        
        # Sauvegarder en cache
        success = db_manager.save_calendar_prices("AMS", "BCN", prices)
        
        if not success:
            print("❌ Échec sauvegarde DB")
            return False
        
        print(f"✅ {len(prices)} prix sauvegardés en DB")
        
        # Tester la lecture du cache
        cached = db_manager.get_cached_calendar_prices("AMS", "BCN")
        
        if cached and len(cached) == len(prices):
            print(f"✅ Cache fonctionne: {len(cached)} prix récupérés")
            return True
        else:
            print(f"❌ Problème cache: {len(cached) if cached else 0}/{len(prices)} prix")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_months():
    """Test 3: Scraping multi-mois (stress test)"""
    print("\n" + "="*70)
    print("TEST 3: Scraping Multi-Mois (CDG → LHR, 4 mois)")
    print("="*70 + "\n")
    
    try:
        scraper = CalendarScraper(headless=True)
        
        import time
        start = time.time()
        prices = scraper.scrape("CDG", "LHR", months_ahead=4)
        duration = time.time() - start
        
        if prices:
            print(f"✅ Succès en {duration:.1f}s")
            print(f"   {len(prices)} prix récupérés")
            print(f"   Performance: {len(prices)/duration:.1f} prix/seconde")
            
            # Vérifier la distribution par mois
            from collections import defaultdict
            by_month = defaultdict(int)
            for date_str in prices.keys():
                month = date_str[:7]  # YYYY-MM
                by_month[month] += 1
            
            print(f"\n   Distribution par mois:")
            for month, count in sorted(by_month.items()):
                print(f"      {month}: {count} jours")
            
            return True
        else:
            print("❌ Échec: Aucun prix trouvé")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """Test 4: Gestion des erreurs"""
    print("\n" + "="*70)
    print("TEST 4: Gestion des Erreurs")
    print("="*70 + "\n")
    
    # Test 4.1: Code aéroport invalide
    print("   Test 4.1: Code aéroport invalide...")
    try:
        scraper = CalendarScraper(headless=True)
        prices = scraper.scrape("XXX", "YYY", months_ahead=1)
        print("   ❌ Devrait lever une exception")
        return False
    except Exception as e:
        print(f"   ✅ Exception attendue: {type(e).__name__}")
    
    # Test 4.2: Nombre de mois invalide
    print("\n   Test 4.2: Nombre de mois invalide...")
    try:
        scraper = CalendarScraper(headless=True)
        prices = scraper.scrape("BRU", "CDG", months_ahead=15)
        print("   ❌ Devrait lever une exception")
        return False
    except Exception as e:
        print(f"   ✅ Exception attendue: {type(e).__name__}")
    
    print("\n✅ Gestion des erreurs fonctionne correctement")
    return True


def test_api_compatibility():
    """Test 5: Compatibilité avec l'API existante"""
    print("\n" + "="*70)
    print("TEST 5: Compatibilité API")
    print("="*70 + "\n")
    
    try:
        # Simuler un appel API
        from src.models.schemas import CalendarPricesResponse
        
        # Scraper
        scraper = CalendarScraper(headless=True)
        prices = scraper.scrape("BRU", "CDG", months_ahead=2)
        
        if not prices:
            print("❌ Échec scraping")
            return False
        
        # Créer la réponse API
        response = CalendarPricesResponse.from_prices_dict(
            origin="BRU",
            destination="CDG",
            prices=prices,
            from_cache=False
        )
        
        # Vérifier les champs
        assert response.origin == "BRU"
        assert response.destination == "CDG"
        assert response.total_dates == len(prices)
        assert response.min_price == min(prices.values())
        assert response.max_price == max(prices.values())
        assert len(response.best_dates) <= 5
        
        print(f"✅ Réponse API correctement formée:")
        print(f"   Total dates: {response.total_dates}")
        print(f"   Min/Max: {response.min_price}€ / {response.max_price}€")
        print(f"   Meilleure date: {response.best_dates[0].date} @ {response.best_dates[0].price}€")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests"""
    print("\n" + "🧪 TEST SUITE - Nouveau Calendar Scraper ".center(70, "="))
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    results = {
        "Test 1 - Scraping Basique": test_basic_scraping(),
        "Test 2 - Base de Données": test_database_integration(),
        "Test 3 - Multi-Mois": test_multi_months(),
        "Test 4 - Erreurs": test_error_handling(),
        "Test 5 - API": test_api_compatibility(),
    }
    
    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{'='*70}")
    print(f"Résultat: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")
    print("="*70 + "\n")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! Le scraper est prêt pour la production.")
        return 0
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez les logs ci-dessus.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        input("\n⏸️  Appuyez sur ENTRÉE pour quitter...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        input("\n⏸️  Appuyez sur ENTRÉE pour quitter...")
        sys.exit(1)
