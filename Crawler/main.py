"""
Script principal pour vérifier les certifications GOTS
Lit un fichier Excel avec les suppliers, traite les PDFs de certification,
et génère un fichier Excel avec les résultats de vérification
"""

import pandas as pd
from pathlib import Path
import logging
from gots_crawler import GOTSCrawler, create_excel_output
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_suppliers_excel(excel_path, pdf_folder=None):
    """
    Traite le fichier Excel des suppliers et vérifie leurs certifications
    
    Args:
        excel_path: Chemin vers le fichier Excel des suppliers
        pdf_folder: Dossier contenant les PDFs de certification (optionnel)
    
    Returns:
        list: Liste des résultats de vérification
    """
    try:
        # Lire le fichier Excel
        df = pd.read_excel(excel_path)
        logger.info(f"Fichier Excel lu: {len(df)} lignes trouvées")
        logger.info(f"Colonnes: {df.columns.tolist()}")
        
        # Initialiser le crawler
        crawler = GOTSCrawler(headless=False)
        results = []
        
        try:
            # Parcourir chaque ligne du DataFrame
            for idx, row in df.iterrows():
                logger.info(f"\n{'='*50}")
                logger.info(f"Traitement de la ligne {idx + 1}/{len(df)}")
                
                # Vérifier si le numéro de certification est déjà dans l'Excel
                cert_number = None
                cert_columns = ['Certification Number', 'Certification', 'License Number', 'CB Client number', 'GOTS Number']
                for col in cert_columns:
                    if col in row and pd.notna(row[col]):
                        cert_number = str(row[col]).strip()
                        logger.info(f"Numéro de certification trouvé dans l'Excel: {cert_number}")
                        break
                
                # Si pas de numéro dans l'Excel, chercher dans un PDF
                if not cert_number:
                    pdf_path = None
                    
                    if pdf_folder:
                        pdf_folder_path = Path(pdf_folder)
                        # Chercher un PDF qui pourrait correspondre à ce supplier
                        company_name = str(row.get('Company', row.get('Company Name', ''))).strip()
                        if company_name:
                            # Chercher un PDF avec un nom similaire
                            for pdf_file in pdf_folder_path.glob("*.pdf"):
                                if company_name.lower() in pdf_file.stem.lower() or pdf_file.stem.lower() in company_name.lower():
                                    pdf_path = pdf_file
                                    break
                    
                    # Si pas de PDF trouvé, utiliser le template par défaut
                    if not pdf_path:
                        default_pdf = Path("../Original files/Template Certification GOTS.pdf")
                        if default_pdf.exists():
                            pdf_path = default_pdf
                            logger.info(f"Utilisation du PDF template par défaut")
                    
                    if pdf_path and pdf_path.exists():
                        logger.info(f"Traitement du PDF: {pdf_path.name}")
                        cert_number = crawler.extract_certification_number_from_pdf(pdf_path)
                
                # Rechercher la certification
                if cert_number:
                    result = crawler.search_certification(cert_number)
                else:
                    logger.warning(f"Aucun numéro de certification trouvé pour la ligne {idx + 1}")
                    result = {
                        "found": False,
                        "error": "Numéro de certification non trouvé",
                        "certification_number": ""
                    }
                
                # Ajouter des informations du supplier depuis l'Excel
                if 'Company' in row or 'Company Name' in row:
                    result['supplier_company'] = row.get('Company', row.get('Company Name', ''))
                    # Si le nom de la compagnie n'a pas été trouvé dans les détails, utiliser celui de l'Excel
                    if not result.get('company_name'):
                        result['company_name'] = result['supplier_company']
                
                results.append(result)
                
                # Pause entre les requêtes pour ne pas surcharger le serveur
                time.sleep(2)
        
        finally:
            crawler.close()
        
        return results
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement de l'Excel: {e}")
        raise


def process_single_pdf(pdf_path):
    """
    Traite un seul PDF de certification
    
    Args:
        pdf_path: Chemin vers le fichier PDF
    
    Returns:
        dict: Résultat de la vérification
    """
    crawler = GOTSCrawler(headless=False)
    try:
        result = crawler.process_pdf(pdf_path)
        return result
    finally:
        crawler.close()


def main():
    """Fonction principale"""
    # Chemins des fichiers
    excel_path = Path("../Original files/UC4_Suppliers datasets.xlsx")
    pdf_folder = Path("../Original files")
    output_path = Path("verification_results.xlsx")
    
    logger.info("Démarrage de la vérification des certifications GOTS")
    logger.info(f"Fichier Excel source: {excel_path}")
    logger.info(f"Dossier PDFs: {pdf_folder}")
    logger.info(f"Fichier de sortie: {output_path}")
    
    # Vérifier que le fichier Excel existe
    if not excel_path.exists():
        logger.error(f"Fichier Excel non trouvé: {excel_path}")
        logger.info("Tentative avec un seul PDF...")
        
        # Mode simple: traiter juste le template PDF
        template_pdf = Path("../Original files/Template Certification GOTS.pdf")
        if template_pdf.exists():
            result = process_single_pdf(template_pdf)
            create_excel_output([result], output_path)
            logger.info(f"Résultats sauvegardés dans {output_path}")
        else:
            logger.error("Aucun fichier à traiter trouvé")
        return
    
    # Traiter le fichier Excel
    try:
        results = process_suppliers_excel(excel_path, pdf_folder)
        
        # Créer le fichier Excel de sortie
        create_excel_output(results, output_path)
        logger.info(f"\n{'='*50}")
        logger.info(f"Vérification terminée!")
        logger.info(f"Résultats sauvegardés dans: {output_path}")
        logger.info(f"Total traité: {len(results)}")
        logger.info(f"Certifications trouvées: {sum(1 for r in results if r.get('found', False))}")
        logger.info(f"Certifications non trouvées: {sum(1 for r in results if not r.get('found', False))}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution: {e}")
        raise


if __name__ == "__main__":
    main()

