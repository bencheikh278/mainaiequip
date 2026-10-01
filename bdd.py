import sqlite3
import os


CHEMIN_DB = "output/synia.db"


# ============================================================
# CONNEXION SQLITE
# ============================================================

def connecter():

    os.makedirs(
        "output",
        exist_ok=True
    )

    connexion = sqlite3.connect(
        CHEMIN_DB
    )

    connexion.execute(
        "PRAGMA foreign_keys = ON"
    )

    # ========================================================
    # RAPPORTS
    # ========================================================

    connexion.execute("""
        CREATE TABLE IF NOT EXISTS rapports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            fichier TEXT NOT NULL,

            hash_contenu TEXT UNIQUE NOT NULL,

            reference TEXT,

            date TEXT,

            analyse_le TEXT
        )
    """)

    # ========================================================
    # EQUIPEMENTS
    # ========================================================

    connexion.execute("""
        CREATE TABLE IF NOT EXISTS equipements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            rapport_id INTEGER NOT NULL,

            nom TEXT,

            type TEXT,

            description TEXT,

            causes TEXT,

            interventions_realisees TEXT,

            interventions_planifiees TEXT,

            resultats TEXT,

            recommandations TEXT,

            FOREIGN KEY (rapport_id)
            REFERENCES rapports(id)
            ON DELETE CASCADE
        )
    """)

    # ========================================================
    # ANOMALIES
    # ========================================================

    connexion.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            equipement_id INTEGER NOT NULL,

            description TEXT,

            niveau TEXT,

            statut TEXT,

            FOREIGN KEY (equipement_id)
            REFERENCES equipements(id)
            ON DELETE CASCADE
        )
    """)

    connexion.commit()

    return connexion


# ============================================================
# VERIFIER HASH
# ============================================================

def rapport_existe_par_hash(
    connexion,
    hash_contenu
):

    resultat = connexion.execute(
        """
        SELECT 1
        FROM rapports
        WHERE hash_contenu = ?
        """,
        (hash_contenu,)
    ).fetchone()

    return resultat is not None


# ============================================================
# INSERER UN RAPPORT
# ============================================================

def inserer_rapport(
    connexion,
    donnees
):

    fichier = donnees.get(
        "fichier"
    )

    hash_contenu = donnees.get(
        "hash_contenu"
    )

    # --------------------------------------------------------
    # Vérifier doublon
    # --------------------------------------------------------

    if rapport_existe_par_hash(
        connexion,
        hash_contenu
    ):

        print(
            f"[BDD] Rapport déjà présent : {fichier}"
        )

        return

    # --------------------------------------------------------
    # Insérer rapport
    # --------------------------------------------------------

    curseur = connexion.execute(
        """
        INSERT INTO rapports
        (
            fichier,
            hash_contenu,
            reference,
            date,
            analyse_le
        )

        VALUES (?, ?, ?, ?, ?)
        """,
        (
            fichier,
            hash_contenu,
            donnees.get("reference"),
            donnees.get("date"),
            donnees.get("analyse_le")
        )
    )

    rapport_id = curseur.lastrowid

    # --------------------------------------------------------
    # Les analyses viennent de "analyses"
    # --------------------------------------------------------

    analyses = donnees.get(
        "analyses",
        []
    )

    for analyse in analyses:

        nom = analyse.get(
            "equipement"
        )

        description = analyse.get(
            "description"
        )

        causes = analyse.get(
            "causes",
            []
        )

        interventions_realisees = analyse.get(
            "interventions_realisees",
            []
        )

        interventions_planifiees = analyse.get(
            "interventions_planifiees",
            []
        )

        resultats = analyse.get(
            "resultats",
            []
        )

        recommandations = analyse.get(
            "recommandations",
            []
        )

        # ----------------------------------------------------
        # Type
        # ----------------------------------------------------

        type_equipement = analyse.get(
            "type"
        )

        # ----------------------------------------------------
        # Convertir recommandations en texte
        # ----------------------------------------------------

        recommandations_text = []

        for rec in recommandations:

            if isinstance(rec, dict):

                action = rec.get(
                    "action",
                    ""
                )

                priorite = rec.get(
                    "priorite",
                    ""
                )

                if priorite:

                    recommandations_text.append(
                        f"{action} ({priorite})"
                    )

                else:

                    recommandations_text.append(
                        action
                    )

            else:

                recommandations_text.append(
                    str(rec)
                )

        # ----------------------------------------------------
        # INSERTION EQUIPEMENT
        # ----------------------------------------------------

        curseur_eq = connexion.execute(
            """
            INSERT INTO equipements
            (
                rapport_id,
                nom,
                type,
                description,
                causes,
                interventions_realisees,
                interventions_planifiees,
                resultats,
                recommandations
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rapport_id,

                nom,

                type_equipement,

                description,

                " | ".join(
                    str(x)
                    for x in causes
                ),

                " | ".join(
                    str(x)
                    for x in interventions_realisees
                ),

                " | ".join(
                    str(x)
                    for x in interventions_planifiees
                ),

                " | ".join(
                    str(x)
                    for x in resultats
                ),

                " | ".join(
                    recommandations_text
                )
            )
        )

        equipement_id = curseur_eq.lastrowid

        # ----------------------------------------------------
        # ANOMALIES
        # ----------------------------------------------------

        anomalies = analyse.get(
            "anomalies",
            []
        )

        for anomalie in anomalies:

            if not isinstance(
                anomalie,
                dict
            ):
                continue

            connexion.execute(
                """
                INSERT INTO anomalies
                (
                    equipement_id,
                    description,
                    niveau,
                    statut
                )

                VALUES (?, ?, ?, ?)
                """,
                (
                    equipement_id,

                    anomalie.get(
                        "description"
                    ),

                    anomalie.get(
                        "niveau"
                    ),

                    anomalie.get(
                        "statut"
                    )
                )
            )

    connexion.commit()

    print(
        f"[BDD] Rapport enregistré : {fichier}"
    )


