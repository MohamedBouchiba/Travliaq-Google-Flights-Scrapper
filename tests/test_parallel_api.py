# tests/test_parallel_api.py
"""
Test de l'API avec exécution parallèle
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:8000/api/v1"


def test_single_request():
    """Test une seule requête"""
    print("\n" + "=" * 70)
    print("TEST 1: Requête unique")
    print("=" * 70)

    start = time.time()
    response = requests.get(
        f"{BASE_URL}/calendar-prices",
        params={
            "origin": "BRU",
            "destination": "CDG",
            "start_date": "2025-11-01",
            "end_date": "2025-11-30",
            "force_refresh": True
        },
        timeout=180
    )
    duration = time.time() - start

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Succès en {duration:.1f}s")
        print(f"   Prix trouvés: {data['total_dates']}")
        print(f"   Min: {data['min_price']}€, Max: {data['max_price']}€")
        return duration
    else:
        print(f"❌ Erreur: {response.status_code}")
        return None


def make_request(route_id, origin, dest, start, end):
    """Fonction pour faire une requête"""
    print(f"   [{route_id}] Démarrage: {origin}->{dest}")
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
            timeout=180
        )
        duration = time.time() - req_start

        if response.status_code == 200:
            data = response.json()
            print(f"   [{route_id}] ✅ Terminé en {duration:.1f}s - {data['total_dates']} prix")
            return (route_id, duration, True, data['total_dates'])
        else:
            print(f"   [{route_id}] ❌ Erreur {response.status_code}")
            return (route_id, duration, False, 0)

    except Exception as e:
        duration = time.time() - req_start
        print(f"   [{route_id}] ❌ Exception: {e}")
        return (route_id, duration, False, 0)


def test_parallel_requests():
    """Test plusieurs requêtes en parallèle"""
    print("\n" + "=" * 70)
    print("TEST 2: Requêtes parallèles (3 routes simultanées)")
    print("=" * 70)

    routes = [
        ("R1", "BRU", "CDG", "2025-11-01", "2025-11-30"),
        ("R2", "AMS", "BCN", "2025-11-01", "2025-11-30"),
        ("R3", "CDG", "LHR", "2025-11-01", "2025-11-30"),
    ]

    print("\n🚀 Lancement des 3 requêtes en parallèle...")
    overall_start = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(make_request, *route)
            for route in routes
        ]

        results = []
        for future in as_completed(futures):
            results.append(future.result())

    overall_duration = time.time() - overall_start

    print(f"\n📊 Résultats:")
    print(f"   Durée totale: {overall_duration:.1f}s")

    successful = [r for r in results if r[2]]
    if successful:
        avg_duration = sum(r[1] for r in successful) / len(successful)
        print(f"   Durée moyenne par route: {avg_duration:.1f}s")
        print(f"   Efficacité parallèle: {avg_duration / overall_duration * 100:.0f}%")

    total_prices = sum(r[3] for r in results)
    print(f"   Total prix récupérés: {total_prices}")

    success_rate = len(successful) / len(results) * 100
    print(f"   Taux de réussite: {success_rate:.0f}%")

    # Le temps total doit être proche du temps d'une seule requête
    # (et non 3x plus long)
    return overall_duration


def main():
    print("\n🧪 TEST SUITE - API Parallèle")

    # Test 1: Une seule requête
    single_duration = test_single_request()

    if not single_duration:
        print("\n❌ Test unique échoué, arrêt")
        return

    # Test 2: Requêtes parallèles
    parallel_duration = test_parallel_requests()

    # Analyse
    print("\n" + "=" * 70)
    print("📈 ANALYSE")
    print("=" * 70)
    print(f"Durée 1 requête: {single_duration:.1f}s")
    print(f"Durée 3 requêtes en parallèle: {parallel_duration:.1f}s")

    if parallel_duration < single_duration * 2:
        print("\n✅ Exécution parallèle fonctionnelle!")
        print(f"   Gain: {(single_duration * 3 - parallel_duration):.1f}s économisées")
    else:
        print("\n⚠️  Parallélisation peu efficace")

    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
        input("\n⏸️  Appuyez sur ENTRÉE...")
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrompu")