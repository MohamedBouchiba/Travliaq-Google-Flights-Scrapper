"""
🌐 Test de l'Endpoint API Calendar Prices
Teste l'intégration complète du nouveau scraper avec FastAPI
"""

import requests
import json
import time
from datetime import datetime
from pathlib import Path


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


def print_section(title):
    """Affiche un titre de section"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_health_check():
    """Test 1: Health check"""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Database: {data.get('database')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_calendar_prices_new_scrape():
    """Test 2: Scraping de nouvelles données"""
    print_section("TEST 2: Calendar Prices - Nouveau Scraping")
    
    params = {
        "origin": "BRU",
        "destination": "CDG",
        "months": 2,
        "force_refresh": True  # Force le scraping
    }
    
    print(f"Paramètres: {json.dumps(params, indent=2)}")
    print("\n🕐 Scraping en cours (cela peut prendre 30-60 secondes)...\n")
    
    try:
        start = time.time()
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/calendar-prices",
            params=params,
            timeout=120  # 2 minutes max
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Succès en {duration:.1f}s")
            print(f"\n📊 Résultats:")
            print(f"   Route: {data['origin']} → {data['destination']}")
            print(f"   Total dates: {data['total_dates']}")
            print(f"   Prix min: {data['min_price']}€")
            print(f"   Prix max: {data['max_price']}€")
            print(f"   Prix moyen: {data['avg_price']:.0f}€")
            print(f"   From cache: {data['from_cache']}")
            
            print(f"\n🏆 Top 5 meilleures dates:")
            for i, best in enumerate(data['best_dates'], 1):
                print(f"   {i}. {best['date']}: {best['price']}€")
            
            # Sauvegarder
            output = Path("api_test_results_new_scrape.json")
            output.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"\n💾 Résultats sauvegardés: {output}")
            
            return True
        else:
            print(f"❌ Erreur {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.Timeout:
        print(f"❌ Timeout après 120 secondes")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_calendar_prices_cached():
    """Test 3: Lecture depuis le cache"""
    print_section("TEST 3: Calendar Prices - Lecture Cache")
    
    params = {
        "origin": "BRU",
        "destination": "CDG",
        "months": 2,
        "force_refresh": False  # Utilise le cache
    }
    
    print(f"Paramètres: {json.dumps(params, indent=2)}\n")
    
    try:
        start = time.time()
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/calendar-prices",
            params=params,
            timeout=10
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Succès en {duration:.3f}s")
            print(f"\n📊 Résultats:")
            print(f"   Total dates: {data['total_dates']}")
            print(f"   From cache: {data['from_cache']}")
            
            if data['from_cache']:
                print(f"   ⚡ Cache hit! Réponse instantanée.")
            else:
                print(f"   ⚠️  Pas de cache, re-scraping effectué.")
            
            return True
        else:
            print(f"❌ Erreur {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_cache_stats():
    """Test 4: Stats du cache"""
    print_section("TEST 4: Cache Stats")
    
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/cache/stats",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Stats récupérées")
            print(f"\n📊 Cache Info:")
            cache = data['cache_info']
            print(f"   Total entrées: {cache['total_entries']}")
            print(f"   Total routes: {cache['total_routes']}")
            
            if cache['oldest_entry']:
                print(f"   Entrée la plus ancienne: {cache['oldest_entry']}")
            if cache['newest_entry']:
                print(f"   Entrée la plus récente: {cache['newest_entry']}")
            
            print(f"\n📝 Scrapes récents:")
            for scrape in data['recent_scrapes'][:5]:
                status = "✅" if scrape['success'] else "❌"
                print(f"   {status} {scrape['route']} - {scrape['type']} - {scrape['started_at']}")
            
            return True
        else:
            print(f"❌ Erreur {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_multiple_routes():
    """Test 5: Plusieurs routes"""
    print_section("TEST 5: Test Multi-Routes")
    
    routes = [
        ("BRU", "CDG", 1),
        ("AMS", "BCN", 1),
        ("CDG", "LHR", 1),
    ]
    
    results = []
    
    for origin, dest, months in routes:
        print(f"📍 Route: {origin} → {dest} ({months} mois)")
        
        try:
            response = requests.get(
                f"{BASE_URL}{API_PREFIX}/calendar-prices",
                params={
                    "origin": origin,
                    "destination": dest,
                    "months": months,
                    "force_refresh": False  # Utiliser cache si dispo
                },
                timeout=90
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {data['total_dates']} prix | Cache: {data['from_cache']}")
                results.append(True)
            else:
                print(f"   ❌ Erreur {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            results.append(False)
        
        time.sleep(1)  # Petit délai entre les requêtes
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Taux de réussite: {success_rate:.0f}% ({sum(results)}/{len(results)})")
    
    return all(results)


def test_error_cases():
    """Test 6: Cas d'erreur"""
    print_section("TEST 6: Gestion des Erreurs")
    
    # Test 6.1: Code aéroport invalide
    print("Test 6.1: Code aéroport invalide")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/calendar-prices",
            params={"origin": "XXX", "destination": "YYY", "months": 1},
            timeout=10
        )
        if response.status_code in [400, 422, 500]:
            print(f"   ✅ Erreur attendue: {response.status_code}")
        else:
            print(f"   ❌ Devrait retourner une erreur")
    except Exception as e:
        print(f"   ⚠️  Exception: {e}")
    
    # Test 6.2: Paramètres manquants
    print("\nTest 6.2: Paramètres manquants")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/calendar-prices",
            params={},
            timeout=10
        )
        if response.status_code in [400, 422]:
            print(f"   ✅ Erreur attendue: {response.status_code}")
        else:
            print(f"   ❌ Devrait retourner une erreur")
    except Exception as e:
        print(f"   ⚠️  Exception: {e}")
    
    # Test 6.3: Months invalide
    print("\nTest 6.3: Nombre de mois invalide")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/calendar-prices",
            params={"origin": "BRU", "destination": "CDG", "months": 15},
            timeout=10
        )
        if response.status_code in [400, 422]:
            print(f"   ✅ Erreur attendue: {response.status_code}")
        else:
            print(f"   ❌ Devrait retourner une erreur")
    except Exception as e:
        print(f"   ⚠️  Exception: {e}")
    
    print("\n✅ Tests d'erreur terminés")
    return True