# ============================================================
# RECUPERER UN RAPPORT
# ============================================================

def recuperer_rapport_par_hash(
    connexion,
    hash_contenu
):

    rapport = connexion.execute(
        """
        SELECT
            id,
            fichier,
            hash_contenu,
            reference,
            date,
            analyse_le

        FROM rapports

        WHERE hash_contenu = ?
        """,
        (hash_contenu,)
    ).fetchone()

    if not rapport:

        return None

    rapport_id = rapport[0]

    donnees = {

        "fichier": rapport[1],

        "hash_contenu": rapport[2],

        "reference": rapport[3],

        "date": rapport[4],

        "analyse_le": rapport[5],

        "analyses": []
    }

    # --------------------------------------------------------
    # EQUIPMENTS
    # --------------------------------------------------------

    equipements = connexion.execute(
        """
        SELECT
            id,
            nom,
            type,
            description,
            causes,
            interventions_realisees,
            interventions_planifiees,
            resultats,
            recommandations

        FROM equipements

        WHERE rapport_id = ?
        """,
        (rapport_id,)
    ).fetchall()

    for eq in equipements:

        equipement_id = eq[0]

        # ----------------------------------------------------
        # ANOMALIES
        # ----------------------------------------------------

        anomalies_sql = connexion.execute(
            """
            SELECT
                description,
                niveau,
                statut

            FROM anomalies

            WHERE equipement_id = ?
            """,
            (equipement_id,)
        ).fetchall()

        anomalies = []

        for anomalie in anomalies_sql:

            anomalies.append({

                "description": anomalie[0],

                "niveau": anomalie[1],

                "statut": anomalie[2]
            })

        # ----------------------------------------------------
        # RECONSTRUIRE
        # ----------------------------------------------------

        causes = (
            eq[4].split(" | ")
            if eq[4]
            else []
        )

        interventions_realisees = (
            eq[5].split(" | ")
            if eq[5]
            else []
        )

        interventions_planifiees = (
            eq[6].split(" | ")
            if eq[6]
            else []
        )

        resultats = (
            eq[7].split(" | ")
            if eq[7]
            else []
        )

        recommandations_brutes = (
            eq[8].split(" | ")
            if eq[8]
            else []
        )

        recommandations = []

        for rec in recommandations_brutes:

            recommandations.append({
                "action": rec
            })

        donnees["analyses"].append({

            "equipement": eq[1],

            "type": eq[2],

            "description": eq[3],

            "anomalies": anomalies,

            "causes": causes,

            "interventions_realisees":
                interventions_realisees,

            "interventions_planifiees":
                interventions_planifiees,

            "resultats": resultats,

            "recommandations":
                recommandations
        })

    return donnees


