# GOTS Certification Crawler

Crawler Python pour vérifier automatiquement les certifications GOTS (Global Organic Textile Standard) des suppliers textiles.

## Fonctionnalités

- Extraction du numéro de certification depuis les PDFs de certification
- Recherche automatique sur la base de données GOTS
- Vérification de la validité des certifications
- Extraction complète des données de certification
- Génération d'un fichier Excel avec les résultats

## Installation

1. Installer les dépendances Python :
```bash
pip install -r requirements.txt
```

2. Installer ChromeDriver :
   - Télécharger ChromeDriver depuis https://chromedriver.chromium.org/
   - Ou utiliser `webdriver-manager` (déjà inclus dans requirements.txt)

## Structure du projet

```
Crawler/
├── gots_crawler.py      # Classe principale du crawler
├── main.py              # Script principal d'exécution
├── requirements.txt     # Dépendances Python
└── README.md           # Ce fichier
```

## Utilisation

### Mode simple (un seul PDF)

```python
from gots_crawler import GOTSCrawler, create_excel_output
from pathlib import Path

crawler = GOTSCrawler(headless=False)
result = crawler.process_pdf(Path("path/to/certification.pdf"))
create_excel_output([result], "results.xlsx")
crawler.close()
```

### Mode batch (fichier Excel + PDFs)

```bash
python main.py
```

Le script `main.py` va :
1. Lire le fichier Excel des suppliers (`../Original files/UC4_Suppliers datasets.xlsx`)
2. Pour chaque supplier, chercher et traiter le PDF de certification correspondant
3. Générer un fichier Excel `verification_results.xlsx` avec les résultats

## Format du fichier Excel de sortie

Le fichier Excel généré contient les colonnes suivantes :

- **Company name** : Nom de la compagnie
- **Certification Number** : Numéro de certification
- **Found?** : Oui/Non selon si la certification a été trouvée
- **Country** : Pays
- **Field of operation** : Domaine d'opération
- **Product category** : Catégorie de produits
- **CB Client number** : Numéro client CB
- **Certification Body** : Organisme de certification
- **Certificate Expiry Date** : Date d'expiration
- **Address** : Adresse
- **Product details** : Détails des produits certifiés

## Notes importantes

- Le crawler utilise Selenium pour interagir avec le site web GOTS
- Des pauses sont ajoutées entre les requêtes pour ne pas surcharger le serveur
- Si une certification n'est pas trouvée, les colonnes suivantes restent vides
- Le mode `headless=False` permet de voir le navigateur (utile pour le débogage)

## Dépannage

### ChromeDriver non trouvé
Installer ChromeDriver ou utiliser `webdriver-manager` :
```python
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
```

### Aucun résultat trouvé
- Vérifier que le numéro de certification est correctement extrait du PDF
- Essayer de rechercher manuellement sur le site pour vérifier
- Le site peut avoir changé sa structure HTML

## Auteur

Créé pour le hackathon GOTS

