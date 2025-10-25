"""FINAL - Gestion consent.google.com + Interception"""

import asyncio
import json
import re
from playwright.async_api import async_playwright

async def main():
    print("🔥 VERSION FINALE - Consent + Interception\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            locale='fr-FR',
            timezone_id='Europe/Brussels',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Données interceptées
        prices_data = []

        async def handle_response(response):
            try:
                url = response.url
                if ('rpc' in url or 'Flight' in url) and response.status == 200:
                    try:
                        data = await response.json()
                        prices_data.append(data)
                        print(f"🎯 Données interceptées: {len(prices_data)}")
                    except:
                        pass
            except:
                pass

        page.on("response", handle_response)

        try:
            # ÉTAPE 1: Aller sur Google Flights (redirige vers consent)
            url = "https://www.google.com/travel/flights?q=Flights%20from%20BRU%20to%20CDG&curr=EUR&hl=fr"
            print("📍 Navigation initiale...\n")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            current_url = page.url
            print(f"📄 URL actuelle: {current_url}\n")

            # ÉTAPE 2: Si on est sur consent.google.com
            if "consent.google.com" in current_url:
                print("🍪 PAGE DE CONSENTEMENT DÉTECTÉE !\n")

                # Chercher et cliquer sur "Tout accepter"
                consent_clicked = False

                # Méthode 1: Texte visible
                try:
                    # Attendre que la page charge
                    await page.wait_for_load_state("networkidle")

                    # Chercher tous les boutons
                    buttons = await page.locator("button").all()
                    print(f"Trouvé {len(buttons)} boutons\n")

                    for btn in buttons:
                        try:
                            text = await btn.inner_text()
                            if text and ('accepter' in text.lower() or 'accept' in text.lower()):
                                print(f"  ➤ Bouton: '{text}'")

                                if 'tout' in text.lower() or 'all' in text.lower():
                                    print(f"  🖱️  Clic sur: '{text}'")
                                    await btn.click()
                                    consent_clicked = True
                                    break
                        except:
                            continue

                    if consent_clicked:
                        print("✅ Consentement accepté!\n")
                        # Attendre la redirection
                        await page.wait_for_url("**/travel/flights**", timeout=10000)
                        print(f"✅ Redirigé vers: {page.url}\n")
                    else:
                        print("❌ Bouton 'Tout accepter' introuvable\n")

                        # Fallback: cliquer sur le premier bouton submit
                        try:
                            submit = page.locator("button[type='submit']").first
                            await submit.click()
                            print("✅ Cliqué sur submit (fallback)\n")
                            await page.wait_for_timeout(3000)
                        except:
                            print("⚠️  Pas de fallback possible\n")

                except Exception as e:
                    print(f"❌ Erreur consentement: {e}\n")

            else:
                print("✅ Déjà sur Google Flights (pas de consentement)\n")

            # ÉTAPE 3: On devrait être sur Google Flights maintenant
            current_url = page.url

            if "travel/flights" not in current_url:
                print("⚠️  TOUJOURS PAS SUR GOOGLE FLIGHTS\n")
                print(f"URL: {current_url}\n")
                await page.screenshot(path="screenshots/stuck.png")
                print("📸 Screenshot: stuck.png\n")
            else:
                print("🎯 SUR GOOGLE FLIGHTS !\n")

                # Attendre le chargement
                print("⏳ Chargement des données (10s)...\n")
                await page.wait_for_timeout(10000)

                # Scroll
                print("📜 Scroll...\n")
                for _ in range(3):
                    await page.keyboard.press("PageDown")
                    await page.wait_for_timeout(2000)

                # EXTRACTION
                print("💰 Extraction...\n")

                # Chercher tous les éléments avec €
                elements = await page.locator("text=/\\d+\\s*€/").all()
                print(f"Trouvé {len(elements)} prix\n")

                prices = {}

                for elem in elements[:30]:
                    try:
                        text = await elem.inner_text()

                        # Remonter pour trouver aria-label
                        current = elem
                        for _ in range(5):
                            parent = current.locator("xpath=..").first
                            aria = await parent.get_attribute("aria-label")

                            if aria and any(m in aria.lower() for m in ['janvier', 'février', 'mars', 'novembre', 'décembre']):

                                price_match = re.search(r'(\d+)\s*€', text)
                                date_match = re.search(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', aria, re.IGNORECASE)

                                if price_match and date_match:
                                    price = float(price_match.group(1))
                                    day = date_match.group(1).zfill(2)
                                    month = date_match.group(2).lower()
                                    year = date_match.group(3)

                                    months = {'janvier':'01', 'février':'02', 'mars':'03', 'avril':'04',
                                            'mai':'05', 'juin':'06', 'juillet':'07', 'août':'08',
                                            'septembre':'09', 'octobre':'10', 'novembre':'11', 'décembre':'12'}

                                    if month in months:
                                        date_str = f"{year}-{months[month]}-{day}"
                                        if date_str not in prices:
                                            prices[date_str] = price
                                            print(f"  ✅ {date_str}: {price}€")

                                break

                            current = parent

                    except:
                        continue

                # Résultats
                print(f"\n\n📊 TOTAL: {len(prices)} prix\n")

                if prices:
                    print("="*60)
                    print("🎉 PRIX EXTRAITS !")
                    print("="*60 + "\n")

                    for date, price in sorted(prices.items(), key=lambda x: x[1]):
                        print(f"{date}: {price}€")

                    with open('prices_SUCCESS.json', 'w') as f:
                        json.dump(dict(sorted(prices.items())), f, indent=2)

                    print("\n💾 prices_SUCCESS.json")
                    print(f"\n🎉🎉 RÉUSSI ! {len(prices)} PRIX ! 🎉🎉\n")
                else:
                    print("❌ Aucun prix\n")

                # Données réseau
                if prices_data:
                    with open('network_data.json', 'w') as f:
                        json.dump(prices_data, f, indent=2)
                    print(f"💾 {len(prices_data)} requêtes réseau: network_data.json\n")

                await page.screenshot(path="screenshots/final.png", full_page=True)
                print("📸 screenshots/final.png")

            input("\n⏸️  ENTRÉE...")

        finally:
            await browser.close()

asyncio.run(main())