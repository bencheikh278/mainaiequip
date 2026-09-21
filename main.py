import os
import hashlib
from datetime import datetime

import bdd

from extract import extract_text
from agent import analyser_rapport, synthese_globale


# CALCULER LE HASH DU CONTENU POUR VOIR C'EST LE FICHIER DEJA EXIST OU PAS 

def calculer_hash(texte):


    contenu = texte.encode(
        "utf-8"
    )

    hash_sha256 = hashlib.sha256(
        contenu
    ).hexdigest()

    return hash_sha256


# ============================================================
# ANALYSER LES DOSSIERS
# ============================================================

def analyser_dossier(*dossiers):

    connexion = bdd.connecter()

   #LES RAPPORT UTULISER 
    rapports_selectionnes = []

   
    for dossier in dossiers:

        if not os.path.isdir(
            dossier
        ):

            print(
                f"{dossier} : dossier introuvable"
            )

            continue

        for nom_fichier in sorted(
            os.listdir(dossier)
        ):

            chemin = os.path.join(
                dossier,
                nom_fichier
            )

          
            if not os.path.isfile(
                chemin
            ):

                continue

            #EXTRACTION DE TEXT 
            print(
                f"\n{nom_fichier} : extraction..."
            )

            try:

                texte = extract_text(
                    chemin
                )

            except Exception as error:

                print(
                    f"{nom_fichier} : "
                    f"erreur extraction : {error}"
                )

                continue

           
            if not texte:

                print(
                    f"{nom_fichier} : "
                    f"fichier vide ou illisible"
                )

                continue

            if len(
                texte.strip()
            ) < 30:

                print(
                    f"{nom_fichier} : "
                    f"fichier vide ou illisible"
                )

                continue

            #CALCULER LE HASH
            hash_contenu = calculer_hash(
                texte
            )

            print(
                f"{nom_fichier} : "
                f"hash = {hash_contenu[:12]}..."
            )

            #VERIFY IF THE RAPPORT DEJA ANALISED
            if bdd.rapport_existe_par_hash(
                connexion,
                hash_contenu
            ):

                print(
                    f"{nom_fichier} : "
                    f"contenu déjà analysé"
                )

                donnees_existantes = (
                    bdd.recuperer_rapport_par_hash(
                        connexion,
                        hash_contenu
                    )
                )

             
                if donnees_existantes:

                   
                    donnees_existantes[
                        "fichier"
                    ] = nom_fichier

                    rapports_selectionnes.append(
                        donnees_existantes
                    )

                continue

            #NEW CONTENT
            print(
                f"{nom_fichier} : "
                f"nouveau contenu"
            )

            print(
                f"{nom_fichier} : "
                f"analyse IA..."
            )

            try:

                donnees = analyser_rapport(
                    texte
                )

            except Exception as error:

                print(
                    f"{nom_fichier} : "
                    f"Erreur IA : {error}"
                )

                continue

            #AJOUTER LES INFO DE FICHIER
            donnees[
                "fichier"
            ] = nom_fichier

            donnees[
                "hash_contenu"
            ] = hash_contenu

            donnees[
                "analyse_le"
            ] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # =================================================
            # SAUVEGARDER DANS SQLITE
            # =================================================

            bdd.inserer_rapport(
                connexion,
                donnees
            )

            # =================================================
            # AJOUTER À LA SYNTHÈSE
            # =================================================

            rapports_selectionnes.append(
                donnees
            )

            print(
                f"{nom_fichier} : terminé"
            )

    # ========================================================
    # FERMER SQLITE
    # ========================================================

    connexion.close()

    return rapports_selectionnes


# ============================================================
#                    PROGRAMME PRINCIPAL
# ============================================================

def main():

    # ========================================================
    # 1. ANALYSER 
    # ========================================================

    rapports_selectionnes = analyser_dossier(

        "data/reports_txt" )

    #AUCUN RAPPORT
    if not rapports_selectionnes:

        print(
            "\nAucun rapport à analyser."
        )

        return

    print(
        f"\nRapports utilisés pour cette analyse : "
        f"{len(rapports_selectionnes)}"
    )

    # ========================================================
    # 2. RÉCUPÉRER L'HISTORIQUE
    # ========================================================

    connexion = bdd.connecter()

    historique = bdd.recuperer_historique(
        connexion
    )

    connexion.close()

    print(
        f"Historique total dans SQLite : "
        f"{len(historique)} rapports"
    )

    # ========================================================
    # 3. SYNTHÈSE + RECOMMANDATIONS
    # ========================================================

    print(
        "\nGénération de la synthèse "
        "et des recommandations..."
    )

    try:

        synthese = synthese_globale(
            rapports_selectionnes,
            historique
        )

        # ====================================================
        # CRÉER OUTPUT
        # ====================================================

        os.makedirs(
            "output",
            exist_ok=True
        )

        # ====================================================
        # SAUVEGARDER LA SYNTHÈSE
        # ====================================================

        with open(
            "output/synthese_interventions.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "=== SYNTHESE DES INTERVENTIONS ===\n\n"
            )

            for item in synthese[
                "synthese_interventions"
            ]:

                file.write(
                    f"{item['equipement']} "
                    f"({item['nb_interventions']} "
                    f"intervention(s))\n"
                )

                file.write(
                    f"  {item['resume']}\n\n"
                )

        # ====================================================
        # SAUVEGARDER LES RECOMMANDATIONS
        # ====================================================

        with open(
            "output/recommandations.txt",
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "=== RECOMMANDATIONS ===\n\n"
            )

            for recommandation in synthese[
                "recommandations"
            ]:

                file.write(
                    f"[{recommandation['priorite'].upper()}] "
                    f"{recommandation['equipement']}\n"
                )

                file.write(
                    f"  Action : "
                    f"{recommandation['action']}\n"
                )

                file.write(
                    f"  Justification : "
                    f"{recommandation['justification']}\n\n"
                )

        # ====================================================
        # AFFICHER LA SYNTHÈSE
        # ====================================================

        print(
            "\n=== SYNTHESE DES INTERVENTIONS ===\n"
        )

        for item in synthese[
            "synthese_interventions"
        ]:

            print(
                f"{item['equipement']} "
                f"({item['nb_interventions']} "
                f"intervention(s))"
            )

            print(
                f"  {item['resume']}\n"
            )

        # ====================================================
        # AFFICHER LES RECOMMANDATIONS
        # ====================================================

        print(
            "=== RECOMMANDATIONS ===\n"
        )

        for recommandation in synthese[
            "recommandations"
        ]:

            print(
                f"[{recommandation['priorite'].upper()}] "
                f"{recommandation['equipement']}"
            )

            print(
                f"  Action : "
                f"{recommandation['action']}"
            )

            print(
                f"  Justification : "
                f"{recommandation['justification']}\n"
            )

        # ====================================================
        # FICHIERS CRÉÉS
        # ====================================================

        print(
            "Fichiers générés :"
        )

        print(
            "synthese_interventions.txt"
        )

        print(
            "recommandations.txt"
        )

    except Exception as error:

        print(
            f"Erreur synthèse : {error}"
        )


if __name__ == "__main__":
    main()