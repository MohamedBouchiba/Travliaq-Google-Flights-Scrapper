"""
Scraper du calendrier des prix Google Flights - Version Production
"""

import time
import random
import re
from datetime import datetime
from typing import Dict, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.core.driver_manager import DriverManager
from src.core.config import settings
from src.core.exceptions import (
    CalendarNotFoundError,
    PriceExtractionError,
    PageLoadError
)
from src.utils.logger import get_logger
from src.utils.validators import Validators

logger = get_logger(__name__)


class CalendarScraper:
    """Scraper pour récupérer tous les prix du calendrier"""

    # Sélecteurs CSS pour les éléments du calendrier
    SELECTORS = {
        'date_picker_button': [
            'button[aria-label*="Départ"]',
            'input[placeholder*="Départ"]',
            'button[jsname="oYxtQd"]',
            '//button[contains(@aria-label, "Départ")]',
        ],
        'calendar_days': [
            'div[data-iso]',
            'button[data-iso]',
            'div[jsname][role="button"]',
            'div.sSHqwe',
        ],
        'next_month_button': [
            'button[aria-label*="Mois suivant"]',
            'button[aria-label*="Next month"]',
            '//button[contains(@aria-label, "suivant")]',
        ],
        'popup_accept': [
            "button[aria-label*='Tout accepter']",
            "button[aria-label*='Accept all']",
            "//button[contains(text(), 'Accepter')]",
        ]
    }

    def __init__(self, headless: Optional[bool] = None):
        """
        Initialise le scraper

        Args:
            headless: Mode headless (None = utiliser config)
        """
        self.driver_manager = DriverManager(headless=headless)
        self.driver = None
        self.wait = None

    def _random_delay(self, min_sec: float = None, max_sec: float = None):
        """Délai aléatoire pour simuler comportement humain"""
        min_sec = min_sec or settings.delay_between_requests_min
        max_sec = max_sec or settings.delay_between_requests_max
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _save_screenshot(self, name: str = "error"):
        """Sauvegarde une capture d'écran"""
        if settings.screenshot_on_error and self.driver:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = settings.screenshots_dir / f"{name}_{timestamp}.png"
                self.driver.save_screenshot(str(filename))
                logger.debug(f"Screenshot: {filename}")
            except Exception as e:
                logger.debug(f"Erreur screenshot: {e}")

    def _handle_popups(self):
        """Ferme les popups de cookies"""
        for selector in self.SELECTORS['popup_accept']:
            try:
                if selector.startswith('//'):
                    button = self.driver.find_element(By.XPATH, selector)
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                button.click()
                logger.debug("Popup fermé")
                self._random_delay(1, 2)
                return True
            except:
                continue
        return False

    def _build_url(self, origin: str, destination: str) -> str:
        """Construit l'URL Google Flights"""
        url = f"https://www.google.com/travel/flights?q=Flights%20from%20{origin}%20to%20{destination}"
        url += "&curr=EUR&hl=fr"
        return url

    def _click_date_picker(self) -> bool:
        """Ouvre le sélecteur de dates"""
        for selector in self.SELECTORS['date_picker_button']:
            try:
                if selector.startswith('//'):
                    element = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    element = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )

                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                self._random_delay(0.5, 1)
                element.click()
                logger.debug("✓ Date picker ouvert")
                self._random_delay(2, 3)
                return True

            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Erreur clic date picker: {e}")
                continue

        logger.warning("Date picker non trouvé")
        return False

    def _extract_calendar_prices(self) -> Dict[str, float]:
        """Extrait tous les prix du calendrier visible"""
        prices_data = {}

        try:
            self._random_delay(2, 3)

            # Chercher les jours avec prix
            days_elements = []
            for selector in self.SELECTORS['calendar_days']:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 10:
                        days_elements = elements
                        logger.debug(f"✓ {len(elements)} jours trouvés")
                        break
                except:
                    continue

            if not days_elements:
                logger.warning("Aucun jour trouvé dans le calendrier")
                return prices_data

            # Extraire prix de chaque jour
            for day_element in days_elements:
                try:
                    # Date (data-iso ou aria-label)
                    date_str = day_element.get_attribute('data-iso')

                    if not date_str:
                        # Fallback: extraire depuis aria-label
                        aria_label = day_element.get_attribute('aria-label')
                        if aria_label:
                            date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', aria_label)
                            if date_match:
                                date_str = date_match.group(0)

                    if not date_str:
                        continue

                    # Prix
                    text = day_element.text
                    price = self._extract_price(text)

                    if price and date_str:
                        prices_data[date_str] = price

                except Exception as e:
                    logger.debug(f"Erreur extraction jour: {e}")
                    continue

            logger.debug(f"✓ {len(prices_data)} prix extraits")

        except Exception as e:
            logger.error(f"Erreur extraction calendrier: {e}")
            raise PriceExtractionError(f"Impossible d'extraire les prix: {e}")

        return prices_data

    def _extract_price(self, text: str) -> Optional[float]:
        """Extrait le prix d'un texte"""
        patterns = [
            r'€\s*(\d+[\s]?\d*)',
            r'(\d+[\s]?\d*)\s*€',
            r'\$(\d+[\s]?\d*)',
            r'(\d+[\s]?\d*)\s*EUR',
        ]

        # Nettoyer le texte
        clean_text = text.replace(',', '').replace(' ', '')

        for pattern in patterns:
            match = re.search(pattern, clean_text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    continue
        return None

    def _navigate_next_month(self) -> bool:
        """Navigue vers le mois suivant"""
        for selector in self.SELECTORS['next_month_button']:
            try:
                if selector.startswith('//'):
                    button = self.driver.find_element(By.XPATH, selector)
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)

                button.click()
                logger.debug("→ Mois suivant")
                self._random_delay(2, 3)
                return True

            except:
                continue

        # Fallback: chercher toutes les flèches
        try:
            arrows = self.driver.find_elements(By.CSS_SELECTOR, 'button[jsname]')
            if len(arrows) >= 2:
                arrows[-1].click()
                logger.debug("→ Mois suivant (fallback)")
                self._random_delay(2, 3)
                return True
        except:
            pass

        return False

    def scrape(
        self,
        origin: str,
        destination: str,
        months_ahead: int = 3
    ) -> Dict[str, float]:
        """
        Scrape les prix du calendrier

        Args:
            origin: Code IATA départ
            destination: Code IATA arrivée
            months_ahead: Nombre de mois à scraper (1-12)

        Returns:
            Dict {date: prix}

        Raises:
            CalendarNotFoundError: Si le calendrier n'est pas accessible
            PageLoadError: Si la page ne charge pas
        """
        # Validation
        origin, destination = Validators.validate_route(origin, destination)
        months_ahead = Validators.validate_months_ahead(months_ahead)

        all_prices = {}

        try:
            # Initialiser driver
            self.driver = self.driver_manager.create_driver()
            self.wait = self.driver_manager.wait

            # Charger la page
            url = self._build_url(origin, destination)
            logger.info(f"🌐 Navigation: {origin} → {destination}")

            self.driver.get(url)
            self._random_delay(3, 5)

            # Gérer popups
            self._handle_popups()
            self._random_delay(2, 3)

            # Ouvrir calendrier
            logger.info("📅 Ouverture du calendrier...")
            if not self._click_date_picker():
                self._save_screenshot("calendar_not_opened")
                raise CalendarNotFoundError("Impossible d'ouvrir le calendrier")

            # Scanner chaque mois
            for month_index in range(months_ahead):
                logger.info(f"📊 Scan mois {month_index + 1}/{months_ahead}")

                month_prices = self._extract_calendar_prices()
                all_prices.update(month_prices)

                # Naviguer au mois suivant
                if month_index < months_ahead - 1:
                    if not self._navigate_next_month():
                        logger.warning("Impossible de naviguer au mois suivant")
                        break

            # Résumé
            if all_prices:
                prices = list(all_prices.values())
                logger.info(f"✅ {len(all_prices)} prix récupérés")
                logger.info(f"   Min: {min(prices)}€ | Max: {max(prices)}€ | Moy: {sum(prices)/len(prices):.2f}€")
            else:
                logger.warning("Aucun prix trouvé")
                self._save_screenshot("no_prices")

        except CalendarNotFoundError:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur scraping: {e}")
            self._save_screenshot("scraping_error")
            raise PageLoadError(f"Erreur lors du scraping: {e}")
        finally:
            self.close()

        return all_prices

    def close(self):
        """Ferme le driver"""
        if self.driver_manager:
            self.driver_manager.close()
            self.driver = None
            self.wait = None