"""
GOTS Certification Crawler
Crawls the GOTS certified suppliers database to verify certifications
"""

import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import pdfplumber
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GOTSCrawler:
    """Crawler pour vérifier les certifications GOTS"""
    
    def __init__(self, headless=False):
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
            # Utiliser webdriver-manager pour télécharger automatiquement ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("Driver Chrome initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du driver: {e}")
            logger.info("Tentative sans webdriver-manager...")
            try:
                # Fallback: essayer sans service explicite
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.implicitly_wait(10)
                logger.info("Driver Chrome initialisé avec succès (sans webdriver-manager)")
            except Exception as e2:
                logger.error(f"Erreur lors de l'initialisation du driver (fallback): {e2}")
                raise
    
    def extract_certification_number_from_pdf(self, pdf_path):
        """
        Extrait le numéro de certification depuis un PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            str: Numéro de certification trouvé, None si non trouvé
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                
                # Recherche de patterns de numéro de certification GOTS
                # Format typique: GOTS-XXXXX ou similaire
                patterns = [
                    r'GOTS[-\s]?(\d+)',
                    r'Certification[-\s]?Number[:\s]+([A-Z0-9-]+)',
                    r'Certificate[-\s]?Number[:\s]+([A-Z0-9-]+)',
                    r'License[-\s]?Number[:\s]+([A-Z0-9-]+)',
                    r'CB[-\s]?Client[-\s]?number[:\s]+(\d+)',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        cert_number = matches[0] if isinstance(matches[0], str) else str(matches[0])
                        logger.info(f"Numéro de certification trouvé: {cert_number}")
                        return cert_number
                
                # Si aucun pattern spécifique, chercher des numéros qui ressemblent à des certifications
                # Format: lettres suivies de tiret et chiffres
                general_pattern = r'[A-Z]{2,}[-\s]?\d{4,}'
                matches = re.findall(general_pattern, text)
                if matches:
                    cert_number = matches[0].replace(' ', '-')
                    logger.info(f"Numéro de certification trouvé (pattern général): {cert_number}")
                    return cert_number
                
                logger.warning(f"Aucun numéro de certification trouvé dans {pdf_path}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du PDF {pdf_path}: {e}")
            return None
    
    def search_certification(self, certification_number):
        """
        Recherche une certification sur le site GOTS
        
        Args:
            certification_number: Numéro de certification à rechercher
            
        Returns:
            dict: Résultats de la recherche avec statut et données
        """
        try:
            logger.info(f"Recherche de la certification: {certification_number}")
            self.driver.get(self.base_url)
            time.sleep(2)  # Attendre le chargement de la page
            
            # Trouver le champ "Free text"
            try:
                free_text_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                free_text_input.clear()
                free_text_input.send_keys(certification_number)
                logger.info(f"Numéro de certification saisi: {certification_number}")
            except TimeoutException:
                logger.error("Impossible de trouver le champ de recherche 'Free text'")
                return {"found": False, "error": "Champ de recherche introuvable"}
            
            # Cliquer sur le bouton de recherche
            try:
                search_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'SEARCH FOR SUPPLIERS') or contains(text(), 'Search')]")
                search_button.click()
                logger.info("Bouton de recherche cliqué")
                time.sleep(3)  # Attendre les résultats
            except NoSuchElementException:
                logger.error("Bouton de recherche introuvable")
                return {"found": False, "error": "Bouton de recherche introuvable"}
            
            # Vérifier si des résultats ont été trouvés
            try:
                # Attendre un peu pour que la page se charge complètement
                time.sleep(3)
                
                # Chercher d'abord s'il y a un tableau ou des liens (signe qu'il y a des résultats)
                has_table = False
                has_links = False
                try:
                    results_table = self.driver.find_element(By.TAG_NAME, "table")
                    has_table = True
                    logger.info("Tableau trouvé sur la page")
                except NoSuchElementException:
                    pass
                
                # Chercher des liens qui pourraient être des résultats
                try:
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        href = link.get_attribute("href") or ""
                        if "view=article" in href or "details" in link.text.lower():
                            has_links = True
                            break
                except:
                    pass
                
                # Si on a un tableau ou des liens, on a probablement des résultats
                if has_table or has_links:
                    logger.info("Résultats détectés (tableau ou liens trouvés)")
                else:
                    # Vérifier les messages d'absence de résultats
                    page_text = self.driver.page_source.lower()
                    page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    
                    no_result_patterns = [
                        "no results",
                        "0 entries",
                        "no entries"
                    ]
                    
                    # Vérifier aussi si "entries were found" contient "0"
                    has_zero_entries = ("entries were found" in page_text_visible and "0" in page_text_visible and "1" not in page_text_visible[:page_text_visible.find("entries")])
                    
                    if any(pattern in page_text or pattern in page_text_visible for pattern in no_result_patterns) or has_zero_entries:
                        logger.info("Aucun résultat trouvé (message d'erreur détecté)")
                        return {"found": False, "certification_number": certification_number}
                
                # Vérifier s'il y a un tableau de résultats ou des liens "details"
                details_links = []
                try:
                    # Attendre un peu plus pour que la page se charge complètement
                    time.sleep(2)
                    
                    # Méthode 1: Chercher par classe et texte
                    logger.info("Recherche du bouton 'details' (méthode 1: classe + texte)...")
                    details_links = self.driver.find_elements(
                        By.XPATH, 
                        "//a[contains(@class, 'uk-button') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'details')]"
                    )
                    
                    # Méthode 2: Chercher par href contenant view=article
                    if not details_links:
                        logger.info("Recherche du bouton 'details' (méthode 2: href view=article)...")
                        details_links = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'view=article')]"
                        )
                    
                    # Méthode 3: Chercher tous les liens avec "details" dans le texte
                    if not details_links:
                        logger.info("Recherche du bouton 'details' (méthode 3: texte 'details')...")
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
                        logger.info("Recherche du bouton 'details' (méthode 4: dans le tableau)...")
                        try:
                            results_table = self.driver.find_element(By.TAG_NAME, "table")
                            # Chercher tous les liens dans le tableau
                            table_links = results_table.find_elements(By.TAG_NAME, "a")
                            for link in table_links:
                                try:
                                    link_text = link.text.strip().lower()
                                    if "details" in link_text or "view=article" in link.get_attribute("href") or "":
                                        details_links.append(link)
                                        break
                                except:
                                    continue
                        except NoSuchElementException:
                            pass
                    
                    # Méthode 5: Chercher par lien partiel (href contient q=)
                    if not details_links:
                        logger.info("Recherche du bouton 'details' (méthode 5: href avec q=)...")
                        details_links = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'q=') and contains(@href, 'view=article')]"
                        )
                    
                    # Vérifier aussi s'il y a un tableau
                    try:
                        results_table = self.driver.find_element(By.TAG_NAME, "table")
                        logger.info("Tableau de résultats trouvé")
                    except NoSuchElementException:
                        pass
                    
                    if details_links:
                        logger.info(f"{len(details_links)} lien(s) 'details' trouvé(s)")
                        
                        # Vérifier si un résultat correspond exactement au numéro recherché
                        target_link = None
                        exact_match_found = False
                        
                        # Si un seul résultat, on peut directement l'utiliser (probablement le bon)
                        if len(details_links) == 1:
                            target_link = details_links[0]
                            exact_match_found = True
                            logger.info("Un seul résultat trouvé, utilisation directe")
                        else:
                            # Chercher dans le tableau pour trouver la ligne correspondante exacte
                            try:
                                results_table = self.driver.find_element(By.TAG_NAME, "table")
                                rows = results_table.find_elements(By.TAG_NAME, "tr")
                                
                                for i, row in enumerate(rows[1:], 1):  # Skip header
                                    try:
                                        row_text = row.text
                                        # Vérifier si le numéro recherché correspond EXACTEMENT
                                        # Formats possibles: "21204", "GOTS-21204", "CB-21204", etc.
                                        # Pattern pour correspondance exacte (word boundary)
                                        cert_pattern = rf'\b{re.escape(certification_number)}\b'
                                        # Vérifier aussi les formats avec préfixes
                                        if (re.search(cert_pattern, row_text) or 
                                            f"GOTS-{certification_number}" in row_text or
                                            f"GOTS {certification_number}" in row_text):
                                            # Trouver le lien "details" dans cette ligne
                                            try:
                                                link_in_row = row.find_element(By.XPATH, ".//a[contains(@class, 'uk-button') or contains(text(), 'details')]")
                                                target_link = link_in_row
                                                exact_match_found = True
                                                logger.info(f"Résultat correspondant exactement trouvé à la ligne {i+1}")
                                                break
                                            except:
                                                continue
                                    except Exception:
                                        continue
                            except Exception as e:
                                logger.warning(f"Impossible de vérifier les résultats dans le tableau: {e}")
                            except Exception as e:
                                logger.warning(f"Impossible de vérifier les résultats dans le tableau: {e}")
                            
                            # Si pas de correspondance exacte trouvée dans le tableau
                            if not exact_match_found:
                                logger.warning(f"Aucun résultat ne correspond exactement au numéro {certification_number}")
                                # Vérifier le message "entries were found" pour confirmer
                                page_text_visible_check = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                                if "0 entries" in page_text_visible_check or "no results" in page_text_visible_check:
                                    logger.info("Aucun résultat trouvé (message confirmé)")
                                    return {"found": False, "certification_number": certification_number}
                                else:
                                    # Il y a des résultats mais aucun ne correspond exactement
                                    logger.info(f"Des résultats existent mais aucun ne correspond exactement à {certification_number}")
                                    return {"found": False, "certification_number": certification_number, "error": "Aucun résultat exact trouvé"}
                        
                        # Si pas de lien cible trouvé mais exact_match_found est True, utiliser le premier
                        if not target_link and exact_match_found:
                            target_link = details_links[0]
                        elif not target_link:
                            # Aucun résultat exact, retourner False
                            return {"found": False, "certification_number": certification_number}
                        
                        # Essayer de cliquer sur le lien
                        try:
                            # Scroller jusqu'au lien pour s'assurer qu'il est visible
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", target_link)
                            time.sleep(0.5)
                            
                            # Essayer de cliquer normalement
                            try:
                                target_link.click()
                                logger.info("Clic sur 'details' réussi (méthode normale)")
                            except Exception as e:
                                logger.warning(f"Clic normal échoué: {e}, tentative avec JavaScript...")
                                # Essayer avec JavaScript
                                self.driver.execute_script("arguments[0].click();", target_link)
                                logger.info("Clic sur 'details' réussi (méthode JavaScript)")
                            
                            time.sleep(4)  # Attendre le chargement de la page details
                            
                            # Extraire les données de la page details
                            details_data = self.extract_details_data()
                            
                            # Vérifier si le numéro de certification correspond EXACTEMENT
                            extracted_cert = details_data.get("certification_number", "")
                            cert_matches = False
                            
                            if extracted_cert:
                                # Nettoyer le numéro extrait (enlever GOTS-, CB-, etc.)
                                clean_extracted = re.sub(r'[A-Za-z\s-]+', '', extracted_cert)
                                clean_searched = re.sub(r'[A-Za-z\s-]+', '', certification_number)
                                
                                # Vérifier correspondance exacte
                                if clean_extracted == clean_searched or certification_number in extracted_cert or extracted_cert in certification_number:
                                    cert_matches = True
                                    logger.info(f"Numéro de certification correspond: {extracted_cert} == {certification_number}")
                                else:
                                    logger.warning(f"Le numéro extrait ({extracted_cert}) ne correspond pas au numéro recherché ({certification_number})")
                            else:
                                # Si pas de numéro extrait, utiliser celui recherché
                                details_data["certification_number"] = certification_number
                                cert_matches = True
                            
                            # Si le numéro ne correspond pas, retourner False
                            if not cert_matches:
                                logger.warning(f"Aucune correspondance exacte trouvée pour {certification_number}")
                                return {"found": False, "certification_number": certification_number, "error": f"Numéro extrait ({extracted_cert}) ne correspond pas"}
                            
                            details_data["found"] = True
                            return details_data
                        except Exception as e:
                            logger.error(f"Erreur lors du clic sur 'details': {e}")
                            return {"found": False, "error": f"Erreur lors du clic: {e}", "certification_number": certification_number}
                    else:
                        # Vérifier s'il y a quand même des résultats affichés
                        if "entries were found" in page_text_visible and "0" not in page_text_visible:
                            logger.warning("Résultats mentionnés mais pas de lien 'details' trouvé")
                            # Essayer de cliquer directement sur le premier lien du tableau
                            try:
                                results_table = self.driver.find_element(By.TAG_NAME, "table")
                                first_result = results_table.find_element(By.XPATH, ".//tr[2]//a")  # Première ligne de données (après header)
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", first_result)
                                time.sleep(0.5)
                                first_result.click()
                                time.sleep(4)
                                details_data = self.extract_details_data()
                                details_data["found"] = True
                                if not details_data.get("certification_number"):
                                    details_data["certification_number"] = certification_number
                                return details_data
                            except Exception as e:
                                logger.warning(f"Tentative de clic sur le premier résultat échouée: {e}")
                        
                        logger.warning("Aucun lien 'details' trouvé malgré la présence de résultats")
                        # Sauvegarder une capture d'écran pour debug (optionnel)
                        return {"found": False, "error": "Lien 'details' introuvable", "certification_number": certification_number}
                        
                except NoSuchElementException:
                    logger.warning("Aucun tableau de résultats trouvé")
                    return {"found": False, "certification_number": certification_number}
                    
            except Exception as e:
                logger.error(f"Erreur lors de la vérification des résultats: {e}")
                return {"found": False, "error": str(e), "certification_number": certification_number}
                
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return {"found": False, "error": str(e), "certification_number": certification_number}
    
    def extract_details_data(self):
        """
        Extrait toutes les données de la page details
        
        Returns:
            dict: Dictionnaire contenant toutes les données extraites
        """
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
            # Extraire le nom de la compagnie (généralement en titre en vert)
            try:
                # Chercher le titre principal (souvent en h1 ou div avec style vert)
                company_elements = self.driver.find_elements(By.XPATH, "//h1 | //h2 | //div[contains(@class, 'title')] | //div[contains(@style, 'color')]")
                for elem in company_elements:
                    text = elem.text.strip()
                    if text and len(text) > 3:  # Filtrer les titres vides ou trop courts
                        data["company_name"] = text
                        break
            except Exception as e:
                logger.warning(f"Impossible d'extraire le nom de la compagnie: {e}")
            
            # Obtenir le texte de la page pour extraction par regex
            page_text = self.driver.page_source
            page_text_visible = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Essayer d'extraire depuis les sections structurées (GENERAL DATA, CERTIFICATION DATA, etc.)
            try:
                # Chercher les sections
                sections = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'section') or contains(@class, 'data')]")
                all_text = page_text_visible
                
                # Méthode améliorée: chercher les labels suivis de leurs valeurs
                def extract_field_improved(label_name, text_source):
                    """Extrait une valeur après un label avec plusieurs méthodes"""
                    # Méthode 1: Regex simple
                    patterns = [
                        rf'{label_name}[:\s]+([^\n]+)',
                        rf'{label_name}[:\s]+([^<]+)',
                        rf'{label_name}\s*[:\s]*\s*([A-Za-z0-9\s,.-]+)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text_source, re.IGNORECASE | re.MULTILINE)
                        if match:
                            value = match.group(1).strip()
                            # Nettoyer
                            value = re.sub(r'<[^>]+>', '', value)
                            value = re.sub(r'\s+', ' ', value)
                            # Enlever les virgules/tirets en début/fin
                            value = value.strip(' ,-')
                            if value and value != "0" and len(value) > 1:
                                return value[:500]
                    
                    # Méthode 2: Chercher dans les éléments HTML structurés
                    try:
                        label_elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{label_name}')]")
                        for label_elem in label_elements:
                            try:
                                # Chercher le parent ou le suivant
                                parent = label_elem.find_element(By.XPATH, "./..")
                                parent_text = parent.text
                                # Extraire la valeur après le label
                                parts = parent_text.split(label_name, 1)
                                if len(parts) > 1:
                                    value = parts[1].strip().split('\n')[0].strip()
                                    value = re.sub(r'[:\s]+', '', value, count=1)  # Enlever le premier : ou espace
                                    if value and value != "0" and len(value) > 1:
                                        return value[:500]
                            except:
                                continue
                    except:
                        pass
                    
                    return ""
                
                # Country - peut être dans GENERAL DATA
                data["country"] = extract_field_improved("Country", page_text_visible)
                if not data["country"] or data["country"] == "0":
                    data["country"] = extract_field_improved("Country", page_text)
                
                # Field of operation
                data["field_of_operation"] = extract_field_improved("Field of operation", page_text_visible)
                if not data["field_of_operation"]:
                    data["field_of_operation"] = extract_field_improved("Field of operation", page_text)
                
                # Product category
                data["product_category"] = extract_field_improved("Product category", page_text_visible)
                if not data["product_category"]:
                    data["product_category"] = extract_field_improved("Product category", page_text)
                    
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction structurée: {e}")
                # Fallback sur l'ancienne méthode
                def extract_field(label_pattern, text, multiline=False):
                    """Extrait une valeur après un label"""
                    pattern = rf'{label_pattern}[:\s]+([^<\n]+)'
                    if multiline:
                        pattern = rf'{label_pattern}[:\s]+([^<]+)'
                    match = re.search(pattern, text, re.IGNORECASE | (re.DOTALL if multiline else 0))
                    if match:
                        value = match.group(1).strip()
                        value = re.sub(r'<[^>]+>', '', value)
                        return value[:1000] if not multiline else value[:2000]
                    return ""
                
                data["country"] = extract_field(r'Country', page_text_visible) or extract_field(r'Country', page_text)
                data["field_of_operation"] = extract_field(r'Field of operation', page_text_visible) or extract_field(r'Field of operation', page_text)
                data["product_category"] = extract_field(r'Product category', page_text_visible) or extract_field(r'Product category', page_text)
            
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
            
            # CB Client number - amélioré
            cb_patterns = [
                r'CB Client number[:\s]+([\d-]+)',
                r'CB[-\s]?Client[-\s]?number[:\s]+([\d-]+)',
                r'Client number[:\s]+([\d-]+)',
                r'CB Client[:\s]+([\d-]+)'
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
            
            # Certification Body - amélioré
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
            if not data["certification_body"]:
                match = re.search(r'Certification Body[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r'<[^>]+>', '', value)
                    data["certification_body"] = value[:200]
            
            # Certificate Expiry Date - amélioré
            expiry_patterns = [
                r'Certificate Expiry Date[:\s]+([\d-]+)',
                r'Expiry Date[:\s]+([\d-]+)',
                r'Expires[:\s]+([\d-]+)',
                r'Certificate[:\s]+Expiry[:\s]+Date[:\s]+([\d-]+)'
            ]
            for pattern in expiry_patterns:
                match = re.search(pattern, page_text_visible, re.IGNORECASE)
                if match:
                    data["certificate_expiry_date"] = match.group(1).strip()
                    break
            if not data["certificate_expiry_date"]:
                for pattern in expiry_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        data["certificate_expiry_date"] = match.group(1).strip()
                        break
            
            # Address - peut contenir plusieurs lignes
            address_patterns = [
                r'Address[:\s]+([^<]+?)(?:\n|State|Postcode|Certification)',
                r'Address[:\s]+([^<\n]+)'
            ]
            for pattern in address_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    addr = match.group(1).strip()
                    addr = re.sub(r'<[^>]+>', '', addr)
                    # Combiner avec State et Postcode si disponibles
                    state_match = re.search(r'State[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                    postcode_match = re.search(r'Postcode[:\s]+([^<\n]+)', page_text, re.IGNORECASE)
                    if state_match:
                        addr += f", {state_match.group(1).strip()}"
                    if postcode_match:
                        addr += f", {postcode_match.group(1).strip()}"
                    data["address"] = addr[:500]
                    break
            
            # Product details - section "OTHER DATA"
            try:
                # Chercher toutes les sections qui contiennent "Product details" ou "OTHER DATA"
                sections = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Product details') or contains(text(), 'OTHER DATA')]")
                if sections:
                    for section in sections:
                        try:
                            # Obtenir le conteneur parent
                            parent = section.find_element(By.XPATH, "./ancestor::div[1]")
                            product_text = parent.text
                            if "Product details" in product_text or "OTHER DATA" in product_text:
                                # Extraire tout le texte après "Product details"
                                parts = product_text.split("Product details")
                                if len(parts) > 1:
                                    data["product_details"] = parts[1].strip()[:2000]
                                else:
                                    data["product_details"] = product_text.strip()[:2000]
                                break
                        except:
                            continue
                
                # Fallback: extraction par regex
                if not data["product_details"]:
                    product_match = re.search(r'Product details[:\s]+([^<]+)', page_text, re.IGNORECASE | re.DOTALL)
                    if product_match:
                        product_text = product_match.group(1).strip()
                        product_text = re.sub(r'<[^>]+>', '', product_text)
                        data["product_details"] = product_text[:2000]
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction des détails produits: {e}")
            
            logger.info(f"Données extraites pour: {data['company_name']}")
            return data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données: {e}")
            return data
    
    def process_pdf(self, pdf_path):
        """
        Traite un PDF: extrait le numéro et vérifie la certification
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            dict: Résultats de la vérification
        """
        cert_number = self.extract_certification_number_from_pdf(pdf_path)
        if not cert_number:
            return {
                "found": False,
                "error": "Numéro de certification non trouvé dans le PDF",
                "pdf_path": str(pdf_path)
            }
        
        return self.search_certification(cert_number)
    
    def close(self):
        """Ferme le driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver fermé")


