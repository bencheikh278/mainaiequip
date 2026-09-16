import json
import os

from extract import extract_text
from analyse import decouper, compter_champs_remplis, TITRES

DOSSIERS = ["data/reports_txt","data/reports_pdf"]


def main():
    tous_les_rapports = []

    for dossier in DOSSIERS:
        if not os.path.isdir(dossier):
            continue

        for nom in sorted(os.listdir(dossier)):
            chemin = os.path.join(dossier, nom)
            texte = extract_text(chemin)

            if len(texte.strip()) < 30:
                print(nom, ": vide ou illisible, ignore")
                continue

            donnees = decouper(texte)
            donnees["fichier"] = nom
            tous_les_rapports.append(donnees)

            remplis = compter_champs_remplis(donnees)
            print(nom, ":", remplis, "/", len(TITRES), "champs trouves")

    os.makedirs("output", exist_ok=True)
    with open("output/dataset.json", "w", encoding="utf-8") as f:
        json.dump(tous_les_rapports, f, ensure_ascii=False, indent=2)

    print()
    print(len(tous_les_rapports), "rapports -> output/dataset.json")


if __name__ == "__main__":
    main()