import os
import hashlib
import tempfile
import traceback
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from extract import (
    extract_text,
    ExtractionError,
    FormatNonSupporte,
    FichierVide,
    FichierIllisible,
    EXTENSIONS_ACCEPTEES,
)

from agent import (
    analyser_rapport,
    synthese_globale,
    RapportVide,
    DocumentTropLong,
    JSONInvalide,
    VLLMIndisponible,
    MAX_CARACTERES_RAPPORT,
)

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
# GESTION DES ERREURS
# ============================================================

def message_erreur(erreur):

    if isinstance(erreur, HTTPException):
        return erreur

    if isinstance(erreur, FormatNonSupporte):
        return HTTPException(
            status_code=400,
            detail=str(erreur)
        )

    if isinstance(erreur, FichierVide):
        return HTTPException(
            status_code=400,
            detail=str(erreur)
        )

    if isinstance(erreur, FichierIllisible):
        return HTTPException(
            status_code=400,
            detail=str(erreur)
            or "Le document est illisible."
        )

    if isinstance(erreur, ExtractionError):
        return HTTPException(
            status_code=400,
            detail=str(erreur)
        )

    if isinstance(erreur, RapportVide):
        return HTTPException(
            status_code=400,
            detail=str(erreur)
        )

    if isinstance(erreur, DocumentTropLong):
        return HTTPException(
            status_code=413,
            detail=str(erreur)
        )

    if isinstance(erreur, VLLMIndisponible):
        return HTTPException(
            status_code=503,
            detail=str(erreur)
        )

    if isinstance(erreur, JSONInvalide):
        return HTTPException(
            status_code=502,
            detail=(
                "La réponse du modèle local est invalide ou incomplète. "
                f"{erreur}"
            )
        )

    return HTTPException(
        status_code=500,
        detail=(
            f"Erreur interne : {type(erreur).__name__}: {str(erreur)}"
        )
    )


# ============================================================
# HOME
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

    resume = []

    for rapport in historique:

        resume.append({
            "fichier": rapport.get("fichier"),
            "date": rapport.get("date"),
            "analyse_le": rapport.get("analyse_le"),
        })

    resume.sort(
        key=lambda r: r.get("analyse_le") or "",
        reverse=True
    )

    return {
        "historique": resume
    }


# ============================================================
# HASH
# ============================================================

def calculer_hash(texte):

    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


# ============================================================
# TRAITER UN FICHIER
# ============================================================

