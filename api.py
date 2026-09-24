import os
import hashlib
import tempfile
from datetime import datetime

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
# CALCUL DU HASH
# ============================================================

def calculer_hash(texte):
    """
    Calcule un SHA-256 du contenu extrait.
    Deux fichiers avec le même contenu auront le même hash.
    """
    return hashlib.sha256(
        texte.encode("utf-8")
    ).hexdigest()


# ============================================================
# ANALYSE D'UN FICHIER
# ============================================================

@app.post("/api/analyse")
async def analyser_fichier(
    fichier: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Vérification du nom
    # --------------------------------------------------------

    if not fichier.filename:
        raise HTTPException(
            status_code=400,
            detail="Aucun fichier reçu."
        )

    print()
    print("=" * 60)
    print(f"📄 Fichier reçu : {fichier.filename}")
    print("=" * 60)


    # --------------------------------------------------------
    # Lire le fichier
    # --------------------------------------------------------

    contenu = await fichier.read()

    if not contenu:
        raise HTTPException(
            status_code=400,
            detail="Le fichier est vide."
        )

    print(f"📦 Taille : {len(contenu)} octets")


    # --------------------------------------------------------
    # Vérification taille : 20 Mo
    # --------------------------------------------------------

    taille_max = 20 * 1024 * 1024

    if len(contenu) > taille_max:
        raise HTTPException(
            status_code=413,
            detail="Le fichier dépasse la limite de 20 Mo."
        )


    # --------------------------------------------------------
    # Créer un fichier temporaire
    # --------------------------------------------------------

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
        # 1. EXTRACTION
        # ====================================================

        print("🔍 Extraction du texte...")

        texte = extract_text(chemin_temp)

        if not texte:
            raise HTTPException(
                status_code=400,
                detail="Impossible d'extraire le texte du fichier."
            )

        texte = texte.strip()

        if len(texte) < 30:
            raise HTTPException(
                status_code=400,
                detail="Le fichier ne contient pas suffisamment de texte exploitable."
            )

        print(f"📝 Texte extrait : {len(texte)} caractères")


        # ====================================================
        # 2. HASH
        # ====================================================

        hash_contenu = calculer_hash(texte)

        print(
            f"🔐 Hash : {hash_contenu}"
        )


        # ====================================================
        # 3. CONNEXION SQLITE
        # ====================================================

        connexion = bdd.connecter()

        try:

            # =================================================
            # 4. CHERCHER DANS SQLITE
            # =================================================

            rapport_existant = (
                bdd.recuperer_rapport_par_hash(
                    connexion,
                    hash_contenu
                )
            )


            # =================================================
            # 5. RAPPORT DÉJÀ ANALYSÉ
            # =================================================

            if rapport_existant:

                print(
                    "♻️ Rapport déjà analysé → récupération depuis SQLite"
                )

                resultat = rapport_existant

                # On garde le nom du fichier envoyé actuellement
                resultat["fichier"] = fichier.filename
                resultat["hash_contenu"] = hash_contenu


            # =================================================
            # 6. NOUVEAU RAPPORT
            # =================================================

            else:

                print(
                    "🤖 Nouvelle analyse IA..."
                )

                resultat = analyser_rapport(
                    texte
                )

                if not resultat:
                    raise HTTPException(
                        status_code=500,
                        detail="L'analyse IA n'a retourné aucun résultat."
                    )


                # ---------------------------------------------
                # Ajouter les métadonnées
                # ---------------------------------------------

                resultat["fichier"] = fichier.filename

                resultat["hash_contenu"] = hash_contenu

                resultat["analyse_le"] = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )


                # ---------------------------------------------
                # Sauvegarde SQLite
                # ---------------------------------------------

                print(
                    "💾 Sauvegarde dans SQLite..."
                )

                bdd.inserer_rapport(
                    connexion,
                    resultat
                )

                print(
                    "✅ Rapport sauvegardé"
                )


            # =================================================
            # 7. RÉCUPÉRER L'HISTORIQUE
            # =================================================

            historique = (
                bdd.recuperer_historique(
                    connexion
                )
            )

            print(
                f"📚 Historique SQLite : {len(historique)} rapports"
            )


            # =================================================
            # 8. SYNTHÈSE + RECOMMANDATIONS
            # =================================================

            print(
                "📊 Génération de la synthèse et des recommandations..."
            )

            try:

                synthese = synthese_globale(
                    [resultat],
                    historique
                )

            except Exception as e:

                print(
                    f"❌ Erreur synthèse : {e}"
                )

                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Le service IA est temporairement indisponible. "
                        "Veuillez réessayer dans quelques instants."
                    )
                )


            print(
                "✅ Analyse terminée"
            )


            # =================================================
            # 9. RETOUR JSON
            # =================================================

            return {
                "status": "success",

                "filename": fichier.filename,

                "analyse": resultat,

                "synthese": synthese
            }


        finally:

            connexion.close()


    finally:

        # ====================================================
        # 10. SUPPRIMER LE FICHIER TEMPORAIRE
        # ====================================================

        if (
            chemin_temp
            and os.path.exists(chemin_temp)
        ):
            os.remove(chemin_temp)
