"""
🎯 SCRAPER GOOGLE FLIGHTS CALENDRIER — SCROLL DIRECT SUR LE MOIS CIBLE
Route BRU->CDG
Objectif: récupérer les prix pour novembre 2025 et décembre 2025
sans partir en 2026 ni cliquer en boucle comme un sauvage.

Idée clé:
- On ouvre le calendrier (le sélecteur de dates avec les prix par jour).
- On récupère TOUS les blocs "mois" déjà chargés dans le DOM.
- Pour chaque mois on lit la vraie année/mois via data-iso="YYYY-MM-DD".
- On scrolle directement sur le mois demandé -> pas besoin de spammer "Suivant".
- On extrait les prix jour par jour.

Bonus:
- Si un jour tu demandes un mois pas encore chargé dans le DOM,
  on cliquera "Suivant" ou "Précédent" pour charger plus de mois,
  mais pour novembre/décembre 2025 ce n'est pas nécessaire.
"""

import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, 'src')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================================#
# CONFIG
# ============================================================================#

ORIGIN = "CDG"
DESTINATION = "NCL"

TARGET_MONTHS = [
    ("septembre", 2026),
    ("décembre", 2025),
    ("janvier", 2026),
]

print("="*70)
print("🎯 SCRAPER GOOGLE FLIGHTS CALENDRIER — SCROLL DIRECT SUR LE MOIS CIBLE")
print("="*70 + "\n")
print(f"📍 Route: {ORIGIN} → {DESTINATION}")
print("📅 Mois cibles:")
for m, y in TARGET_MONTHS:
    print(f"   - {m} {y}")
print()

# ============================================================================#
# SELENIUM
# ============================================================================#

driver_path = Path("drivers/chromedriver.exe")

options = Options()
options.add_argument("--lang=fr-FR")
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-logging"])

service = Service(str(driver_path))
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

Path("screenshots").mkdir(parents=True, exist_ok=True)

# ============================================================================#
# UTIL MOIS
# ============================================================================#

MONTHS_FR_ALIASES = {
    "janvier": 1, "janv": 1, "janv.": 1,
    "février": 2, "fevrier": 2, "févr": 2, "févr.": 2, "fevr": 2, "fevr.": 2,
    "mars": 3,
    "avril": 4, "avr": 4, "avr.": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
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

def _month_num(name: str) -> int:
    key = name.strip().lower()
    if key in MONTHS_FR_ALIASES:
        return MONTHS_FR_ALIASES[key]
    # fallback
    return MONTHS_FR_LONG.index(key) + 1

def _month_name(num: int) -> str:
    return MONTHS_FR_LONG[num - 1]

# ============================================================================#
# LOW LEVEL HELPERS
# ============================================================================#

def handle_consent():
    # Accepte la bannière cookies si elle apparaît
    try:
        if "consent.google.com" in driver.current_url:
            print("🍪 Consentement...")
            btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), 'Tout accepter')]]")
            ))
            btn.click()
            time.sleep(2)
            print("✅ Accepté\n")
    except:
        pass

def open_calendar():
    """
    Ouvre le calendrier en cliquant sur le champ 'Départ'.
    C'est ce calendrier-là qui contient tous les mois avec les prix.
    """
    print("📅 Ouverture calendrier...\n")
    try:
        date_input = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[aria-label*='Départ']")
            )
        )
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", date_input
        )
        time.sleep(0.5)
        date_input.click()

        print("✅ Ouvert\n")
        time.sleep(2.0)  # on laisse le popup se poser
        return True
    except Exception as e:
        print(f"❌ Erreur ouverture calendrier: {e}")
        return False

def _click_prev():
    """
    Clique la flèche 'Précédent' du calendrier (si dispo).
    Ces flèches sont les bulles blanches rondes (classe a2rVxf) dans la modale.
    """
    try:
        btns = driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//button[contains(@class,'a2rVxf') and @aria-label='Précédent']"
        )
        for b in btns:
            if b.is_displayed():
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", b
                )
                time.sleep(0.15)
                driver.execute_script("arguments[0].click();", b)
                return True
        raise Exception("pas de bouton 'Précédent' visible")
    except Exception as e:
        print(f"   ⚠️ clic Précédent: {e}")
        return False

