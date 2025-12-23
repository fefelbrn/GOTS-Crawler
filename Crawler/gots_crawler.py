"""
GOTS Certification Crawler - Version corrigée avec gestion cookies
"""

import time
import re
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GOTSCrawler:
    """Crawler pour vérifier les certifications GOTS"""
    
    def __init__(self, headless=True):
        """
        Initialise le crawler
        
        Args:
            headless: Si True, le navigateur s'exécute en mode headless
        """
        self.base_url = "https://global-standard.org/find-suppliers-shops-and-inputs/certifiedsuppliers"
        self.driver = None
        self.headless = headless
        self.setup_driver()
    
    def setup_driver(self):
        """Configure et initialise le driver Selenium"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("✅ Driver Chrome initialisé avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation du driver: {e}")
            raise
    
    def close_cookie_popup(self):
        """Ferme le popup de cookies s'il est présent"""
        try:
            # Méthode 1: Bouton "Accept all"
            accept_buttons = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'accept')]",
                "//button[contains(@class, 'accept')]",
                "//a[contains(text(), 'Accept')]",
                "//button[@id='cookieConsentAcceptButton']",
                "//button[contains(@class, 'cookie-accept')]",
            ]
            
            for xpath in accept_buttons:
                try:
                    button = self.driver.find_element(By.XPATH, xpath)
                    button.click()
                    logger.info("✅ Popup de cookies fermé (Accept)")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            # Méthode 2: Fermer via JavaScript
            try:
                self.driver.execute_script("""
                    var cookieElements = document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="consent"]');
                    cookieElements.forEach(el => el.style.display = 'none');
                """)
                logger.info("✅ Popup de cookies masqué via JavaScript")
                return True
            except:
                pass
            
            logger.info("ℹ️  Aucun popup de cookies détecté")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️  Erreur lors de la fermeture du popup: {e}")
            return False
    
    def search_certification(self, certification_number):
        """
        Recherche une certification sur le site GOTS
        
        Args:
            certification_number: Numéro de certification à rechercher
            
        Returns:
            dict: Résultats de la recherche avec statut et données
        """
        try:
            logger.info(f"🔍 Recherche de la certification: {certification_number}")
            self.driver.get(self.base_url)
            time.sleep(3)  # Attendre le chargement complet
            
            # IMPORTANT: Fermer le popup de cookies
            self.close_cookie_popup()
            time.sleep(1)
            
            # Trouver le champ "Free text"
            try:
                free_text_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                # Scroller vers l'input
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", free_text_input)
                time.sleep(0.5)
                
                free_text_input.clear()
                free_text_input.send_keys(certification_number)
                logger.info(f"✏️  Numéro de certification saisi: {certification_number}")
            except TimeoutException:
                logger.error("❌ Impossible de trouver le champ de recherche 'Free text'")
                return {"found": False, "error": "Champ de recherche introuvable", "certification_number": certification_number}
            
            # Cliquer sur le bouton de recherche avec gestion améliorée
            try:
                search_button = self.driver.find_element(
                    By.XPATH, 
                    "//button[contains(text(), 'SEARCH FOR SUPPLIERS') or contains(text(), 'Search')]"
                )
                
                # Scroller vers le bouton
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
                time.sleep(0.5)
                
                # Essayer clic normal
                try:
                    search_button.click()
                    logger.info("🔎 Bouton de recherche cliqué (méthode normale)")
                except Exception as e:
                    logger.warning(f"⚠️  Clic normal échoué: {e}, tentative JavaScript...")
                    # Fallback: JavaScript
                    self.driver.execute_script("arguments[0].click();", search_button)
                    logger.info("🔎 Bouton de recherche cliqué (méthode JavaScript)")
                
                # Attendre les résultats - CRUCIAL
                time.sleep(5)  # Augmenté à 5 secondes
                
            except NoSuchElementException:
                logger.error("❌ Bouton de recherche introuvable")
                return {"found": False, "error": "Bouton de recherche introuvable", "certification_number": certification_number}
            
            # Vérifier si des résultats ont été trouvés
            try:
                # Attendre que la page se charge complètement
                time.sleep(3)
                
                # Chercher d'abord s'il y a un tableau ou des liens
                has_table = False
                has_links = False
                
                try:
                    results_table = self.driver.find_element(By.TAG_NAME, "table")
                    has_table = True
                    logger.info("📊 Tableau trouvé sur la page")
                except NoSuchElementException:
                    pass
                
                # Chercher des liens de résultats
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute("href") or ""
                        if "view=article" in href or "details" in link.text.lower():
                            has_links = True
                            break
                except:
                    pass
                
                if has_table or has_links:
                    logger.info("✅ Résultats détectés")
                else:
                    # Vérifier les messages d'absence de résultats
                    page_text = self.driver.page_source.lower()
                    page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    
                    no_result_patterns = ["no results", "0 entries", "no entries"]
                    has_zero_entries = ("entries were found" in page_text_visible and "0" in page_text_visible)
                    
                    if any(pattern in page_text or pattern in page_text_visible for pattern in no_result_patterns) or has_zero_entries:
                        logger.info("ℹ️  Aucun résultat trouvé")
                        return {"found": False, "certification_number": certification_number}
                
                # Chercher le lien "details"
                details_links = []
                time.sleep(2)
                
                # Méthode 1: Chercher par classe et texte
                logger.info("🔍 Recherche du bouton 'details' (méthode 1: classe + texte)...")
                details_links = self.driver.find_elements(
                    By.XPATH, 
                    "//a[contains(@class, 'uk-button') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'details')]"
                )
                
                # Méthode 2: Chercher par href contenant view=article
                if not details_links:
                    logger.info("🔍 Recherche du bouton 'details' (méthode 2: href view=article)...")
                    details_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'view=article')]")
                
                # Méthode 3: Chercher tous les liens avec "details" dans le texte
                if not details_links:
                    logger.info("🔍 Recherche du bouton 'details' (méthode 3: texte 'details')...")
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        try:
                            link_text = link.text.strip().lower()
                            if "details" in link_text:
                                details_links.append(link)
                                break
                        except:
                            continue
                
                # Méthode 4: Chercher dans le tableau de résultats
                if not details_links:
                    logger.info("🔍 Recherche du bouton 'details' (méthode 4: dans le tableau)...")
                    try:
                        results_table = self.driver.find_element(By.TAG_NAME, "table")
                        table_links = results_table.find_elements(By.TAG_NAME, "a")
                        for link in table_links:
                            try:
                                link_text = link.text.strip().lower()
                                href = link.get_attribute("href") or ""
                                if "details" in link_text or "view=article" in href:
                                    details_links.append(link)
                                    break
                            except:
                                continue
                    except NoSuchElementException:
                        pass
                
                # Méthode 5: Chercher par lien partiel
                if not details_links:
                    logger.info("🔍 Recherche du bouton 'details' (méthode 5: href avec q=)...")
                    details_links = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(@href, 'q=') and contains(@href, 'view=article')]"
                    )
                
                if details_links:
                    logger.info(f"✅ {len(details_links)} lien(s) 'details' trouvé(s)")
                    
                    # Vérifier correspondance exacte
                    target_link = None
                    exact_match_found = False
                    
                    # Si un seul résultat, utilisation directe
                    if len(details_links) == 1:
                        target_link = details_links[0]
                        exact_match_found = True
                        logger.info("✅ Un seul résultat trouvé, utilisation directe")
                    else:
                        # Chercher dans le tableau pour correspondance exacte
                        try:
                            results_table = self.driver.find_element(By.TAG_NAME, "table")
                            rows = results_table.find_elements(By.TAG_NAME, "tr")
                            
                            for i, row in enumerate(rows[1:], 1):
                                try:
                                    row_text = row.text
                                    cert_pattern = rf'\b{re.escape(certification_number)}\b'
                                    if (re.search(cert_pattern, row_text) or 
                                        f"GOTS-{certification_number}" in row_text or
                                        f"GOTS {certification_number}" in row_text):
                                        try:
                                            link_in_row = row.find_element(By.XPATH, ".//a[contains(@class, 'uk-button') or contains(text(), 'details')]")
                                            target_link = link_in_row
                                            exact_match_found = True
                                            logger.info(f"✅ Résultat exact trouvé à la ligne {i+1}")
                                            break
                                        except:
                                            continue
                                except:
                                    continue
                        except Exception as e:
                            logger.warning(f"⚠️  Impossible de vérifier le tableau: {e}")
                        
                        if not exact_match_found:
                            logger.warning(f"⚠️  Aucun résultat exact pour {certification_number}")
                            page_text_check = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                            if "0 entries" in page_text_check or "no results" in page_text_check:
                                return {"found": False, "certification_number": certification_number}
                            else:
                                return {"found": False, "certification_number": certification_number, "error": "Aucun résultat exact trouvé"}
                    
                    if not target_link and exact_match_found:
                        target_link = details_links[0]
                    elif not target_link:
                        return {"found": False, "certification_number": certification_number}
                    
                    # CLIC SUR LE LIEN DETAILS
                    try:
                        # Scroller jusqu'au lien
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link)
                        time.sleep(1)
                        
                        # Essayer clic normal
                        try:
                            target_link.click()
                            logger.info("✅ Clic sur 'details' réussi (méthode normale)")
                        except Exception as e:
                            logger.warning(f"⚠️  Clic normal échoué: {e}, tentative avec JavaScript...")
                            self.driver.execute_script("arguments[0].click();", target_link)
                            logger.info("✅ Clic sur 'details' réussi (méthode JavaScript)")
                        
                        # ATTENDRE LE CHARGEMENT - CRUCIAL
                        time.sleep(5)
                        
                        # EXTRAIRE LES DONNÉES
                        details_data = self.extract_details_data()
                        
                        # Vérifier correspondance du numéro
                        extracted_cert = details_data.get("certification_number", "")
                        cert_matches = False
                        
                        if extracted_cert:
                            clean_extracted = re.sub(r'[A-Za-z\s-]+', '', extracted_cert)
                            clean_searched = re.sub(r'[A-Za-z\s-]+', '', certification_number)
                            
                            if clean_extracted == clean_searched or certification_number in extracted_cert or extracted_cert in certification_number:
                                cert_matches = True
                                logger.info(f"✅ Numéro correspond: {extracted_cert} == {certification_number}")
                            else:
                                logger.warning(f"⚠️  Numéro extrait ({extracted_cert}) != recherché ({certification_number})")
                        else:
                            details_data["certification_number"] = certification_number
                            cert_matches = True
                        
                        if not cert_matches:
                            return {"found": False, "certification_number": certification_number, "error": f"Numéro extrait ({extracted_cert}) ne correspond pas"}
                        
                        details_data["found"] = True
                        return details_data
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du clic sur 'details': {e}")
                        return {"found": False, "error": f"Erreur lors du clic: {e}", "certification_number": certification_number}
                else:
                    logger.warning("⚠️  Aucun lien 'details' trouvé")
                    return {"found": False, "error": "Lien 'details' introuvable", "certification_number": certification_number}
                    
            except Exception as e:
                logger.error(f"❌ Erreur lors de la vérification des résultats: {e}")
                return {"found": False, "error": str(e), "certification_number": certification_number}
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche: {e}")
            return {"found": False, "error": str(e), "certification_number": certification_number}
    
    def extract_details_data(self):
        """Extrait toutes les données de la page details"""
        data = {
            "company_name": "",
            "country": "",
            "field_of_operation": "",
            "product_category": "",
            "cb_client_number": "",
            "certification_body": "",
            "certificate_expiry_date": "",
            "address": "",
            "product_details": "",
            "certification_number": ""
        }
        
        try:
            # Nom de la compagnie
            try:
                company_elements = self.driver.find_elements(By.XPATH, "//h1 | //h2 | //div[contains(@class, 'title')] | //div[contains(@style, 'color')]")
                for elem in company_elements:
                    text = elem.text.strip()
                    if text and len(text) > 3:
                        data["company_name"] = text
                        logger.info(f"🏢 Compagnie: {text}")
                        break
            except Exception as e:
                logger.warning(f"⚠️  Impossible d'extraire le nom: {e}")
            
            # Texte de la page
            page_text = self.driver.page_source
            page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Fonction d'extraction
            def extract_field_improved(label_name, text_source):
                patterns = [
                    rf'{label_name}[:\s]+([^\n]+)',
                    rf'{label_name}[:\s]+([^<]+)',
                    rf'{label_name}\s*[:\s]*\s*([A-Za-z0-9\s,.-]+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text_source, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value = match.group(1).strip()
                        value = re.sub(r'<[^>]+>', '', value)
                        value = re.sub(r'\s+', ' ', value)
                        value = value.strip(' ,-')
                        if value and value != "0" and len(value) > 1:
                            return value[:500]
                
                try:
                    label_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{label_name}')]")
                    for label_elem in label_elements:
                        try:
                            parent = label_elem.find_element(By.XPATH, "./..")
                            parent_text = parent.text
                            parts = parent_text.split(label_name, 1)
                            if len(parts) > 1:
                                value = parts[1].strip().split('\n')[0].strip()
                                value = re.sub(r'[:\s]+', '', value, count=1)
                                if value and value != "0" and len(value) > 1:
                                    return value[:500]
                        except:
                            continue
                except:
                    pass
                
                return ""
            
            # Extraction des champs
            logger.info("📋 Extraction des données...")
            
            data["country"] = extract_field_improved("Country", page_text_visible) or extract_field_improved("Country", page_text)
            data["field_of_operation"] = extract_field_improved("Field of operation", page_text_visible) or extract_field_improved("Field of operation", page_text)
            data["product_category"] = extract_field_improved("Product category", page_text_visible) or extract_field_improved("Product category", page_text)
            
            # Certification Number
            cert_patterns = [
                r'Certification Number[:\s]+([A-Z0-9-]+)',
                r'Certification[:\s]+Number[:\s]+([A-Z0-9-]+)',
                r'GOTS[-\s]?(\d+)'
            ]
            for pattern in cert_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    data["certification_number"] = match.group(1).strip()
                    break
            
            # CB Client number
            cb_patterns = [
                r'CB Client number[:\s]+([\d-]+)',
                r'CB[-\s]?Client[-\s]?number[:\s]+([\d-]+)',
                r'Client number[:\s]+([\d-]+)'
            ]
            for pattern in cb_patterns:
                match = re.search(pattern, page_text_visible, re.IGNORECASE)
                if match:
                    data["cb_client_number"] = match.group(1).strip()
                    break
            if not data["cb_client_number"]:
                for pattern in cb_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        data["cb_client_number"] = match.group(1).strip()
                        break
            
            # Certification Body
            body_patterns = [
                r'Certification Body[:\s]+([^<\n]+)',
                r'Certification[:\s]+Body[:\s]+([^<\n]+)'
            ]
            for pattern in body_patterns:
                match = re.search(pattern, page_text_visible, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r'<[^>]+>', '', value)
                    data["certification_body"] = value[:200]
                    break
            
            # Certificate Expiry Date
            expiry_patterns = [
                r'Certificate Expiry Date[:\s]+([\d-]+)',
                r'Expiry Date[:\s]+([\d-]+)',
                r'Expires[:\s]+([\d-]+)'
            ]
            for pattern in expiry_patterns:
                match = re.search(pattern, page_text_visible, re.IGNORECASE)
                if match:
                    data["certificate_expiry_date"] = match.group(1).strip()
                    break
            
            # Address
            address_patterns = [
                r'Address[:\s]+([^<]+?)(?:\n|State|Postcode|Certification)',
                r'Address[:\s]+([^<\n]+)'
            ]
            for pattern in address_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    addr = match.group(1).strip()
                    addr = re.sub(r'<[^>]+>', '', addr)
                    state_match = re.search(r'State[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                    postcode_match = re.search(r'Postcode[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                    if state_match:
                        addr += f", {state_match.group(1).strip()}"
                    if postcode_match:
                        addr += f", {postcode_match.group(1).strip()}"
                    data["address"] = addr[:500]
                    break
            
            # Product details
            try:
                sections = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Product details') or contains(text(), 'OTHER DATA')]")
                if sections:
                    for section in sections:
                        try:
                            parent = section.find_element(By.XPATH, "./ancestor::div[1]")
                            product_text = parent.text
                            if "Product details" in product_text:
                                parts = product_text.split("Product details")
                                if len(parts) > 1:
                                    data["product_details"] = parts[1].strip()[:2000]
                                else:
                                    data["product_details"] = product_text.strip()[:2000]
                                break
                        except:
                            continue
                
                if not data["product_details"]:
                    product_match = re.search(r'Product details[:\s]+([^<]+)', page_text, re.IGNORECASE | re.DOTALL)
                    if product_match:
                        product_text = product_match.group(1).strip()
                        product_text = re.sub(r'<[^>]+>', '', product_text)
                        data["product_details"] = product_text[:2000]
            except Exception as e:
                logger.warning(f"⚠️  Erreur extraction product details: {e}")
            
            logger.info(f"✅ Données extraites pour: {data['company_name']}")
            logger.info(f"   - Pays: {data['country']}")
            logger.info(f"   - CB Client: {data['cb_client_number']}")
            logger.info(f"   - Expiration: {data['certificate_expiry_date']}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'extraction: {e}")
            return data
    
    def close(self):
        """Ferme le driver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Driver fermé")


# Script de test
if __name__ == "__main__":
    import json
    
    test_cert_number = "21205"
    
    crawler = GOTSCrawler(headless=False)  # headless=False pour debug
    
    try:
        result = crawler.search_certification(test_cert_number)
        
        print("\n" + "="*70)
        print("RÉSULTAT DE LA RECHERCHE")
        print("="*70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*70 + "\n")
        
    finally:
        crawler.close()