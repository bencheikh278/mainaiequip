import os
import json
import textwrap
from datetime import datetime

from extract import extract_text
from agent import analyser_rapport, synthese_globale


FICHIER_HISTORIQUE = "output/historique.json"


def charger_historique():

    if not os.path.exists(FICHIER_HISTORIQUE):
        return []

    with open(
        FICHIER_HISTORIQUE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def sauvegarder_historique(historique):

    os.makedirs("output", exist_ok=True)

    with open(
        FICHIER_HISTORIQUE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            historique,
            file,
            ensure_ascii=False,
            indent=2
        )


def analyser_dossier(*dossiers):

    historique = charger_historique()

    fichiers_deja_connus = {
        rapport["fichier"]
        for rapport in historique
    }

    for dossier in dossiers:

        if not os.path.isdir(dossier):

            print(
                f"{dossier} : dossier introuvable"
            )

            continue

        for nom_fichier in sorted(
            os.listdir(dossier)
        ):

            if nom_fichier in fichiers_deja_connus:

                print(
                    f"{nom_fichier} : déjà analysé"
                )

                continue

            chemin = os.path.join(
                dossier,
                nom_fichier
            )

            print(
                f"{nom_fichier} : extraction..."
            )

            texte = extract_text(chemin)

            if not texte:

                print(
                    f"{nom_fichier} : format non supporté"
                )

                continue

            if len(texte.strip()) < 30:

                print(
                    f"{nom_fichier} : fichier vide ou illisible"
                )

                continue

            print(
                f"{nom_fichier} : analyse IA..."
            )

            try:

                donnees = analyser_rapport(
                    texte
                )

            except Exception as error:

                print(
                    f"Erreur : {error}"
                )

                continue

            donnees["fichier"] = nom_fichier

            donnees["analyse_le"] = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            historique.append(donnees)

            fichiers_deja_connus.add(
                nom_fichier
            )

            sauvegarder_historique(
                historique
            )

            print(
                f"{nom_fichier} : terminé"
            )

    return historique


def main():

    historique = analyser_dossier(
        "data/reports_txt",
        "data/reports_pdf",
        "data/reports_docx"
    )

    print(
        f"\nNombre de rapports : {len(historique)}"
    )

    if not historique:

        print("Aucun rapport à analyser.")

        return

    print(
        "\nGénération de la synthèse et des recommandations..."
    )

    try:

        synthese = synthese_globale(
            historique
        )

        os.makedirs(
            "output",
            exist_ok=True
        )

        # livrable 1 : synthese des interventions realisees, par equipement
        with open(
            "output/synthese_interventions.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write("=== SYNTHESE DES INTERVENTIONS ===\n\n")

            for item in synthese["synthese_interventions"]:

                file.write(
                    f"{item['equipement']} ({item['nb_interventions']} intervention(s))\n"
                )

                resume_formate = textwrap.fill(
                    item['resume'],
                    width=80,
                    initial_indent="  ",
                    subsequent_indent="  "
                )

                file.write(f"{resume_formate}\n\n")

        # livrable 2 : recommandations, priorisees
        with open(
            "output/recommandations.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write("=== RECOMMANDATIONS ===\n\n")

            for r in synthese["recommandations"]:

                file.write(
                    f"[{r['priorite'].upper()}] {r['equipement']}\n"
                )
                file.write(
                    f"  Action : {r['action']}\n"
                )
                file.write(
                    f"  Justification : {r['justification']}\n\n"
                )

        print(
            "\n=== SYNTHESE DES INTERVENTIONS ===\n"
        )
        for item in synthese["synthese_interventions"]:
            print(
                f"{item['equipement']} ({item['nb_interventions']} intervention(s))"
            )
            resume_formate = textwrap.fill(
                item['resume'],
                width=80,
                initial_indent="  ",
                subsequent_indent="  "
            )
            print(f"{resume_formate}\n")

        print(
            "=== RECOMMANDATIONS ===\n"
        )
        for r in synthese["recommandations"]:
            print(
                f"[{r['priorite'].upper()}] {r['equipement']} : {r['action']}"
            )

        print(
            "\n-> output/synthese_interventions.txt"
        )
        print(
            "-> output/recommandations.txt"
        )

    except Exception as error:

        print(
            f"Erreur synthèse : {error}"
        )


if __name__ == "__main__":
    main()