def _click_next():
    """
    Clique la flèche 'Suivant' du calendrier (si dispo).
    """
    try:
        btns = driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//button[contains(@class,'a2rVxf') and @aria-label='Suivant']"
        )
        for b in btns:
            if b.is_displayed():
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", b
                )
                time.sleep(0.15)
                driver.execute_script("arguments[0].click();", b)
                return True
        raise Exception("pas de bouton 'Suivant' visible")
    except Exception as e:
        print(f"   ⚠️ clic Suivant: {e}")
        return False

# ============================================================================#
# CALENDRIER: STRUCTURE DES MOIS
# ============================================================================#

def _month_groups():
    """
    Récupère tous les blocs 'mois' actuellement DANS le calendrier.
    Chaque mois est un <div role="rowgroup" ...> qui contient:
      - un header .BgYkof ... ("novembre", "janvier 2026", ...)
      - des jours <div role="gridcell" data-iso="YYYY-MM-DD">

    On renvoie une liste de dicts:
        {
          "year": 2025,
          "month_num": 11,
          "header_text": "novembre",
          "group_el": <WebElement du rowgroup>,
          "header_el": <WebElement du titre>,
        }

    Très important: on déduit l'année réelle à partir du premier data-iso.
    Comme ça on gère ton point:
      - "novembre" sans année => 2025
      - "janvier 2026" => 2026
    """
    groups = driver.find_elements(
        By.XPATH,
        "//div[@role='dialog']//div[@jsname='RAZSvb']"
        "//div[@role='rowgroup' and contains(@class,'Bc6Ryd')]"
    )

    out = []
    for g in groups:
        try:
            header_el = g.find_element(
                By.CSS_SELECTOR,
                ".BgYkof.B5dqIf.qZwLKe"
            )
        except Exception:
            continue

        header_text = header_el.text.strip()  # ex: "novembre" ou "janvier 2026"

        # trouve une cellule avec data-iso, pour extraire l'année/mois vrais
        day_cells = g.find_elements(By.CSS_SELECTOR, "[data-iso]")
        year_val = None
        month_val = None
        for c in day_cells:
            iso = c.get_attribute("data-iso") or ""
            m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
            if m:
                year_val = int(m.group(1))
                month_val = int(m.group(2))
                break

        if year_val is None:
            # pas normal mais on skip juste au cas où
            continue

        out.append({
            "year": year_val,
            "month_num": month_val,
            "header_text": header_text,
            "group_el": g,
            "header_el": header_el,
        })

    return out

def _focus_month(target_month_name: str, target_year: int) -> bool:
    """
    Va amener le mois demandé sous les yeux :
    - Si le mois est déjà chargé dans le DOM:
        -> scrollIntoView sur son header
    - Sinon:
        -> on clique Suivant ou Précédent pour charger plus de mois,
           et on recommence.

    NOTE: Pour novembre 2025 / décembre 2025,
          c'est déjà chargé dès l'ouverture, donc pas de spam de flèches.
    """
    tgt_num = _month_num(target_month_name)
    tgt_total = target_year * 12 + tgt_num

    print(f"🔍 Navigation/scroll vers {target_month_name} {target_year}...\n")

    for step in range(60):  # garde-fou
        groups = _month_groups()

        # 1. Est-ce que notre mois est déjà dans le DOM ?
        for g in groups:
            if g["year"] == target_year and g["month_num"] == tgt_num:
                print(f"   ✅ Mois {target_month_name} {target_year} trouvé (step {step})")
                # on scroll ce mois en haut du viewport pour forcer le chargement prix
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'start'});",
                    g["header_el"]
                )
                time.sleep(0.8)
                return True

        # 2. Sinon, on doit charger plus loin (rare pour 2025 mais je prévois)
        months_loaded = [x["year"] * 12 + x["month_num"] for x in groups]
        if not months_loaded:
            print("   ⚠️ Aucun mois détecté dans le DOM, on réessaie...")
            time.sleep(0.5)
            continue

        min_loaded = min(months_loaded)
        max_loaded = max(months_loaded)

        if tgt_total < min_loaded:
            # on veut un mois PLUS ANCIEN -> clique Précédent
            print("   ← Besoin de mois plus anciens -> clic Précédent")
            if not _click_prev():
                print("   ❌ Échec clic Précédent")
                return False
            time.sleep(1.0)
            continue

        if tgt_total > max_loaded:
            # on veut un mois PLUS RÉCENT -> clique Suivant
            print("   → Besoin de mois plus récents -> clic Suivant")
            if not _click_next():
                print("   ❌ Échec clic Suivant")
                return False
            time.sleep(1.0)
            continue

        # 3. Target est entre min et max mais pas encore accroché :
        #    Parfois Google est lazy et ne render pas tant que t'as pas scrollé proche.
        closest = min(
            groups,
            key=lambda g: abs((g["year"] * 12 + g["month_num"]) - tgt_total)
        )
        print("   ↪ Scroll vers le mois le plus proche pour forcer le render…")
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'start'});",
            closest["header_el"]
        )
        time.sleep(0.8)

    print("   ❌ Impossible d'afficher le mois demandé après 60 tentatives")
    return False