def main():
    """Exécute tous les tests API"""
    print("\n" + "🌐 TEST SUITE - API Calendar Prices ".center(70, "="))
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Base URL: {BASE_URL}")
    
    # Vérifier que l'API est lancée
    print("\n⏳ Vérification de l'API...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print(f"❌ API non accessible à {BASE_URL}")
            print("   Assurez-vous que l'API est lancée: uvicorn src.api.main:app")
            return 1
    except Exception as e:
        print(f"❌ Impossible de se connecter à {BASE_URL}")
        print(f"   Erreur: {e}")
        print("\n   💡 Lancez l'API avec:")
        print("      python -m uvicorn src.api.main:app --reload")
        return 1
    
    # Tests
    results = {
        "Health Check": test_health_check(),
        "Nouveau Scraping": test_calendar_prices_new_scrape(),
        "Cache": test_calendar_prices_cached(),
        "Cache Stats": test_cache_stats(),
        "Multi-Routes": test_multiple_routes(),
        "Erreurs": test_error_cases(),
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
        print("🎉 Tous les tests API sont passés!")
        print("   L'intégration du nouveau scraper est réussie!")
        return 0
    else:
        print("⚠️  Certains tests ont échoué.")
        print("   Vérifiez les logs de l'API et les messages d'erreur ci-dessus.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        input("\n⏸️  Appuyez sur ENTRÉE pour quitter...")
        import sys
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrompus")
        import sys
        sys.exit(1)
