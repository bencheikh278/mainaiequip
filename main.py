from extract import extract_text
from analyse import decouper 
import json

texte = extract_text("data/reports_pdf/000.pdf")
donnees = decouper(texte)
print(json.dumps(donnees, ensure_ascii=False, indent=1))