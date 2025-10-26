"""
Scraper du calendrier des prix Google Flights - Version Production
Basé sur l'approche "scroll direct" vers les mois cibles
"""

import time
import random
import re
from datetime import datetime, date
from typing import Dict, Optional, List, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from ..core.driver_manager import DriverManager
from ..core.config import settings
from ..core.exceptions import (
    CalendarNotFoundError,
    PriceExtractionError,
    PageLoadError
)
from ..utils.logger import get_logger
from ..utils.validators import Validators

logger = get_logger(__name__)


class CalendarScraper:
    """
    Scraper pour récupérer tous les prix du calendrier Google Flights
    Utilise une approche de navigation intelligente vers les mois cibles
    """

    # Mapping des noms de mois français
    MONTHS_FR_ALIASES = {
        "janvier": 1, "janv": 1, "janv.": 1,
        "février": 2, "fevrier": 2, "févr": 2, "févr.": 2, "fevr": 2, "fevr.": 2,
        "mars": 3,
        "avril": 4, "avr": 4, "avr.": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7, "juil": 7, "juil.": 7,
        "août": 8, "aout": 8,
        "septembre": 9, "sept": 9, "sept.": 9,
        "octobre": 10, "oct": 10, "oct.": 10,
        "novembre": 11, "nov": 11, "nov.": 11,
        "décembre": 12, "decembre": 12, "déc": 12, "déc.": 12, "dec": 12, "dec.": 12,
    }

    MONTHS_FR_LONG = [
        'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
        'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'
    ]

    def __init__(self, headless: Optional[bool] = None):
        """
        Initialise le scraper

        Args:
            headless: Mode headless (None = utiliser config)
        """
        self.driver_manager = DriverManager(headless=headless)
        self.driver = None
        self.wait = None

    # ==================== UTILITIES ====================

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
                logger.debug(f"Screenshot sauvegardée: {filename}")
            except Exception as e:
                logger.debug(f"Erreur screenshot: {e}")

    def _month_num(self, name: str) -> int:
        """Convertit un nom de mois en numéro (1-12)"""
        key = name.strip().lower()
        if key in self.MONTHS_FR_ALIASES:
            return self.MONTHS_FR_ALIASES[key]
        # Fallback
        try:
            return self.MONTHS_FR_LONG.index(key) + 1
        except ValueError:
            raise ValueError(f"Nom de mois invalide: {name}")

    def _month_name(self, num: int) -> str:
        """Convertit un numéro de mois (1-12) en nom"""
        if not 1 <= num <= 12:
            raise ValueError(f"Numéro de mois invalide: {num}")
        return self.MONTHS_FR_LONG[num - 1]

    def _build_url(self, origin: str, destination: str) -> str:
        """Construit l'URL Google Flights"""
        url = f"https://www.google.com/travel/flights?q=Flights+from+{origin}+to+{destination}"
        url += "&curr=EUR&hl=fr"
        return url

    # ==================== POPUPS & CONSENT ====================

    def _handle_consent(self):
        """Gère la page de consentement Google"""
        try:
            if "consent.google.com" in self.driver.current_url:
                logger.debug("Gestion du consentement Google...")
                btn = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[.//span[contains(text(), 'Tout accepter')]]")
                    )
                )
                btn.click()
                time.sleep(2)
                logger.debug("✓ Consentement accepté")
        except Exception as e:
            logger.debug(f"Pas de page de consentement ou erreur: {e}")

    def _handle_popups(self):
        """Ferme les popups de cookies sur la page principale"""
        selectors = [
            "button[aria-label*='Tout accepter']",
            "button[aria-label*='Accept all']",
            "//button[contains(text(), 'Accepter')]",
        ]

        for selector in selectors:
            try:
                if selector.startswith('//'):
                    button = self.driver.find_element(By.XPATH, selector)
                else:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                button.click()
                logger.debug("✓ Popup cookies fermé")
                self._random_delay(1, 2)
                return True
            except:
                continue
        return False

    # ==================== CALENDAR NAVIGATION ====================

    def _open_calendar(self) -> bool:
        """Ouvre le calendrier en cliquant sur le champ Départ"""
        logger.debug("Ouverture du calendrier...")

        selectors = [
            "input[aria-label*='Départ']",
            "input[placeholder*='Départ']",
            "button[aria-label*='Départ']",
        ]

        for selector in selectors:
            try:
                element = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", element
                )
                time.sleep(0.5)
                element.click()
                logger.debug("✓ Calendrier ouvert")
                time.sleep(2.0)
                return True
            except:
                continue

        logger.warning("Impossible d'ouvrir le calendrier")
        return False

    def _click_prev_button(self) -> bool:
        """Clique sur le bouton Précédent du calendrier"""
        try:
            btns = self.driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//button[contains(@class,'a2rVxf') and @aria-label='Précédent']"
            )
            for b in btns:
                if b.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", b
                    )
                    time.sleep(0.15)
                    self.driver.execute_script("arguments[0].click();", b)
                    return True
            return False
        except Exception as e:
            logger.debug(f"Erreur clic Précédent: {e}")
            return False

    def _click_next_button(self) -> bool:
        """Clique sur le bouton Suivant du calendrier"""
        try:
            btns = self.driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//button[contains(@class,'a2rVxf') and @aria-label='Suivant']"
            )
            for b in btns:
                if b.is_displayed():
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", b
                    )
                    time.sleep(0.15)
                    self.driver.execute_script("arguments[0].click();", b)
                    return True
            return False
        except Exception as e:
            logger.debug(f"Erreur clic Suivant: {e}")
            return False

    # ==================== MONTH DETECTION ====================

    def _get_month_groups(self) -> List[Dict]:
        """
        Récupère tous les blocs mois présents dans le calendrier
        
        Returns:
            Liste de dicts avec year, month_num, header_text, group_el, header_el
        """
        groups = self.driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//div[@jsname='RAZSvb']"
            "//div[@role='rowgroup' and contains(@class,'Bc6Ryd')]"
        )

        result = []
        for g in groups:
            try:
                # Header du mois (ex: "novembre" ou "janvier 2026")
                header_el = g.find_element(By.CSS_SELECTOR, ".BgYkof.B5dqIf.qZwLKe")
            except:
                continue

            header_text = header_el.text.strip()

            # Trouver une cellule avec data-iso pour extraire année/mois réels
            day_cells = g.find_elements(By.CSS_SELECTOR, "[data-iso]")
            year_val = None
            month_val = None

            for cell in day_cells:
                iso = cell.get_attribute("data-iso") or ""
                match = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
                if match:
                    year_val = int(match.group(1))
                    month_val = int(match.group(2))
                    break

            if year_val is None:
                continue

            result.append({
                "year": year_val,
                "month_num": month_val,
                "header_text": header_text,
                "group_el": g,
                "header_el": header_el,
            })

        return result

    def _focus_on_month(self, target_month_name: str, target_year: int, max_attempts: int = 60) -> bool:
        """
        Navigue vers le mois cible (scroll ou clic Suivant/Précédent)
        
        Args:
            target_month_name: Nom du mois (ex: "novembre")
            target_year: Année (ex: 2025)
            max_attempts: Nombre max de tentatives
            
        Returns:
            True si le mois est trouvé et affiché
        """
        target_num = self._month_num(target_month_name)
        target_total = target_year * 12 + target_num

        logger.debug(f"Navigation vers {target_month_name} {target_year}...")

        for attempt in range(max_attempts):
            groups = self._get_month_groups()

            # Le mois est-il déjà visible ?
            for g in groups:
                if g["year"] == target_year and g["month_num"] == target_num:
                    logger.debug(f"✓ Mois {target_month_name} {target_year} trouvé (attempt {attempt})")
                    # Scroll pour s'assurer qu'il est visible et que les prix se chargent
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'start'});",
                        g["header_el"]
                    )
                    time.sleep(0.8)
                    return True

            # Sinon, on doit charger plus de mois
            months_loaded = [x["year"] * 12 + x["month_num"] for x in groups]
            if not months_loaded:
                logger.debug("Aucun mois détecté, retry...")
                time.sleep(0.5)
                continue

            min_loaded = min(months_loaded)
            max_loaded = max(months_loaded)

            if target_total < min_loaded:
                # Mois plus ancien → Précédent
                logger.debug("← Clic Précédent pour charger mois plus anciens")
                if not self._click_prev_button():
                    logger.warning("Échec clic Précédent")
                    return False
                time.sleep(1.0)
                continue

            if target_total > max_loaded:
                # Mois plus récent → Suivant
                logger.debug("→ Clic Suivant pour charger mois plus récents")
                if not self._click_next_button():
                    logger.warning("Échec clic Suivant")
                    return False
                time.sleep(1.0)
                continue

            # Target entre min et max mais pas encore rendu
            # Scroll vers le plus proche pour forcer le render
            closest = min(
                groups,
                key=lambda g: abs((g["year"] * 12 + g["month_num"]) - target_total)
            )
            logger.debug("Scroll vers mois proche pour forcer render...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'start'});",
                closest["header_el"]
            )
            time.sleep(0.8)

        logger.warning(f"Impossible d'afficher {target_month_name} {target_year} après {max_attempts} tentatives")
        return False

    # ==================== PRICE EXTRACTION ====================

    def _get_grid_cells(self) -> List[WebElement]:
        """Récupère toutes les cellules jour visibles dans le calendrier"""
        cells = self.driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//*[@role='gridcell' and @data-iso]"
        )

        visible_cells = []
        for cell in cells:
            if not cell.is_displayed():
                continue
            # Ignorer les jours masqués (aria-hidden="true")
            aria_hidden = (cell.get_attribute("aria-hidden") or "").lower()
            if aria_hidden == "true":
                continue
            iso = (cell.get_attribute("data-iso") or "").strip()
            if not iso:
                continue
            visible_cells.append(cell)

        return visible_cells

    def _parse_iso_date(self, cell: WebElement) -> Optional[datetime]:
        """Parse la date ISO d'une cellule (data-iso="2025-11-12")"""
        iso = cell.get_attribute("data-iso") or ""
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
        if not match:
            return None
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def _extract_day_and_price(self, cell: WebElement) -> Tuple[Optional[int], Optional[float]]:
        """
        Extrait le jour et le prix d'une cellule
        
        Returns:
            (jour, prix) ou (None, None) si échec
        """
        try:
            # Structure typique:
            # <div jsname="nEWxA">12</div>  (le jour)
            # <div jsname="qCDwBb">€179</div>  (le prix)
            day_el = cell.find_element(By.CSS_SELECTOR, "[jsname='nEWxA']")
            price_el = cell.find_element(By.CSS_SELECTOR, "[jsname='qCDwBb']")
            day_txt = day_el.text.strip()
            price_txt = price_el.text.strip()
        except:
            # Fallback: split du texte brut
            raw = (cell.text or "").strip().split("\n")
            raw = [x.strip() for x in raw if x.strip()]
            if len(raw) < 2:
                return (None, None)
            day_txt, price_txt = raw[0], raw[1]

        # Valider le jour
        if not day_txt.isdigit():
            return (None, None)
        day = int(day_txt)

        # Extraire le prix (garder uniquement les chiffres)
        digits = "".join(ch for ch in price_txt if ch.isdigit())
        if not digits:
            return (None, None)
        price = float(digits)

        return (day, price)

    def _wait_prices_ready(self, target_month: str, target_year: int,
                          min_cells: int = 4, timeout: float = 7.0) -> bool:
        """
        Attend que le mois ait au moins quelques cellules avec prix
        """
        target_num = self._month_num(target_month)
        deadline = time.time() + timeout

        while time.time() < deadline:
            ready_count = 0
            for cell in self._get_grid_cells():
                dt = self._parse_iso_date(cell)
                if not dt or dt.year != target_year or dt.month != target_num:
                    continue

                # Vérifier qu'il y a un prix
                try:
                    price_el = cell.find_element(By.CSS_SELECTOR, "[jsname='qCDwBb']")
                    price_txt = price_el.text.strip()
                except:
                    raw_lines = (cell.text or "").strip().split("\n")
                    price_txt = raw_lines[-1] if raw_lines else ""

                if any(ch.isdigit() for ch in price_txt):
                    ready_count += 1

            if ready_count >= min_cells:
                return True

            time.sleep(0.25)

        return False

    def _extract_prices_for_month(self, target_month: str, target_year: int) -> Dict[str, float]:
        """
        Extrait tous les prix d'un mois spécifique
        
        Args:
            target_month: Nom du mois (ex: "novembre")
            target_year: Année (ex: 2025)
            
        Returns:
            Dict {date: prix} (ex: {"2025-11-15": 179.0, ...})
        """
        logger.debug(f"Extraction des prix pour {target_month} {target_year}...")

        # Attendre que les prix soient chargés
        if not self._wait_prices_ready(target_month, target_year, min_cells=4, timeout=7.0):
            logger.warning(f"Peu de cellules avec prix détectées pour {target_month} {target_year}")

        target_num = self._month_num(target_month)
        prices = {}

        for cell in self._get_grid_cells():
            dt = self._parse_iso_date(cell)
            if not dt or dt.year != target_year or dt.month != target_num:
                continue

            day_int, price_val = self._extract_day_and_price(cell)
            if day_int is None or price_val is None:
                continue

            # Formater la date en ISO (YYYY-MM-DD)
            date_key = f"{target_year:04d}-{target_num:02d}-{day_int:02d}"
            prices[date_key] = price_val

        logger.debug(f"✓ {len(prices)} prix extraits pour {target_month} {target_year}")
        return prices

    # ==================== MAIN SCRAPE METHOD ====================

    def scrape(
        self,
        origin: str,
        destination: str,
        months_ahead: int = 3
    ) -> Dict[str, float]:
        """
        Scrape les prix du calendrier Google Flights
        
        Args:
            origin: Code IATA aéroport de départ
            destination: Code IATA aéroport d'arrivée
            months_ahead: Nombre de mois à scraper à partir d'aujourd'hui
            
        Returns:
            Dict {date: prix} (ex: {"2025-11-15": 179.0, ...})
            
        Raises:
            CalendarNotFoundError: Si le calendrier n'est pas accessible
            PageLoadError: Si la page ne charge pas
            PriceExtractionError: Si l'extraction échoue
        """
        # Validation des inputs
        origin, destination = Validators.validate_route(origin, destination)
        months_ahead = Validators.validate_months_ahead(months_ahead)

        all_prices = {}

        try:
            # Initialiser le WebDriver
            self.driver = self.driver_manager.create_driver()
            self.wait = self.driver_manager.wait

            # Charger la page Google Flights
            url = self._build_url(origin, destination)
            logger.info(f"🌐 Navigation: {origin} → {destination}")
            logger.debug(f"URL: {url}")

            self.driver.get(url)
            time.sleep(5)

            # Gérer les popups de consentement
            self._handle_consent()
            time.sleep(1)

            # Gérer les popups de cookies
            self._handle_popups()
            time.sleep(1)

            # Ouvrir le calendrier
            logger.info("📅 Ouverture du calendrier...")
            if not self._open_calendar():
                self._save_screenshot("calendar_not_opened")
                raise CalendarNotFoundError("Impossible d'ouvrir le calendrier")

            self._save_screenshot("calendar_opened")

            # Déterminer les mois cibles
            today = date.today()
            target_months = []
            for i in range(months_ahead):
                target_date = date(
                    today.year + (today.month + i - 1) // 12,
                    (today.month + i - 1) % 12 + 1,
                    1
                )
                month_name = self._month_name(target_date.month)
                target_months.append((month_name, target_date.year))

            logger.info(f"📊 Mois cibles: {', '.join([f'{m} {y}' for m, y in target_months])}")

            # Scanner chaque mois
            for idx, (month_name, year) in enumerate(target_months, 1):
                logger.info(f"📊 Mois {idx}/{len(target_months)}: {month_name} {year}")

                # Naviguer vers le mois
                if not self._focus_on_month(month_name, year):
                    logger.warning(f"⚠️ Impossible d'afficher {month_name} {year}, skip")
                    continue

                # Screenshot du mois
                safe_month = month_name.replace(" ", "_")
                self._save_screenshot(f"month_{idx}_{safe_month}_{year}")

                # Extraire les prix
                month_prices = self._extract_prices_for_month(month_name, year)
                all_prices.update(month_prices)

                time.sleep(0.5)

            # Résumé des résultats
            if all_prices:
                prices_list = list(all_prices.values())
                logger.info(f"✅ {len(all_prices)} prix récupérés au total")
                logger.info(f"   Min: {min(prices_list):.0f}€")
                logger.info(f"   Max: {max(prices_list):.0f}€")
                logger.info(f"   Moyenne: {sum(prices_list)/len(prices_list):.0f}€")
            else:
                logger.warning("⚠️ Aucun prix trouvé")
                self._save_screenshot("no_prices_found")

        except CalendarNotFoundError:
            raise
        except PriceExtractionError:
            raise
        except Exception as e:
            logger.error(f"❌ Erreur lors du scraping: {e}", exc_info=True)
            self._save_screenshot("scraping_error")
            raise PageLoadError(f"Erreur lors du scraping: {e}")
        finally:
            self.close()

        return all_prices

    def close(self):
        """Ferme proprement le WebDriver"""
        if self.driver_manager:
            self.driver_manager.close()
            self.driver = None
            self.wait = None
