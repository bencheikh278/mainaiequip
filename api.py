import os
import hashlib
import tempfile
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from extract import extract_text
from agent import analyser_rapport, synthese_globale
import bdd


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="SYNIA API",
    description="API de SYNIA pour l'analyse intelligente des documents de maintenance",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.get("/")
def home():
    return {
        "message": "SYNIA API is running",
        "status": "ok"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():
    return {
        "status": "ok"
    }

# ============================================================
# HISTORIQUE 
# ============================================================

@app.get("/api/historique")
def obtenir_historique():

    connexion = bdd.connecter()

    try:

        historique = bdd.recuperer_historique(
            connexion
        )

    finally:

        connexion.close()

    resume = [
        {
            "fichier": rapport.get("fichier"),
            "date": rapport.get("date"),
            "analyse_le": rapport.get("analyse_le"),
        }
        for rapport in historique
    ]

    resume.sort(
        key=lambda r: r.get("analyse_le") or "",
        reverse=True
    )


    return {
        "historique": resume
    }

# ============================================================
# CALCUL DU HASH
# ============================================================

def calculer_hash(texte):
    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


# ============================================================
# TRAITER UN SEUL FICHIER
# ============================================================

async def traiter_un_fichier(fichier: UploadFile):

    if not fichier.filename:
        raise HTTPException(
            status_code=400,
            detail="Un fichier reçu n'a pas de nom."
        )

    print()
    print("=" * 60)
    print(f" Fichier reçu : {fichier.filename}")
    print("=" * 60)

    contenu = await fichier.read()

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail=f"Le fichier {fichier.filename} est vide."
        )

    print(f" Taille : {len(contenu)} octets")

    taille_max = 20 * 1024 * 1024

    if len(contenu) > taille_max:
        raise HTTPException(
            status_code=413,
            detail=f"{fichier.filename} dépasse la limite de 20 Mo."
        )

    extension = os.path.splitext(
        fichier.filename
    )[1].lower()

    chemin_temp = None

    try:

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as fichier_temp:

            fichier_temp.write(contenu)

            chemin_temp = fichier_temp.name

        # ====================================================
        # EXTRACTION
        # ====================================================

        print(" Extraction du texte...")

        texte = extract_text(chemin_temp)

        if not texte:
            raise HTTPException(
                status_code=400,
                detail=f"Impossible d'extraire le texte de {fichier.filename}."
            )

        texte = texte.strip()

        if len(texte) < 30:
            raise HTTPException(
                status_code=400,
                detail=f"{fichier.filename} ne contient pas assez de texte exploitable."
            )

        print(f" Texte extrait : {len(texte)} caractères")

        # ====================================================
        # HASH
        # ====================================================

        hash_contenu = calculer_hash(texte)

        print(f" Hash : {hash_contenu}")

        # ====================================================
        # SQLITE
        # ====================================================

        connexion = bdd.connecter()

        try:

            rapport_existant = (
                bdd.recuperer_rapport_par_hash(
                    connexion,
                    hash_contenu
                )
            )

            if rapport_existant:

                print(
                    " Rapport déjà analysé → récupération depuis SQLite"
                )

                resultat = rapport_existant

                resultat["fichier"] = fichier.filename

                resultat["hash_contenu"] = hash_contenu

            else:

                print(" Nouvelle analyse IA...")

                resultat = analyser_rapport(texte)

                if not resultat:
                    raise HTTPException(
                        status_code=500,
                        detail=f"L'analyse IA n'a rien retourné pour {fichier.filename}."
                    )

                resultat["fichier"] = fichier.filename

                resultat["hash_contenu"] = hash_contenu

                resultat["analyse_le"] = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                print(" Sauvegarde dans SQLite...")

                bdd.inserer_rapport(
                    connexion,
                    resultat
                )

                print(" Rapport sauvegardé")

            return resultat

        finally:

            connexion.close()

    finally:

        if (
            chemin_temp
            and os.path.exists(chemin_temp)
        ):
            os.remove(chemin_temp)


# ============================================================
# ANALYSE DE PLUSIEURS FICHIERS
# ============================================================

@app.post("/api/analyse")
async def analyser_fichiers(
    fichiers: List[UploadFile] = File(...)
):

    if not fichiers:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier reçu."
        )

    # --------------------------------------------------------
    # 1. TRAITER CHAQUE FICHIER 
    # --------------------------------------------------------

    resultats = []

    for fichier in fichiers:

        resultat = await traiter_un_fichier(fichier)

        resultats.append(resultat)

    # --------------------------------------------------------
    # 2. RÉCUPÉRER L'HISTORIQUE
    # --------------------------------------------------------

    connexion = bdd.connecter()

    try:

        historique = bdd.recuperer_historique(
            connexion
        )

    finally:

        connexion.close()

    print(
        f" Historique SQLite : {len(historique)} rapports"
    )

    # --------------------------------------------------------
    # 3. SYNTHÈSE GLOBALE (tous les fichiers envoyés ensemble)
    # --------------------------------------------------------

    print(
        " Génération de la synthèse et des recommandations..."
    )

    try:

        synthese = synthese_globale(
            resultats,
            historique
        )

    except Exception as e:

        print(f" Erreur synthèse : {e}")

        raise HTTPException(
            status_code=503,
            detail=(
                "Le service IA est temporairement indisponible. "
                "Veuillez réessayer dans quelques instants."
            )
        )

    print(" Analyse terminée")

    # --------------------------------------------------------
    # 4. RETOUR JSON
    # --------------------------------------------------------

    return {
        "status": "success",

        "analyses": resultats,   # liste, un élément par fichier

        "synthese": synthese
    }