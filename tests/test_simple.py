# tests/test_local_production.py - VERSION AVEC RETRY
"""
Test en local avec configuration proche de la production
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8001/api/v1"


def wait_for_api(max_retries=5, delay=2):
    """Attend que l'API soit disponible"""
    for i in range(max_retries):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                return True
        except:
            pass

        if i < max_retries - 1:
            print(f"⏳ API pas encore prête, retry {i + 1}/{max_retries}...")
            time.sleep(delay)

    return False


def test_long_scraping():
    """Test avec un scraping qui peut être long"""
    print("\n" + "=" * 70)
    print("🧪 TEST SCRAPING LONG (peut prendre jusqu'à 2-3 minutes)")
    print("=" * 70)

    routes = [
        ("BRU", "CDG", "2025-11-01", "2025-12-31"),  # 2 mois
    ]

    for origin, dest, start, end in routes:
        print(f"\n📍 Test: {origin} → {dest} ({start} to {end})")
        print(f"⏱️  Démarré à: {datetime.now().strftime('%H:%M:%S')}")

        start_time = time.time()

        try:
            response = requests.get(
                f"{BASE_URL}/calendar-prices",
                params={
                    "origin": origin,
                    "destination": dest,
                    "start_date": start,
                    "end_date": end,
                    "force_refresh": True
                },
                timeout=300
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Succès en {duration:.1f}s")
                print(f"   Prix trouvés: {data['total_dates']}")
                print(f"   Min: {data['min_price']}€")
                print(f"   Max: {data['max_price']}€")
                print(f"   Moyenne: {data['avg_price']:.0f}€")
                print(f"   Cache: {data['from_cache']}")

                # Top 5
                print(f"\n   🏆 Top 5:")
                for best in data['best_dates'][:5]:
                    print(f"      {best['date']}: {best['price']}€")

            else:
                print(f"\n❌ Erreur {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except requests.Timeout:
            print(f"\n⏰ Timeout après 5 minutes!")
        except Exception as e:
            print(f"\n❌ Exception: {e}")


def test_parallel_long():
    """Test parallèle avec scraping long"""
    print("\n" + "=" * 70)
    print("🧪 TEST PARALLÈLE AVEC SCRAPING LONG")
    print("=" * 70)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    routes = [
        ("R1", "BRU", "CDG", "2025-11-01", "2025-11-30"),  # 1 mois
        ("R2", "AMS", "BCN", "2025-11-01", "2025-11-30"),  # 1 mois
        ("R3", "CDG", "LHR", "2025-11-01", "2025-11-30"),  # 1 mois
    ]

    def make_request(route_id, origin, dest, start, end):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{route_id}] 🚀 START: {origin}->{dest}")
        req_start = time.time()

        try:
            response = requests.get(
                f"{BASE_URL}/calendar-prices",
                params={
                    "origin": origin,
                    "destination": dest,
                    "start_date": start,
                    "end_date": end,
                    "force_refresh": True
                },
                timeout=300
            )

            duration = time.time() - req_start
            ts = datetime.now().strftime("%H:%M:%S")

            if response.status_code == 200:
                data = response.json()
                print(f"[{ts}] [{route_id}] ✅ OK en {duration:.1f}s - {data['total_dates']} prix")
                return (route_id, duration, True)
            else:
                print(f"[{ts}] [{route_id}] ❌ Erreur {response.status_code}")
                print(f"   {response.text[:100]}")
                return (route_id, duration, False)
        except Exception as e:
            duration = time.time() - req_start
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] [{route_id}] ❌ {str(e)[:50]}")
            return (route_id, duration, False)

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Lancement de 3 requêtes...")
    overall_start = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(make_request, rid, o, d, s, e)
            for rid, o, d, s, e in routes
        ]

        results = []
        for future in as_completed(futures):
            results.append(future.result())

    overall_duration = time.time() - overall_start

    print(f"\n{'=' * 70}")
    print("📊 RÉSULTATS")
    print(f"{'=' * 70}")
    print(f"⏱️  Durée totale: {overall_duration:.1f}s")

    successful = [r for r in results if r[2]]
    if successful:
        max_time = max(r[1] for r in successful)
        avg_time = sum(r[1] for r in successful) / len(successful)

        print(f"   Max individuel: {max_time:.1f}s")
        print(f"   Moy individuel: {avg_time:.1f}s")

        # Efficacité du parallélisme
        efficiency = (max_time / overall_duration) * 100
        print(f"   Efficacité parallèle: {efficiency:.0f}%")

        if efficiency > 85:
            print(f"   ✅ Excellent parallélisme!")
        elif efficiency > 70:
            print(f"   ✅ Bon parallélisme")
        else:
            print(f"   ⚠️  Parallélisme limité")

        # Gain de temps
        sequential_time = sum(r[1] for r in successful)
        time_saved = sequential_time - overall_duration
        print(f"\n   💰 Gain: {time_saved:.1f}s économisées ({time_saved / sequential_time * 100:.0f}%)")


def main():
    print("\n🧪 TESTS LOCAUX - PRODUCTION-LIKE")
    print("Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Attendre que l'API soit disponible
    print("\n⏳ Vérification de l'API...")
    if not wait_for_api(max_retries=10, delay=2):
        print("\n❌ API non accessible après 20 secondes")
        print("   Vérifiez que l'API tourne: python scripts/run_api.py")
        return

    print("✅ API accessible\n")

    # Menu
    print("Choisissez le test:")
    print("1. Test simple (1 route, 2 mois)")
    print("2. Test parallèle (3 routes, 1 mois chacune)")
    print("3. Les deux")

    choice = input("\nVotre choix (1, 2 ou 3): ").strip()

    if choice == "1":
        test_long_scraping()
    elif choice == "2":
        test_parallel_long()
    elif choice == "3":
        test_long_scraping()
        time.sleep(2)
        test_parallel_long()
    else:
        print("❌ Choix invalide")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
        input("\n⏸️  Appuyez sur ENTRÉE...")
    except KeyboardInterrupt:
        print("\n⏹️  Interrompu")