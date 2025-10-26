# src/core/driver_manager.py - MODIFIER pour Windows + Linux

import random
import time
import platform
from typing import Optional
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait

from ..core.config import settings
from ..core.exceptions import DriverInitializationError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DriverManager:
    """Gestionnaire du WebDriver - compatible Windows + Linux"""

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(self, headless: Optional[bool] = None):
        self.headless = headless if headless is not None else settings.headless
        self.driver = None
        self.wait = None
        self.is_windows = platform.system() == 'Windows'

        logger.info(f"DriverManager - OS: {platform.system()}, Headless: {self.headless}")

    def create_driver(self):
        """Crée un driver avec anti-détection"""
        try:
            options = Options()
            self._configure_stealth_options(options)

            # Déterminer le chemin du driver selon l'OS
            if self.is_windows:
                # Windows: utiliser le driver local ou webdriver-manager
                driver_path = Path("drivers/chromedriver.exe")
                if driver_path.exists():
                    logger.info(f"Utilisation driver local: {driver_path}")
                    service = Service(str(driver_path))
                else:
                    logger.info("Utilisation webdriver-manager")
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
            else:
                # Linux/Docker: chemin standard
                logger.info("Linux détecté - driver à /usr/local/bin/chromedriver")
                service = Service('/usr/local/bin/chromedriver')

            # Créer le driver
            self.driver = webdriver.Chrome(service=service, options=options)

            # Scripts anti-détection
            self._inject_stealth_scripts()

            # Wait avec timeout augmenté
            self.wait = WebDriverWait(self.driver, settings.timeout)

            logger.info("✓ WebDriver créé avec succès")
            return self.driver

        except Exception as e:
            logger.error(f"❌ Erreur création driver: {e}")
            raise DriverInitializationError(f"Impossible de créer le driver: {e}")

    def _configure_stealth_options(self, options: Options):
        """Configure les options stealth"""

        # User agent
        if settings.random_user_agent:
            user_agent = random.choice(self.USER_AGENTS)
        else:
            user_agent = self.USER_AGENTS[0]

        options.add_argument(f'user-agent={user_agent}')
        logger.debug(f"User agent: {user_agent[:50]}...")

        # Anti-détection CRITIQUES
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Performance
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')

        # Désactiver les logs Chrome verbeux
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # Langue
        options.add_argument('--lang=fr-FR')
        options.add_experimental_option('prefs', {
            'intl.accept_languages': 'fr-FR,fr,en-US,en',
            'profile.default_content_setting_values.notifications': 2,
            'profile.managed_default_content_settings.images': 1,
        })

        # Headless
        if self.headless:
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            logger.info("Mode headless activé")

        # Proxy
        if settings.use_proxy and settings.proxy_url:
            options.add_argument(f'--proxy-server={settings.proxy_url}')
            logger.info(f"Proxy: {settings.proxy_url}")

    def _inject_stealth_scripts(self):
        """Injecte les scripts anti-détection"""
        if not self.driver:
            return

        try:
            # Script 1: Masquer webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })

            # Script 2: Plugins
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                '''
            })

            # Script 3: Languages
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['fr-FR', 'fr', 'en-US', 'en']
                    });
                '''
            })

            # Script 4: Chrome runtime
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    window.chrome = {
                        runtime: {}
                    };
                '''
            })

            # Script 5: Permissions
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                '''
            })

            logger.debug("✓ Scripts anti-détection injectés")

        except Exception as e:
            logger.warning(f"Erreur injection scripts: {e}")

    def simulate_human_behavior(self):
        """Simule un comportement humain"""
        if not settings.simulate_human or not self.driver:
            return

        try:
            # Scroll aléatoire
            scroll_y = random.randint(100, 500)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_y});")
            time.sleep(random.uniform(0.5, 1.5))

            # Scroll retour partiel
            self.driver.execute_script(f"window.scrollBy(0, -{scroll_y // 2});")
            time.sleep(random.uniform(0.3, 0.8))

        except Exception as e:
            logger.debug(f"Erreur simulation: {e}")

    def close(self):
        """Ferme le driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("✓ Driver fermé")
            except:
                pass
            finally:
                self.driver = None
                self.wait = None