# ============================================================================#
# LECTURE DES CELLULES JOUR/PRIX
# ============================================================================#

def _grid_cells():
    """
    Récupère toutes les cases jour visibles dans la modale calendrier.
    Chaque jour est un <div role='gridcell' data-iso='YYYY-MM-DD'> ... </div>
    """
    cells = driver.find_elements(
        By.XPATH,
        "//div[@role='dialog']//*[@role='gridcell' and @data-iso]"
    )

    out = []
    for c in cells:
        if not c.is_displayed():
            # s'il est carrément masqué (style display:none), on skip
            continue
        # même si aria-hidden="true", je les garde pas, parce que souvent
        # c'est les jours du mois précédent qui sont grisés
        aria_hidden = (c.get_attribute("aria-hidden") or "").lower()
        if aria_hidden == "true":
            continue

        iso = (c.get_attribute("data-iso") or "").strip()
        if not iso:
            continue
        out.append(c)

    return out

def _parse_iso(cell):
    """
    data-iso="2025-11-12" -> datetime(2025, 11, 12)
    """
    iso = cell.get_attribute("data-iso") or ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return None
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))

def _day_price(cell):
    """
    Lit le numéro du jour + le prix depuis la cellule.
    Structure typique:
      <div jsname="nEWxA">12</div>
      <div jsname="qCDwBb">€179</div>
    """
    try:
        d_el = cell.find_element(By.CSS_SELECTOR, "[jsname='nEWxA']")
        p_el = cell.find_element(By.CSS_SELECTOR, "[jsname='qCDwBb']")
        day_txt = d_el.text.strip()
        price_txt = p_el.text.strip()
    except Exception:
        # fallback bourrin si la structure change
        raw = (cell.text or "").strip().split("\n")
        raw = [x.strip() for x in raw if x.strip()]
        if len(raw) < 2:
            return (None, None)
        day_txt, price_txt = raw[0], raw[1]

    # jour
    if not day_txt.isdigit():
        return (None, None)
    day = int(day_txt)

    # prix -> garder uniquement les chiffres
    digits = "".join(ch for ch in price_txt if ch.isdigit())
    if not digits:
        return (None, None)
    price = int(digits)

    return (day, price)

def wait_prices_ready(target_month: str, target_year: int,
                      min_cells=4, timeout=7.0):
    """
    On attend que le mois ciblé ait au moins quelques cellules avec prix numériques.
    """
    tgt_num = _month_num(target_month)
    deadline = time.time() + timeout

    while time.time() < deadline:
        ready = 0
        for c in _grid_cells():
            dt = _parse_iso(c)
            if not dt or dt.year != target_year or dt.month != tgt_num:
                continue

            # check prix
            try:
                p_el = c.find_element(By.CSS_SELECTOR, "[jsname='qCDwBb']")
                price_txt = p_el.text.strip()
            except Exception:
                raw_last = (c.text or "").strip().split("\n")[-1]
                price_txt = raw_last

            if any(ch.isdigit() for ch in price_txt):
                ready += 1

        if ready >= min_cells:
            return True

        time.sleep(0.25)

    return False

