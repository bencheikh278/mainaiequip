import sqlite3
import os


CHEMIN_DB = "output/synia.db"


# ============================================================
# CONNEXION À SQLITE
# ============================================================

def connecter():

    """
    Ouvre la base SQLite et crée les tables
    si elles n'existent pas.
    """

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
    # TABLE RAPPORTS
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
    # TABLE EQUIPEMENTS
    # ========================================================

    connexion.execute("""
        CREATE TABLE IF NOT EXISTS equipements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            rapport_id INTEGER NOT NULL,

            nom TEXT,

            type TEXT,

            causes TEXT,

            interventions TEXT,

            resultats TEXT,

            FOREIGN KEY (rapport_id)
            REFERENCES rapports(id)
            ON DELETE CASCADE
        )
    """)

    # ========================================================
    # TABLE ANOMALIES
    # ========================================================

    connexion.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            equipement_id INTEGER NOT NULL,

            description TEXT,

            niveau TEXT,

            FOREIGN KEY (equipement_id)
            REFERENCES equipements(id)
            ON DELETE CASCADE
        )
    """)

    connexion.commit()

    return connexion


# ============================================================
# VÉRIFIER SI LE HASH EXISTE
# ============================================================

def rapport_existe_par_hash(
    connexion,
    hash_contenu
):

    """
    Vérifie si le contenu du rapport
    a déjà été analysé.
    """

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
# RÉCUPÉRER UN RAPPORT PAR HASH
# ============================================================

def recuperer_rapport_par_hash(
    connexion,
    hash_contenu
):

    """
    Récupère l'analyse complète d'un rapport
    à partir de son hash.
    """

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

    donnees_rapport = {

        "fichier": rapport[1],

        "hash_contenu": rapport[2],

        "reference": rapport[3],

        "date": rapport[4],

        "analyse_le": rapport[5],

        "equipements": []
    }

    # ========================================================
    # RÉCUPÉRER LES ÉQUIPEMENTS
    # ========================================================

    equipements = connexion.execute(
        """
        SELECT
            id,
            nom,
            type,
            causes,
            interventions,
            resultats

        FROM equipements

        WHERE rapport_id = ?
        """,
        (rapport_id,)
    ).fetchall()

    for eq in equipements:

        equipement_id = eq[0]

        # ====================================================
        # RÉCUPÉRER LES ANOMALIES
        # ====================================================

        anomalies = connexion.execute(
            """
            SELECT
                description,
                niveau

            FROM anomalies

            WHERE equipement_id = ?
            """,
            (equipement_id,)
        ).fetchall()

        liste_anomalies = []

        for anomalie in anomalies:

            liste_anomalies.append({

                "description": anomalie[0],

                "niveau": anomalie[1]
            })

        # ====================================================
        # RECONSTRUIRE LES LISTES
        # ====================================================

        causes = (
            eq[3].split(" | ")
            if eq[3]
            else []
        )

        interventions = (
            eq[4].split(" | ")
            if eq[4]
            else []
        )

        resultats = (
            eq[5].split(" | ")
            if eq[5]
            else []
        )

        donnees_rapport[
            "equipements"
        ].append({

            "nom": eq[1],

            "type": eq[2],

            "anomalies": liste_anomalies,

            "causes": causes,

            "interventions": interventions,

            "resultats": resultats
        })

    return donnees_rapport


# ============================================================
# INSÉRER UN RAPPORT
# ============================================================

def inserer_rapport(
    connexion,
    donnees
):

    """
    Enregistre l'analyse complète d'un rapport.

    Le hash du contenu permet d'éviter de réanalyser
    exactement le même document.
    """

    fichier = donnees.get(
        "fichier"
    )

    hash_contenu = donnees.get(
        "hash_contenu"
    )

    # ========================================================
    # VÉRIFIER SI LE CONTENU EXISTE DÉJÀ
    # ========================================================

    if rapport_existe_par_hash(
        connexion,
        hash_contenu
    ):

        return

    # ========================================================
    # INSÉRER LE RAPPORT
    # ========================================================

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

            donnees.get(
                "reference"
            ),

            donnees.get(
                "date"
            ),

            donnees.get(
                "analyse_le"
            )
        )
    )

    rapport_id = curseur.lastrowid

    # ========================================================
    # INSÉRER LES ÉQUIPEMENTS
    # ========================================================

    for eq in donnees.get(
        "equipements",
        []
    ):

        curseur_eq = connexion.execute(
            """
            INSERT INTO equipements
            (
                rapport_id,
                nom,
                type,
                causes,
                interventions,
                resultats
            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,

            (

                rapport_id,

                eq.get("nom"),

                eq.get("type"),

                " | ".join(
                    str(c)
                    for c in eq.get(
                        "causes",
                        []
                    )
                ),

                " | ".join(
                    str(i)
                    for i in eq.get(
                        "interventions",
                        []
                    )
                ),

                " | ".join(
                    str(r)
                    for r in eq.get(
                        "resultats",
                        []
                    )
                )
            )
        )

        equipement_id = (
            curseur_eq.lastrowid
        )

        # ====================================================
        # INSÉRER LES ANOMALIES
        # ====================================================

        for anomalie in eq.get(
            "anomalies",
            []
        ):

            connexion.execute(
                """
                INSERT INTO anomalies
                (
                    equipement_id,
                    description,
                    niveau
                )

                VALUES (?, ?, ?)
                """,

                (

                    equipement_id,

                    anomalie.get(
                        "description"
                    ),

                    anomalie.get(
                        "niveau"
                    )
                )
            )

    connexion.commit()


# ============================================================
# RÉCUPÉRER TOUT L'HISTORIQUE
# ============================================================

def recuperer_historique(
    connexion
):

    """
    Récupère tous les rapports analysés
    dans SQLite.
    """

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

        donnees_rapport = {

            "fichier": rapport[1],

            "hash_contenu": rapport[2],

            "reference": rapport[3],

            "date": rapport[4],

            "analyse_le": rapport[5],

            "equipements": []
        }

        # ====================================================
        # ÉQUIPEMENTS
        # ====================================================

        equipements = connexion.execute(
            """
            SELECT
                id,
                nom,
                type,
                causes,
                interventions,
                resultats

            FROM equipements

            WHERE rapport_id = ?
            """,
            (rapport_id,)
        ).fetchall()

        for eq in equipements:

            equipement_id = eq[0]

            # =================================================
            # ANOMALIES
            # =================================================

            anomalies = connexion.execute(
                """
                SELECT
                    description,
                    niveau

                FROM anomalies

                WHERE equipement_id = ?
                """,
                (equipement_id,)
            ).fetchall()

            liste_anomalies = []

            for anomalie in anomalies:

                liste_anomalies.append({

                    "description": anomalie[0],

                    "niveau": anomalie[1]
                })

            causes = (
                eq[3].split(" | ")
                if eq[3]
                else []
            )

            interventions = (
                eq[4].split(" | ")
                if eq[4]
                else []
            )

            resultats = (
                eq[5].split(" | ")
                if eq[5]
                else []
            )

            donnees_rapport[
                "equipements"
            ].append({

                "nom": eq[1],

                "type": eq[2],

                "anomalies": liste_anomalies,

                "causes": causes,

                "interventions": interventions,

                "resultats": resultats
            })

        historique.append(
            donnees_rapport
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

        "nb_rapports": nb_rapports,

        "nb_equipements_distincts":
            nb_equipements,

        "anomalies_par_niveau":
            dict(par_niveau),

        "equipements_recurrents":
            equipements_recurrents
    }