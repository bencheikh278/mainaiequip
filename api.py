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
    description=(
        "API de SYNIA pour l'analyse intelligente "
        "des documents de maintenance"
    ),
    version="1.0.0",
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
            detail=str(erreur),
        )

    if isinstance(erreur, FichierVide):
        return HTTPException(
            status_code=400,
            detail=str(erreur),
        )

    if isinstance(erreur, FichierIllisible):
        return HTTPException(
            status_code=400,
            detail=(
                str(erreur)
                or "Le document est illisible."
            ),
        )

    if isinstance(erreur, ExtractionError):
        return HTTPException(
            status_code=400,
            detail=str(erreur),
        )

    if isinstance(erreur, RapportVide):
        return HTTPException(
            status_code=400,
            detail=str(erreur),
        )

    if isinstance(erreur, DocumentTropLong):
        return HTTPException(
            status_code=413,
            detail=str(erreur),
        )

    if isinstance(erreur, VLLMIndisponible):
        return HTTPException(
            status_code=503,
            detail=str(erreur),
        )

    if isinstance(erreur, JSONInvalide):
        return HTTPException(
            status_code=502,
            detail=(
                "La réponse du modèle local est invalide "
                "ou incomplète. "
                f"{erreur}"
            ),
        )

    return HTTPException(
        status_code=500,
        detail=(
            f"Erreur interne : "
            f"{type(erreur).__name__}: {str(erreur)}"
        ),
    )


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message": "SYNIA API is running",
        "status": "ok",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
    }


# ============================================================
# CALCUL HASH
# ============================================================

def calculer_hash(texte):

    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


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

    except Exception as erreur:

        print()
        print("!!! ERREUR HISTORIQUE !!!")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                "Impossible de récupérer "
                "l'historique."
            ),
        )

    finally:

        connexion.close()

    resume = []

    for rapport in historique:

        resume.append({

            "fichier":
                rapport.get("fichier"),

            "date":
                rapport.get("date"),

            "analyse_le":
                rapport.get("analyse_le"),

        })

    resume.sort(
        key=lambda r:
            r.get("analyse_le") or "",
        reverse=True,
    )

    return {
        "historique": resume
    }


# ============================================================
# TRAITER UN FICHIER
# ============================================================

