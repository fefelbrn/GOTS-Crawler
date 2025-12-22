"""
Exemple d'utilisation simple du crawler GOTS
"""

from pathlib import Path
from gots_crawler import GOTSCrawler, create_excel_output
import logging

logging.basicConfig(level=logging.INFO)

def example_single_pdf():
    """Exemple: vérifier une certification depuis un PDF"""
    crawler = GOTSCrawler(headless=False)
    
    try:
        # Chemin vers le PDF de certification
        pdf_path = Path("../Original files/Template Certification GOTS - 10DAYS Wholesale BV.pdf")
        
        if pdf_path.exists():
            print(f"Traitement du PDF: {pdf_path.name}")
            result = crawler.process_pdf(pdf_path)
            
            print(f"\nRésultat:")
            print(f"  Trouvé: {result.get('found', False)}")
            print(f"  Compagnie: {result.get('company_name', 'N/A')}")
            print(f"  Numéro de certification: {result.get('certification_number', 'N/A')}")
            
            # Créer le fichier Excel
            create_excel_output([result], "example_result.xlsx")
            print(f"\nRésultats sauvegardés dans example_result.xlsx")
        else:
            print(f"Fichier PDF non trouvé: {pdf_path}")
    
    finally:
        crawler.close()


def example_direct_search(certification_numbers, output_file="all_search_results.xlsx"):
    """
    Recherche plusieurs certifications et accumule les résultats dans un seul fichier Excel
    
    Args:
        certification_numbers: Liste de numéros de certification à rechercher
        output_file: Nom du fichier Excel de sortie (unique pour tous les résultats)
    """
    crawler = GOTSCrawler(headless=False)
    all_results = []
    
    try:
        for idx, cert_number in enumerate(certification_numbers, 1):
            print(f"\n{'='*50}")
            print(f"Recherche {idx}/{len(certification_numbers)}: {cert_number}")
            print(f"{'='*50}")
            
            result = crawler.search_certification(cert_number)
            all_results.append(result)
            
            print(f"\nRésultat:")
            print(f"  Trouvé: {result.get('found', False)}")
            if result.get('found'):
                print(f"  Compagnie: {result.get('company_name', 'N/A')}")
                print(f"  Pays: {result.get('country', 'N/A')}")
                print(f"  Date d'expiration: {result.get('certificate_expiry_date', 'N/A')}")
                print(f"  Numéro de certification: {result.get('certification_number', 'N/A')}")
                print(f"  CB Client number: {result.get('cb_client_number', 'N/A')}")
            else:
                print(f"  Erreur: {result.get('error', 'Non trouvé')}")
            
            # Ajouter au fichier Excel (append=True après la première recherche)
            append_mode = (idx > 1) or Path(output_file).exists()
            create_excel_output([result], output_file, append=append_mode)
        
        print(f"\n{'='*50}")
        print(f"Toutes les recherches terminées!")
        print(f"Total: {len(all_results)} recherche(s)")
        print(f"Trouvées: {sum(1 for r in all_results if r.get('found', False))}")
        print(f"Non trouvées: {sum(1 for r in all_results if not r.get('found', False))}")
        print(f"\nTous les résultats sont dans: {output_file}")
    
    finally:
        crawler.close()


if __name__ == "__main__":
    # Liste des numéros de certification à rechercher
    certification_numbers = ["21205", "21204"]
    
    print("Recherche de plusieurs certifications")
    print("=" * 50)
    example_direct_search(certification_numbers)