async def traiter_un_fichier(
    fichier: UploadFile
):

    if not fichier.filename:

        raise HTTPException(
            status_code=400,
            detail="Un fichier reçu n'a pas de nom."
        )

    print()
    print("=" * 70)
    print(f" FICHIER REÇU : {fichier.filename}")
    print("=" * 70)

    # ========================================================
    # LECTURE DU FICHIER
    # ========================================================

    contenu = await fichier.read()

    if not contenu:

        raise HTTPException(
            status_code=400,
            detail=f"Le fichier {fichier.filename} est vide."
        )

    print(
        f" Taille : {len(contenu)} octets"
    )

    # ========================================================
    # LIMITE TAILLE
    # ========================================================

    taille_max = 20 * 1024 * 1024

    if len(contenu) > taille_max:

        raise HTTPException(
            status_code=413,
            detail=(
                f"{fichier.filename} dépasse "
                "la limite de 20 Mo."
            )
        )

    # ========================================================
    # EXTENSION
    # ========================================================

    extension = os.path.splitext(
        fichier.filename
    )[1].lower()

    if extension not in EXTENSIONS_ACCEPTEES:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Format non supporté pour "
                f"{fichier.filename}. "
                "Formats acceptés : PDF, DOCX, TXT."
            )
        )

    chemin_temp = None

    try:

        # ====================================================
        # FICHIER TEMPORAIRE
        # ====================================================

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as fichier_temp:

            fichier_temp.write(contenu)

            chemin_temp = fichier_temp.name

        # ====================================================
        # EXTRACTION
        # ====================================================

        print()
        print(">>> EXTRACTION DU TEXTE...")

        try:

            texte = extract_text(
                chemin_temp
            )

        except Exception as erreur:

            print()
            print("!!! ERREUR EXTRACTION !!!")
            print(
                type(erreur).__name__,
                str(erreur)
            )
            traceback.print_exc()

            raise message_erreur(
                erreur
            )

        texte = texte.strip()

        print(
            f">>> Texte extrait : {len(texte)} caractères"
        )

        if len(texte) < 30:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"{fichier.filename} "
                    "ne contient pas assez de texte exploitable."
                )
            )

        # ====================================================
        # LIMITE TEXTE
        # ====================================================

        if len(texte) > MAX_CARACTERES_RAPPORT:

            raise HTTPException(
                status_code=413,
                detail=(
                    f"{fichier.filename} dépasse la limite "
                    f"supportée de {MAX_CARACTERES_RAPPORT} caractères."
                )
            )

        # ====================================================
        # HASH
        # ====================================================

        hash_contenu = calculer_hash(
            texte
        )

        print(
            f">>> Hash : {hash_contenu}"
        )

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

            # =================================================
            # RAPPORT DÉJÀ ANALYSÉ
            # =================================================

            if rapport_existant:

                print()
                print(
                    ">>> Rapport déjà analysé."
                )
                print(
                    ">>> Récupération depuis SQLite."
                )

                resultat = rapport_existant

                if isinstance(
                    resultat,
                    dict
                ):

                    resultat["fichier"] = (
                        fichier.filename
                    )

                    resultat["hash_contenu"] = (
                        hash_contenu
                    )

                return resultat

            # =================================================
            # NOUVELLE ANALYSE
            # =================================================

            print()
            print(">>> NOUVELLE ANALYSE IA...")
            print(">>> Appel de analyser_rapport()...")

            try:

                analyses = analyser_rapport(
                    texte
                )

            except Exception as erreur:

                print()
                print("=" * 70)
                print("!!! ERREUR DANS AGENT !!!")
                print(
                    "TYPE :",
                    type(erreur).__name__
                )
                print(
                    "MESSAGE :",
                    str(erreur)
                )
                print("=" * 70)

                traceback.print_exc()

                raise message_erreur(
                    erreur
                )

            # =================================================
            # DEBUG RESULTAT AGENT
            # =================================================

            print()
            print("=" * 70)
            print(">>> RESULTAT DE L'AGENT")
            print(
                "TYPE :",
                type(analyses).__name__
            )
            print(
                "CONTENU :",
                analyses
            )
            print("=" * 70)

            # =================================================
            # VERIFICATION
            # =================================================

            if not analyses:

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "L'agent SYNIA n'a retourné "
                        "aucune analyse."
                    )
                )

            if not isinstance(
                analyses,
                list
            ):

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Format inattendu retourné "
                        "par l'agent SYNIA."
                    )
                )

            # =================================================
            # CREATION DU RESULTAT
            # =================================================

            resultat = {

                "fichier":
                    fichier.filename,

                "hash_contenu":
                    hash_contenu,

                "analyse_le":
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                "analyses":
                    analyses
            }

            # =================================================
            # SAUVEGARDE SQLITE
            # =================================================

            print()
            print(">>> Sauvegarde dans SQLite...")

            try:

                bdd.inserer_rapport(
                    connexion,
                    resultat
                )

                print(
                    ">>> Rapport sauvegardé."
                )

            except Exception as erreur:

                print()
                print("!!! ERREUR SQLITE !!!")
                print(
                    type(erreur).__name__,
                    str(erreur)
                )

                traceback.print_exc()

                # Pour ne pas perdre l'analyse si
                # SQLite pose problème
                print(
                    ">>> L'analyse sera quand même retournée."
                )

            return resultat

        finally:

            connexion.close()

    finally:

        # ====================================================
        # SUPPRESSION FICHIER TEMPORAIRE
        # ====================================================

        if (
            chemin_temp
            and os.path.exists(chemin_temp)
        ):

            os.remove(
                chemin_temp
            )