async def traiter_un_fichier(
    fichier: UploadFile,
):

    # ========================================================
    # NOM
    # ========================================================

    if not fichier.filename:

        raise HTTPException(
            status_code=400,
            detail="Un fichier reçu n'a pas de nom.",
        )


    print()
    print("=" * 70)
    print(
        f" FICHIER REÇU : {fichier.filename}"
    )
    print("=" * 70)


    # ========================================================
    # LECTURE
    # ========================================================

    contenu = await fichier.read()


    if not contenu:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Le fichier {fichier.filename} "
                "est vide."
            ),
        )


    print(
        f">>> Taille : {len(contenu)} octets"
    )


    # ========================================================
    # LIMITE 20 MO
    # ========================================================

    taille_max = 20 * 1024 * 1024


    if len(contenu) > taille_max:

        raise HTTPException(
            status_code=413,
            detail=(
                f"{fichier.filename} dépasse "
                "la limite de 20 Mo."
            ),
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
            ),
        )


    chemin_temp = None


    try:

        # ====================================================
        # FICHIER TEMPORAIRE
        # ====================================================

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension,
        ) as fichier_temp:

            fichier_temp.write(contenu)

            chemin_temp = fichier_temp.name


        # ====================================================
        # EXTRACTION DU TEXTE
        # ====================================================

        print()
        print(">>> EXTRACTION DU TEXTE...")


        try:

            texte = extract_text(
                chemin_temp
            )

        except Exception as erreur:

            print()
            print(
                "!!! ERREUR EXTRACTION !!!"
            )

            print(
                "TYPE :",
                type(erreur).__name__,
            )

            print(
                "MESSAGE :",
                str(erreur),
            )

            traceback.print_exc()


            raise message_erreur(
                erreur
            )


        texte = texte.strip()


        print(
            f">>> Texte extrait : "
            f"{len(texte)} caractères"
        )


        # ====================================================
        # TEXTE TROP COURT
        # ====================================================

        if len(texte) < 30:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"{fichier.filename} "
                    "ne contient pas assez de "
                    "texte exploitable."
                ),
            )


        # ====================================================
        # TEXTE TROP LONG
        # ====================================================

        if (
            len(texte)
            > MAX_CARACTERES_RAPPORT
        ):

            raise HTTPException(
                status_code=413,
                detail=(
                    f"{fichier.filename} dépasse "
                    "la limite supportée de "
                    f"{MAX_CARACTERES_RAPPORT} "
                    "caractères."
                ),
            )


        # ====================================================
        # HASH DU CONTENU
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

            # =================================================
            # CHERCHER SI LE RAPPORT EXISTE
            # =================================================

            rapport_existant = (
                bdd.recuperer_rapport_par_hash(
                    connexion,
                    hash_contenu,
                )
            )


            # =================================================
            # RAPPORT DÉJÀ ANALYSÉ
            # =================================================

            if rapport_existant:

                print()
                print(
                    ">>> RAPPORT DÉJÀ ANALYSÉ."
                )

                print(
                    ">>> Récupération depuis SQLite..."
                )


                analyses_existantes = (
                    rapport_existant.get(
                        "analyses",
                        [],
                    )
                )


                # ------------------------------------------------
                # Sécurité
                # ------------------------------------------------

                if not isinstance(
                    analyses_existantes,
                    list,
                ):

                    analyses_existantes = []


                resultat = {

                    "fichier":
                        fichier.filename,

                    "hash_contenu":
                        hash_contenu,

                    "analyse_le":
                        rapport_existant.get(
                            "analyse_le"
                        ),

                    "analyses":
                        analyses_existantes,

                }


                print()
                print(
                    ">>> Analyses récupérées :"
                )

                print(
                    analyses_existantes
                )


                return resultat


            # =================================================
            # NOUVELLE ANALYSE
            # =================================================

            print()
            print(
                ">>> NOUVELLE ANALYSE IA..."
            )

            print(
                ">>> Appel de "
                "analyser_rapport()..."
            )


            try:

                analyses = analyser_rapport(
                    texte
                )

            except Exception as erreur:

                print()
                print("=" * 70)
                print(
                    "!!! ERREUR AGENT !!!"
                )

                print(
                    "TYPE :",
                    type(erreur).__name__,
                )

                print(
                    "MESSAGE :",
                    str(erreur),
                )

                print("=" * 70)

                traceback.print_exc()


                raise message_erreur(
                    erreur
                )


            # =================================================
            # DEBUG AGENT
            # =================================================

            print()
            print("=" * 70)
            print(
                ">>> RESULTAT DE L'AGENT"
            )

            print(
                "TYPE :",
                type(analyses).__name__,
            )

            print(
                "CONTENU :",
                analyses,
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
                    ),
                )


            if not isinstance(
                analyses,
                list,
            ):

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Format inattendu retourné "
                        "par l'agent SYNIA."
                    ),
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
                    analyses,

            }


            # =================================================
            # SAUVEGARDE SQLITE
            # =================================================

            print()
            print(
                ">>> Sauvegarde dans SQLite..."
            )


            try:

                bdd.inserer_rapport(
                    connexion,
                    resultat,
                )

                print(
                    ">>> Rapport sauvegardé."
                )


            except Exception as erreur:

                print()
                print(
                    "!!! ERREUR SQLITE !!!"
                )

                print(
                    "TYPE :",
                    type(erreur).__name__,
                )

                print(
                    "MESSAGE :",
                    str(erreur),
                )

                traceback.print_exc()


                print(
                    ">>> L'analyse sera "
                    "quand même retournée."
                )


            return resultat


        finally:

            connexion.close()


    finally:

        # ====================================================
        # SUPPRESSION TEMPORAIRE
        # ====================================================

        if (
            chemin_temp
            and os.path.exists(
                chemin_temp
            )
        ):

            try:

                os.remove(
                    chemin_temp
                )

            except Exception:

                pass


# ============================================================
# ANALYSE DE PLUSIEURS FICHIERS
# ============================================================

