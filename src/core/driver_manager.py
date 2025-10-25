"""
Gestionnaire robuste du WebDriver avec gestion automatique de ChromeDriver
"""

import random
from typing import Optional
from contextlib import contextmanager
from selenium import webdriver

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from src.core.config import settings
from src.core.exceptions import DriverInitializationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DriverManager:
    """Gestionnaire centralisé du WebDriver"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, headless: Optional[bool] = None):
        """
        Initialise le gestionnaire
        
        Args:
            headless: Mode headless (None = utiliser config)
        """
        self.headless = headless if headless is not None else settings.headless
        self.driver = None
        self.wait = None
        
        logger.info(f"DriverManager initialisé - Headless: {self.headless}")
        logger.info(f"Undetected ChromeDriver disponible: {UNDETECTED_AVAILABLE}")
    
    def create_driver(self):
        """
        Crée et configure un WebDriver
        
        Returns:
            WebDriver configuré
            
        Raises:
            DriverInitializationError: Si l'initialisation échoue
        """
        try:
            if UNDETECTED_AVAILABLE:
                logger.debug("Utilisation d'undetected-chromedriver")
                self.driver = self._create_undetected_driver()
            else:
                logger.debug("Utilisation de Selenium standard")
                self.driver = self._create_standard_driver()
            
            self.wait = WebDriverWait(self.driver, settings.timeout)
            logger.info("✓ WebDriver créé avec succès")
            
            return self.driver
            
        except Exception as e:
            logger.error(f"✗ Erreur création WebDriver: {e}")
            raise DriverInitializationError(
                f"Impossible de créer le WebDriver: {e}",
                details={"error": str(e)}
            )
    
    def _create_undetected_driver(self):
        """Crée un driver avec undetected-chromedriver"""
        options = uc.ChromeOptions()
        self._configure_options(options)
        
        try:
            driver = uc.Chrome(
                options=options,
                version_main=120,  # Version de Chrome
                use_subprocess=True
            )
            return driver
        except Exception as e:
            logger.warning(f"Erreur avec undetected-chromedriver: {e}")
            logger.info("Fallback vers Selenium standard")
            return self._create_standard_driver()

    def _create_standard_driver(self):
        """Crée un driver Selenium standard"""
        from pathlib import Path

        options = Options()
        self._configure_options(options)

        # Utiliser le ChromeDriver manuel
        driver_path = Path("drivers/chromedriver.exe")

        if driver_path.exists():
            logger.info(f"✓ Utilisation de ChromeDriver manuel: {driver_path}")
            service = Service(str(driver_path))
        else:
            logger.info("ChromeDriver manuel introuvable, tentative auto-install...")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)

        # Masquer la propriété webdriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        return driver
    
    def _configure_options(self, options):
        """Configure les options du driver"""
        
        # User agent aléatoire
        user_agent = random.choice(self.USER_AGENTS)
        options.add_argument(f'user-agent={user_agent}')
        
        # Options anti-détection
        options.add_argument('--disable-blink-features=AutomationControlled')
        #options.add_experimental_option("excludeSwitches", ["enable-automation"])
        #options.add_experimental_option('useAutomationExtension', False)
        
        # Options de performance
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        
        # Langue
        options.add_argument('--lang=fr-FR')
        options.add_experimental_option('prefs', {
            'intl.accept_languages': 'fr-FR,fr',
            'profile.default_content_setting_values.notifications': 2
        })
        
        # Proxy
        if settings.use_proxy and settings.proxy_url:
            options.add_argument(f'--proxy-server={settings.proxy_url}')
            logger.info(f"Proxy configuré: {settings.proxy_url}")
        
        # Mode headless
        if self.headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            logger.debug("Mode headless activé")
        else:
            logger.debug("Mode avec fenêtre visible")
    
    def close(self):
        """Ferme proprement le driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ WebDriver fermé")
            except Exception as e:
                logger.warning(f"Erreur fermeture driver: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def __enter__(self):
        """Support du context manager"""
        self.create_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fermeture automatique avec context manager"""
        self.close()
    
    @contextmanager
    def get_driver(self):
        """
        Context manager pour obtenir un driver temporaire
        
        Usage:
            with driver_manager.get_driver() as driver:
                driver.get("https://google.com")
        """
        try:
            driver = self.create_driver()
            yield driver
        finally:
            self.close()