# ============================================================
# HISTORIQUE COMPLET
# ============================================================

def recuperer_historique(
    connexion
):

    rapports = connexion.execute(
        """
        SELECT
            id,
            fichier,
            hash_contenu,
            reference,
            date,
            analyse_le

        FROM rapports

        ORDER BY date
        """
    ).fetchall()

    historique = []

    for rapport in rapports:

        rapport_id = rapport[0]

        donnees = {

            "fichier": rapport[1],

            "hash_contenu": rapport[2],

            "reference": rapport[3],

            "date": rapport[4],

            "analyse_le": rapport[5],

            "analyses": []
        }

        equipements = connexion.execute(
            """
            SELECT
                id,
                nom,
                type,
                description,
                causes,
                interventions_realisees,
                interventions_planifiees,
                resultats,
                recommandations

            FROM equipements

            WHERE rapport_id = ?
            """,
            (rapport_id,)
        ).fetchall()

        for eq in equipements:

            equipement_id = eq[0]

            anomalies_sql = connexion.execute(
                """
                SELECT
                    description,
                    niveau,
                    statut

                FROM anomalies

                WHERE equipement_id = ?
                """,
                (equipement_id,)
            ).fetchall()

            anomalies = []

            for anomalie in anomalies_sql:

                anomalies.append({

                    "description": anomalie[0],

                    "niveau": anomalie[1],

                    "statut": anomalie[2]
                })

            causes = (
                eq[4].split(" | ")
                if eq[4]
                else []
            )

            interventions_realisees = (
                eq[5].split(" | ")
                if eq[5]
                else []
            )

            interventions_planifiees = (
                eq[6].split(" | ")
                if eq[6]
                else []
            )

            resultats = (
                eq[7].split(" | ")
                if eq[7]
                else []
            )

            recommandations = (
                eq[8].split(" | ")
                if eq[8]
                else []
            )

            donnees["analyses"].append({

                "equipement": eq[1],

                "type": eq[2],

                "description": eq[3],

                "anomalies": anomalies,

                "causes": causes,

                "interventions_realisees":
                    interventions_realisees,

                "interventions_planifiees":
                    interventions_planifiees,

                "resultats": resultats,

                "recommandations": [
                    {
                        "action": r
                    }
                    for r in recommandations
                ]
            })

        historique.append(
            donnees
        )

    return historique


# ============================================================
# STATISTIQUES
# ============================================================

def statistiques(
    connexion
):

    nb_rapports = connexion.execute(
        """
        SELECT COUNT(*)
        FROM rapports
        """
    ).fetchone()[0]

    nb_equipements = connexion.execute(
        """
        SELECT COUNT(DISTINCT nom)
        FROM equipements
        """
    ).fetchone()[0]

    par_niveau = connexion.execute(
        """
        SELECT
            niveau,
            COUNT(*)

        FROM anomalies

        GROUP BY niveau
        """
    ).fetchall()

    equipements_recurrents = connexion.execute(
        """
        SELECT
            nom,
            COUNT(*) AS nb

        FROM equipements

        GROUP BY nom

        HAVING nb >= 2

        ORDER BY nb DESC
        """
    ).fetchall()

    return {

        "nb_rapports":
            nb_rapports,

        "nb_equipements_distincts":
            nb_equipements,

        "anomalies_par_niveau":
            dict(par_niveau),

        "equipements_recurrents":
            equipements_recurrents
    }