@app.post("/api/analyse")
async def analyser_fichiers(
    fichiers: List[UploadFile] = File(...),
):

    print()
    print("=" * 70)
    print(
        "========== NOUVELLE REQUÊTE "
        "/api/analyse =========="
    )
    print("=" * 70)


    # ========================================================
    # VERIFICATION
    # ========================================================

    if not fichiers:

        raise HTTPException(
            status_code=400,
            detail="Aucun fichier reçu.",
        )


    # ========================================================
    # ANALYSER LES FICHIERS
    # ========================================================

    resultats = []


    for fichier in fichiers:

        try:

            resultat = await traiter_un_fichier(
                fichier
            )

            resultats.append(
                resultat
            )

        except HTTPException:

            raise

        except Exception as erreur:

            print()
            print(
                "!!! ERREUR TRAITEMENT FICHIER !!!"
            )

            traceback.print_exc()


            raise HTTPException(
                status_code=500,
                detail=(
                    f"Erreur pendant le traitement "
                    f"de {fichier.filename} : "
                    f"{type(erreur).__name__}: "
                    f"{str(erreur)}"
                ),
            )


    # ========================================================
    # EXTRAIRE LES ANALYSES
    # ========================================================

    analyses_pour_synthese = []


    for resultat in resultats:

        if not isinstance(
            resultat,
            dict,
        ):

            continue


        analyses = resultat.get(
            "analyses",
            [],
        )


        if isinstance(
            analyses,
            list,
        ):

            analyses_pour_synthese.extend(
                analyses
            )


    # ========================================================
    # DEBUG
    # ========================================================

    print()
    print("=" * 70)
    print(
        ">>> DONNEES POUR LA SYNTHESE"
    )

    print(
        "Nombre d'analyses :",
        len(
            analyses_pour_synthese
        ),
    )

    print(
        "Contenu :",
        analyses_pour_synthese,
    )

    print("=" * 70)


    # ========================================================
    # SYNTHESE PAR DEFAUT
    # ========================================================

    synthese = {

        "synthese_interventions": [],

        "recommandations": [],

    }


    # ========================================================
    # GENERATION SYNTHESE
    # ========================================================

    if analyses_pour_synthese:

        print()
        print(
            ">>> GENERATION DE LA SYNTHESE..."
        )


        try:

            synthese = synthese_globale(
                analyses_pour_synthese
            )


            print()
            print("=" * 70)
            print(
                ">>> SYNTHESE GENEREE"
            )

            print(
                synthese
            )

            print("=" * 70)


        except Exception as erreur:

            print()
            print("=" * 70)
            print(
                "!!! ERREUR SYNTHESE !!!"
            )

            print(
                "TYPE :",
                type(erreur).__name__,
            )

            print(
                "MESSAGE :",
                str(erreur),
            )

            print("=" * 70)

            traceback.print_exc()


            raise HTTPException(
                status_code=500,
                detail=(
                    "Erreur pendant la génération "
                    "de la synthèse : "
                    f"{type(erreur).__name__}: "
                    f"{str(erreur)}"
                ),
            )


    else:

        print(
            ">>> Aucune analyse disponible "
            "pour la synthèse."
        )


    # ========================================================
    # VERIFICATION SYNTHESE
    # ========================================================

    if not isinstance(
        synthese,
        dict,
    ):

        synthese = {

            "synthese_interventions": [],

            "recommandations": [],

        }


    # ========================================================
    # NORMALISATION
    # ========================================================

    synthese_interventions = (
        synthese.get(
            "synthese_interventions",
            [],
        )
    )


    recommandations = (
        synthese.get(
            "recommandations",
            [],
        )
    )


    if not isinstance(
        synthese_interventions,
        list,
    ):

        synthese_interventions = []


    if not isinstance(
        recommandations,
        list,
    ):

        recommandations = []


    # ========================================================
    # REPONSE FINALE
    # ========================================================

    reponse = {

        "status":
            "success",

        # Les analyses détaillées sont conservées
        # pour le backend / historique.
        #
        # Le frontend ne les affiche pas.

        "analyses":
            resultats,

        # Ce bloc est celui utilisé
        # par app.js.

        "synthese": {

            "synthese_interventions":
                synthese_interventions,

            "recommandations":
                recommandations,

        },

    }


    # ========================================================
    # DEBUG FINAL
    # ========================================================

    print()
    print("=" * 70)
    print(
        ">>> REPONSE ENVOYEE AU FRONTEND"
    )

    print(
        reponse
    )

    print("=" * 70)

    print()
    print(
        "========== ANALYSE TERMINEE =========="
    )
    print()


    return reponse