def extract_prices_for_month(target_month: str, target_year: int) -> dict:
    """
    Après qu'on ait scrollé sur le bon mois.
    On lit toutes les cellules de ce mois et on renvoie { "mois année": {jour: prix, ...} }
    """
    print(f"💰 Extraction des prix pour {target_month} {target_year}...\n")

    if not wait_prices_ready(target_month, target_year,
                             min_cells=4,
                             timeout=7.0):
        print("   ⚠️  Peu de cellules avec prix détectées (on tente quand même)")

    tgt_num = _month_num(target_month)
    month_key = f"{target_month} {target_year}"
    out = {}

    for c in _grid_cells():
        dt = _parse_iso(c)
        if not dt or dt.year != target_year or dt.month != tgt_num:
            continue

        day_int, price_int = _day_price(c)
        if day_int is None or price_int is None:
            continue

        out[day_int] = price_int

    print(f"   → {len(out)} prix trouvés pour {month_key}\n")
    return {month_key: out}

# ============================================================================#
# MAIN
# ============================================================================#

try:
    # 1. Aller sur Google Flights
    url = (
        "https://www.google.com/travel/flights"
        f"?q=Flights+from+{ORIGIN}+to+{DESTINATION}&curr=EUR&hl=fr"
    )
    print("🌐 Navigation...\n")
    driver.get(url)
    time.sleep(5)

    handle_consent()
    time.sleep(1)

    driver.save_screenshot("screenshots/working_01.png")

    # 2. Ouvrir le calendrier
    print("="*70)
    print("ÉTAPE 1: OUVERTURE CALENDRIER")
    print("="*70 + "\n")

    if not open_calendar():
        raise Exception("Impossible d'ouvrir le calendrier")

    driver.save_screenshot("screenshots/working_02.png")

    # Juste pour debug: afficher les mois détectés dans le DOM au départ
    groups_init = _month_groups()
    if groups_init:
        print("   🚩 Mois présents dans le DOM au départ:")
        for g in groups_init:
            print(f"      - {_month_name(g['month_num'])} {g['year']}")
        print()

    # 3. Pour chaque mois cible:
    print("="*70)
    print("ÉTAPE 2: NAVIGATION (SCROLL) + EXTRACTION")
    print("="*70 + "\n")

    all_prices = {}

    for i, (m_name, y_val) in enumerate(TARGET_MONTHS, 1):
        print(f"--- MOIS {i}/{len(TARGET_MONTHS)}: {m_name} {y_val} ---\n")

        if not _focus_month(m_name, y_val):
            print(f"⚠️  Impossible d'afficher {m_name} {y_val}\n")
            continue

        # screenshot du mois après scroll
        safe_month = m_name.replace(" ", "_")
        driver.save_screenshot(f"screenshots/month_{i}_{safe_month}_{y_val}.png")

        month_prices = extract_prices_for_month(m_name, y_val)
        for k, v in month_prices.items():
            all_prices.setdefault(k, {}).update(v)

        time.sleep(0.5)

    # 4. Sauvegarde JSON
    print("="*70)
    print("ÉTAPE 3: SAUVEGARDE")
    print("="*70 + "\n")

    output = {
        "origin": ORIGIN,
        "destination": DESTINATION,
        "currency": "EUR",
        "prices_by_month": all_prices
    }

    out_file = Path("screenshots/calendar_prices_WORKING.json")
    out_file.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"💾 Sauvegardé: {out_file}\n")

    # 5. Résumé
    print("="*70)
    print("✅ TERMINÉ")
    print("="*70 + "\n")

    print("📊 Résumé:")
    for k, v in all_prices.items():
        print(f"   {k}: {len(v)} prix")

    if all_prices:
        vals = []
        for v in all_prices.values():
            vals.extend(v.values())
        if vals:
            print("\n💰 Statistiques globales:")
            print(f"   Min: {min(vals)} €")
            print(f"   Max: {max(vals)} €")
            print(f"   Moyenne: {sum(vals)//len(vals)} €")

    print("\n📁 Fichier: calendar_prices_WORKING.json ⭐")

    input("\n⏸️  ENTRÉE...")

except Exception as e:
    print(f"\n❌ {e}")
    import traceback
    traceback.print_exc()
    driver.save_screenshot("screenshots/working_error.png")
    input("▶️  ENTRÉE...")

finally:
    driver.quit()
    print("\n✅ Terminé")
