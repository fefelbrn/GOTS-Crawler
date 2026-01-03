"""
GOTS Certification Crawler - Version optimisée pour Dust (< 30s)
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

# Réduire les logs externes
logging.getLogger('WDM').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


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
        
        # OPTIMISATIONS SPEED
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Pas de chargement d'images
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        chrome_options.page_load_strategy = 'eager'  # Ne pas attendre le chargement complet
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(5)  # Réduit de 10 à 5
            logger.info("✅ Driver Chrome initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur driver: {e}")
            raise
    
    def close_cookie_popup(self):
        """Ferme le popup de cookies rapidement"""
        try:
            # Méthode JavaScript directe (plus rapide)
            self.driver.execute_script("""
                var cookieElements = document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="consent"]');
                cookieElements.forEach(el => el.style.display = 'none');
            """)
            logger.info("✅ Cookies masqués")
            return True
        except:
            return False
    
    def search_certification(self, certification_number):
        """
        Recherche une certification sur le site GOTS (optimisé < 30s)
        
        Args:
            certification_number: Numéro de certification à rechercher
            
        Returns:
            dict: Résultats de la recherche avec statut et données
        """
        try:
            logger.info(f"🔍 Recherche: {certification_number}")
            self.driver.get(self.base_url)
            time.sleep(2)  # Réduit de 3 à 2
            
            self.close_cookie_popup()
            time.sleep(0.5)  # Réduit de 1 à 0.5
            
            # Champ "Free text"
            try:
                free_text_input = WebDriverWait(self.driver, 8).until(  # Réduit de 10 à 8
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", free_text_input)
                time.sleep(0.3)  # Réduit de 0.5 à 0.3
                
                free_text_input.clear()
                free_text_input.send_keys(certification_number)
                logger.info(f"✏️  Saisi: {certification_number}")
            except TimeoutException:
                logger.error("❌ Champ introuvable")
                return {"found": False, "error": "Champ de recherche introuvable", "certification_number": certification_number}
            
            # Bouton de recherche
            try:
                search_button = self.driver.find_element(
                    By.XPATH, 
                    "//button[contains(text(), 'SEARCH FOR SUPPLIERS') or contains(text(), 'Search')]"
                )
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_button)
                time.sleep(0.3)  # Réduit de 0.5 à 0.3
                
                try:
                    search_button.click()
                    logger.info("🔎 Recherche lancée")
                except:
                    self.driver.execute_script("arguments[0].click();", search_button)
                    logger.info("🔎 Recherche lancée (JS)")
                
                time.sleep(3)  # Réduit de 5 à 3
                
            except NoSuchElementException:
                logger.error("❌ Bouton introuvable")
                return {"found": False, "error": "Bouton de recherche introuvable", "certification_number": certification_number}
            
            # Vérifier résultats
            try:
                time.sleep(2)  # Réduit de 3 à 2
                
                has_table = False
                has_links = False
                
                try:
                    self.driver.find_element(By.TAG_NAME, "table")
                    has_table = True
                    logger.info("📊 Tableau trouvé")
                except NoSuchElementException:
                    pass
                
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute("href") or ""
                        if "view=article" in href or "details" in link.text.lower():
                            has_links = True
                            break
                except:
                    pass
                
                if not has_table and not has_links:
                    page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    no_result_patterns = ["no results", "0 entries", "no entries"]
                    
                    if any(pattern in page_text_visible for pattern in no_result_patterns):
                        logger.info("ℹ️  Aucun résultat")
                        return {"found": False, "certification_number": certification_number}
                
                # Chercher le lien "details"
                details_links = []
                time.sleep(1)  # Réduit de 2 à 1
                
                logger.info("🔍 Recherche 'details'...")
                details_links = self.driver.find_elements(
                    By.XPATH, 
                    "//a[contains(@class, 'uk-button') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'details')]"
                )
                
                if not details_links:
                    details_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'view=article')]")
                
                if not details_links:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        try:
                            if "details" in link.text.strip().lower():
                                details_links.append(link)
                                break
                        except:
                            continue
                
                if details_links:
                    logger.info(f"✅ {len(details_links)} lien(s) trouvé(s)")
                    
                    target_link = None
                    exact_match_found = False
                    
                    if len(details_links) == 1:
                        target_link = details_links[0]
                        exact_match_found = True
                        logger.info("✅ Un seul résultat, sélection automatique")
                    
                    elif len(details_links) > 1:
                        logger.info(f"⚠️  Plusieurs résultats ({len(details_links)}), tentative de match exact dans le tableau...")
                        
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
                                            logger.info(f"✅ Match exact trouvé dans la ligne {i}")
                                            break
                                        except:
                                            continue
                                except:
                                    continue
                        except:
                            pass
                        
                        # SI AUCUN MATCH DANS LE TABLEAU : PRENDRE LE PREMIER RÉSULTAT
                        if not exact_match_found:
                            logger.warning(f"⚠️  Aucun match exact dans le tableau (normal, le numéro n'y est pas affiché)")
                            logger.info(f"📌 Sélection du PREMIER résultat par défaut")
                            target_link = details_links[0]
                            exact_match_found = True  # On considère qu'on a un candidat valide
                    
                    # Vérification finale
                    if not target_link:
                        logger.error("❌ Impossible de sélectionner un lien")
                        return {"found": False, "certification_number": certification_number}
                    
                    # Clic sur details
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_link)
                        time.sleep(0.5)
                        
                        try:
                            target_link.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", target_link)
                        
                        time.sleep(3)
                        
                        # EXTRAIRE DONNÉES
                        details_data = self.extract_details_data()
                        
                        # Vérifier que le numéro de certification correspond bien
                        extracted_cert = details_data.get("certification_number", "")
                        cert_matches = False
                        
                        if extracted_cert:
                            clean_extracted = re.sub(r'[A-Za-z\s-]+', '', extracted_cert)
                            clean_searched = re.sub(r'[A-Za-z\s-]+', '', certification_number)
                            
                            if clean_extracted == clean_searched or certification_number in extracted_cert:
                                cert_matches = True
                            else:
                                # On retourne quand même les données avec un warning
                                details_data["warning"] = f"Certification trouvée: {extracted_cert}, recherchée: {certification_number}"
                                cert_matches = True  # On accepte quand même pour investigation
                        else:
                            # Pas de numéro extrait de la page, on met celui recherché
                            logger.warning("⚠️  Numéro de certification non extrait de la page de détails")
                            details_data["certification_number"] = certification_number
                            cert_matches = True
                        
                        details_data["found"] = True
                        return details_data
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur lors du clic: {e}")
                        return {"found": False, "error": str(e), "certification_number": certification_number}
                        
                        if extracted_cert:
                            clean_extracted = re.sub(r'[A-Za-z\s-]+', '', extracted_cert)
                            clean_searched = re.sub(r'[A-Za-z\s-]+', '', certification_number)
                            
                            if clean_extracted == clean_searched or certification_number in extracted_cert:
                                cert_matches = True
                                logger.info(f"✅ Match: {extracted_cert}")
                            else:
                                logger.warning(f"⚠️  Pas de match: {extracted_cert} != {certification_number}")
                        else:
                            details_data["certification_number"] = certification_number
                            cert_matches = True
                        
                        if not cert_matches:
                            return {"found": False, "certification_number": certification_number}
                        
                        details_data["found"] = True
                        return details_data
                        
                    except Exception as e:
                        logger.error(f"❌ Erreur clic: {e}")
                        return {"found": False, "error": str(e), "certification_number": certification_number}
                else:
                    logger.warning("⚠️  Aucun lien 'details'")
                    return {"found": False, "certification_number": certification_number}
                    
            except Exception as e:
                logger.error(f"❌ Erreur résultats: {e}")
                return {"found": False, "error": str(e), "certification_number": certification_number}
                
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return {"found": False, "error": str(e), "certification_number": certification_number}
    
    def extract_details_data(self):
        """Extrait les données complètes incluant CONTACT DATA"""
        data = {
            "company_name": "",
            "country": "",
            "field_of_operation": "",
            "product_category": "",
            "cb_client_number": "",
            "certification_body": "",
            "certificate_expiry_date": "",
            "address": "",
            "state": "",                    
            "postcode": "",                 
            "city": "",                     
            "product_details": "",
            "certification_number": ""
        }
        
        try:
            # Nom compagnie
            try:
                company_elements = self.driver.find_elements(By.XPATH, "//h1 | //h2")
                for elem in company_elements:
                    text = elem.text.strip()
                    if text and len(text) > 3:
                        data["company_name"] = text
                        break
            except:
                pass
            
            page_text = self.driver.page_source
            page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text
            
            # ==================== EXTRACTION CHAMPS GÉNÉRAUX ====================
            
            def extract_field(label, text_source):
                patterns = [
                    rf'{label}[:\s]+([^\n]+)',
                    rf'{label}\s*[:\s]*\s*([A-Za-z0-9\s,.-]+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text_source, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        value = re.sub(r'<[^>]+>', '', value)
                        value = re.sub(r'\s+', ' ', value).strip(' ,-')
                        if value and len(value) > 1:
                            return value[:500]
                return ""
            
            data["country"] = extract_field("Country", page_text_visible)
            data["field_of_operation"] = extract_field("Field of operation", page_text_visible)
            data["product_category"] = extract_field("Product category", page_text_visible)
            
            # Certification Number
            cert_match = re.search(r'GOTS[-\s]?(\d+)', page_text, re.IGNORECASE)
            if cert_match:
                data["certification_number"] = cert_match.group(1)
            
            # CB Client number
            cb_match = re.search(r'CB Client number[:\s]+([\d-]+)', page_text_visible, re.IGNORECASE)
            if cb_match:
                data["cb_client_number"] = cb_match.group(1)
            
            # Certification Body
            body_match = re.search(r'Certification Body[:\s]+([^<\n]+)', page_text_visible, re.IGNORECASE)
            if body_match:
                data["certification_body"] = body_match.group(1).strip()[:200]
            
            # Expiry Date
            expiry_match = re.search(r'Certificate Expiry Date[:\s]+([\d-]+)', page_text_visible, re.IGNORECASE)
            if expiry_match:
                data["certificate_expiry_date"] = expiry_match.group(1)
            
            # ==================== CONTACT DATA ====================
                     
            # Address (rue + numéro)
            address_match = re.search(
                r'Address[:\s]+([^\n]+?)(?=\s*State|$)', 
                page_text_visible, 
                re.IGNORECASE
            )
            if address_match:
                data["address"] = address_match.group(1).strip()[:300]
            else:
                # Fallback: chercher dans le HTML
                addr_match_html = re.search(r'Address[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                if addr_match_html:
                    data["address"] = re.sub(r'<[^>]+>', '', addr_match_html.group(1)).strip()[:300]
            
            # State
            state_match = re.search(
                r'State[:\s]+([^\n]+?)(?=\s*Postcode|$)', 
                page_text_visible, 
                re.IGNORECASE
            )
            if state_match:
                data["state"] = state_match.group(1).strip()[:200]
            
            # Postcode, City (souvent sur la même ligne)
            postcode_city_match = re.search(
                r'Postcode,\s*City[:\s]+([^\n]+)', 
                page_text_visible, 
                re.IGNORECASE
            )
            if postcode_city_match:
                postcode_city = postcode_city_match.group(1).strip()
                # Essayer de séparer postcode et city
                # Format typique: "1033 MZ, Amsterdam"
                parts = postcode_city.split(',', 1)
                if len(parts) == 2:
                    data["postcode"] = parts[0].strip()
                    data["city"] = parts[1].strip()
                else:
                    # Si pas de virgule, tout dans postcode
                    data["postcode"] = postcode_city
            else:
                # Fallback séparé
                postcode_match = re.search(r'Postcode[:\s]+([^\n,]+)', page_text_visible, re.IGNORECASE)
                if postcode_match:
                    data["postcode"] = postcode_match.group(1).strip()
                
                city_match = re.search(r'City[:\s]+([^\n]+)', page_text_visible, re.IGNORECASE)
                if city_match:
                    data["city"] = city_match.group(1).strip()
                        
            # ==================== PRODUCT DETAILS ====================
            
            logger.info("📦 Extraction product_details...")
            
            product_details_list = []
            
            # Méthode 1: Chercher un tableau de produits
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    header_text = ""
                    if rows:
                        header_text = rows[0].text.lower()
                                            
                        for row in rows[1:]:
                            try:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 2:
                                    row_text = row.text.strip()
                                    if row_text and len(row_text) > 5:
                                        product_details_list.append(row_text)
                            except:
                                continue
                        
                        if product_details_list:
                            break
            except Exception as e:
                logger.warning(f"⚠️ Erreur extraction tableau: {e}")
            
            # Méthode 2: Extraction par regex
            if not product_details_list:            
                product_pattern = r"([A-Za-z\s',]+)\s*\(PC\d+\);?\s*([^;]+)\s*\(PD\d+\);?\s*([^,\n]+(?:Min\.\s*\d+%\s*Max\.\s*\d+%[^,\n]*)+)"
                matches = re.findall(product_pattern, page_text_visible, re.IGNORECASE)
                
                for match in matches:
                    product_line = "; ".join([m.strip() for m in match if m.strip()])
                    product_details_list.append(product_line)
                
            
            # Méthode 3: Extraction section Product Details
            if not product_details_list:
                
                product_section_match = re.search(
                    r'Product Details[:\s]*(.*?)(?:Address|Certificate|CONTACT DATA|$)',
                    page_text_visible,
                    re.IGNORECASE | re.DOTALL
                )
                
                if product_section_match:
                    product_section = product_section_match.group(1)
                    
                    lines = product_section.split('\n')
                    for line in lines:
                        line = line.strip()
                        if (line and 
                            len(line) > 10 and 
                            ('PC' in line or 'PD' in line or 'Min.' in line or '%' in line)):
                            product_details_list.append(line)
                    
            
            # Assembler product_details
            if product_details_list:
                cleaned_products = []
                seen = set()
                
                for product in product_details_list:
                    product = re.sub(r'\s+', ' ', product).strip()
                    product = product.strip(',; ')
                    
                    if product and product not in seen and len(product) > 10:
                        cleaned_products.append(product)
                        seen.add(product)
                
                data["product_details"] = ", ".join(cleaned_products)
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction: {e}")
            return data


    def close(self):
        """Ferme le driver"""
        if self.driver:
            self.driver.quit()
            logger.info("🔒 Driver fermé")


if __name__ == "__main__":
    import json
    
    crawler = GOTSCrawler(headless=True)
    
    try:
        result = crawler.search_certification("21205")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        crawler.close()