# ============================================================
# ANALYSE DE PLUSIEURS FICHIERS
# ============================================================

@app.post("/api/analyse")
async def analyser_fichiers(
    fichiers: List[UploadFile] = File(...)
):

    print()
    print("=" * 70)
    print("========== NOUVELLE REQUÊTE /api/analyse ==========")
    print("=" * 70)

    if not fichiers:

        raise HTTPException(
            status_code=400,
            detail="Aucun fichier reçu."
        )

    # ========================================================
    # ANALYSER LES FICHIERS
    # ========================================================

    resultats = []

    for fichier in fichiers:

        resultat = await traiter_un_fichier(
            fichier
        )

        resultats.append(
            resultat
        )

    # ========================================================
    # DEBUG
    # ========================================================

    print()
    print("=" * 70)
    print(">>> RESULTATS AVANT SYNTHESE")
    print(
        "TYPE :",
        type(resultats).__name__
    )
    print(
        "CONTENU :",
        resultats
    )
    print("=" * 70)

    # ========================================================
    # EXTRAIRE LES ANALYSES POUR LA SYNTHESE
    # ========================================================

    analyses_pour_synthese = []

    for resultat in resultats:

        if not isinstance(
            resultat,
            dict
        ):
            continue

        analyses = resultat.get(
            "analyses",
            []
        )

        if isinstance(
            analyses,
            list
        ):

            analyses_pour_synthese.extend(
                analyses
            )

    print()
    print("=" * 70)
    print(">>> DONNEES ENVOYEES A LA SYNTHESE")
    print(
        "TYPE :",
        type(analyses_pour_synthese).__name__
    )
    print(
        "CONTENU :",
        analyses_pour_synthese
    )
    print("=" * 70)

    # ========================================================
    # SYNTHESE GLOBALE
    # ========================================================

    synthese = {
        "synthese_interventions": [],
        "recommandations": []
    }

    if analyses_pour_synthese:

        print()
        print(
            ">>> Génération de la synthèse globale..."
        )

        try:

            # IMPORTANT :
            # ton agent.py définit :
            # synthese_globale(resultats)
            #
            # donc on lui donne UN SEUL argument.

            synthese = synthese_globale(
                analyses_pour_synthese
            )

            print()
            print("=" * 70)
            print(">>> SYNTHESE GENEREE")
            print(
                synthese
            )
            print("=" * 70)

        except Exception as erreur:

            print()
            print("=" * 70)
            print("!!! ERREUR SYNTHESE !!!")
            print(
                "TYPE :",
                type(erreur).__name__
            )
            print(
                "MESSAGE :",
                str(erreur)
            )
            print("=" * 70)

            traceback.print_exc()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Erreur pendant la génération "
                    f"de la synthèse : "
                    f"{type(erreur).__name__}: "
                    f"{str(erreur)}"
                )
            )

    else:

        print(
            ">>> Aucune analyse disponible pour la synthèse."
        )

    # ========================================================
    # VERIFICATION SYNTHESE
    # ========================================================

    if not isinstance(
        synthese,
        dict
    ):

        synthese = {
            "synthese_interventions": [],
            "recommandations": []
        }

    # ========================================================
    # REPONSE FINALE
    # ========================================================

    print()
    print("=" * 70)
    print(">>> ANALYSE TERMINEE")
    print("=" * 70)

    return {

        "status": "success",

        "analyses": resultats,

        "synthese": {

            "synthese_interventions":
                synthese.get(
                    "synthese_interventions",
                    []
                ),

            "recommandations":
                synthese.get(
                    "recommandations",
                    []
                )
        }
    }