def create_excel_output(results, output_path="verification_results.xlsx", append=False):
    """
    Crée ou met à jour un fichier Excel avec les résultats de vérification
    
    Args:
        results: Liste de dictionnaires contenant les résultats
        output_path: Chemin du fichier Excel de sortie
        append: Si True, ajoute les résultats à un fichier existant. Si False, crée un nouveau fichier.
    """
    # Préparer les données pour le DataFrame
    excel_data = []
    
    for result in results:
        row = {
            "Company name": result.get("company_name", ""),
            "Certification Number": result.get("certification_number", ""),
            "Found?": "Yes" if result.get("found", False) else "No",
            "Country": result.get("country", "") if result.get("found", False) else "",
            "Field of operation": result.get("field_of_operation", "") if result.get("found", False) else "",
            "Product category": result.get("product_category", "") if result.get("found", False) else "",
            "CB Client number": result.get("cb_client_number", "") if result.get("found", False) else "",
            "Certification Body": result.get("certification_body", "") if result.get("found", False) else "",
            "Certificate Expiry Date": result.get("certificate_expiry_date", "") if result.get("found", False) else "",
            "Address": result.get("address", "") if result.get("found", False) else "",
            "Product details": result.get("product_details", "") if result.get("found", False) else ""
        }
        excel_data.append(row)
    
    # Créer le DataFrame
    df_new = pd.DataFrame(excel_data)
    
    # Si append est True et que le fichier existe, charger les données existantes
    if append and Path(output_path).exists():
        try:
            df_existing = pd.read_excel(output_path, engine='openpyxl')
            # Concaténer les nouvelles données avec les existantes
            df = pd.concat([df_existing, df_new], ignore_index=True)
            logger.info(f"Ajout de {len(df_new)} ligne(s) au fichier existant: {output_path}")
        except Exception as e:
            logger.warning(f"Impossible de lire le fichier existant: {e}. Création d'un nouveau fichier.")
            df = df_new
    else:
        df = df_new
    
    # Sauvegarder le DataFrame
    df.to_excel(output_path, index=False, engine='openpyxl')
    logger.info(f"Fichier Excel {'mis à jour' if append and Path(output_path).exists() else 'créé'}: {output_path} ({len(df)} ligne(s) au total)")
    return output_path


if __name__ == "__main__":
    # Exemple d'utilisation
    crawler = GOTSCrawler(headless=False)
    
    try:
        # Exemple: traiter un PDF
        pdf_path = Path("../Original files/Template Certification GOTS.pdf")
        if pdf_path.exists():
            result = crawler.process_pdf(pdf_path)
            print(f"Résultat: {result}")
            
            # Créer le fichier Excel
            create_excel_output([result], "verification_results.xlsx")
        else:
            print(f"Fichier PDF non trouvé: {pdf_path}")
    
    finally:
        crawler.close()

