import os
import json
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
        "\n=== SYNTHESE GLOBALE ===\n"
    )

    try:

        synthese = synthese_globale(
            historique
        )

        print(synthese)

        os.makedirs(
            "output",
            exist_ok=True
        )

        with open(
            "output/synthese_ia.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write(synthese)

    except Exception as error:

        print(
            f"Erreur synthèse : {error}"
        )


if __name__ == "__main__":
    main()