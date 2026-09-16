import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from extract import extract_text

load_dotenv()

client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

MODEL = "gemini-3.5-flash-lite"

FICHIER_HISTORIQUE = "output/historique.json"


# ============================================================
# ETAPE 1 : analyser UN SEUL rapport avec l'IA
# ============================================================

def analyser_rapport(texte):
    prompt = f"""Tu es un agent IA specialise en maintenance industrielle.
Voici un rapport d'intervention. Analyse-le et reponds UNIQUEMENT en JSON,
sans markdown, sans texte avant ou apres.

Format attendu :
{{
  "reference": "...",
  "date": "...",
  "equipement": "...",
  "technicien": "...",
  "probleme": "resume du probleme en une phrase",
  "recurrent": true ou false,
  "recommandation": "ta recommandation en une ou deux phrases"
}}

Si une information est absente, mets null. N'invente rien.

RAPPORT :
---
{texte}
---
"""
    reponse = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(reponse.choices[0].message.content)


# ============================================================
# ETAPE 2 : historique (charger / sauvegarder)
# ============================================================

def charger_historique():
    if not os.path.exists(FICHIER_HISTORIQUE):
        print("[historique] aucun fichier existant -> on part de zero")
        return []

    with open(FICHIER_HISTORIQUE, "r", encoding="utf-8") as f:
        historique = json.load(f)

    print(f"[historique] {len(historique)} rapport(s) deja dedans")
    return historique


def sauvegarder_historique(historique):
    os.makedirs("output", exist_ok=True)
    with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


# ============================================================
# ETAPE 3 : analyser un ou plusieurs dossiers
# ============================================================

def analyser_dossier(*dossiers):
    """
    Accepte un ou plusieurs dossiers en meme temps.
    Exemple : analyser_dossier("data/reports_txt", "data/reports_pdf")

    Sauvegarde l'historique APRES CHAQUE rapport reussi, donc si ca
    plante en cours de route (quota API, etc.), rien n'est perdu.
    Les fichiers deja presents dans l'historique sont ignores
    (pas de doublons si tu relances le script).
    """
    historique = charger_historique()
    fichiers_deja_connus = {entree["fichier"] for entree in historique}

    for dossier in dossiers:
        if not os.path.isdir(dossier):
            print(f"{dossier} : dossier introuvable, ignore")
            continue

        for nom_fichier in sorted(os.listdir(dossier)):
            if nom_fichier in fichiers_deja_connus:
                print(f"{nom_fichier} : deja analyse, ignore")
                continue

            chemin = os.path.join(dossier, nom_fichier)
            texte = extract_text(chemin)

            if len(texte.strip()) < 30:
                print(f"{nom_fichier} : ignore (vide ou illisible)")
                continue

            print(f"{nom_fichier} : analyse en cours...")

            try:
                donnees = analyser_rapport(texte)
            except Exception as e:
                print(f"  ERREUR sur {nom_fichier} : {e}")
                print("  -> arret. Les rapports deja traites sont sauvegardes.")
                return historique

            donnees["fichier"] = nom_fichier
            donnees["analyse_le"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            historique.append(donnees)
            fichiers_deja_connus.add(nom_fichier)
            sauvegarder_historique(historique)   # sauvegarde immediate

    return historique


# ============================================================
# ETAPE 4 : synthese globale (patterns entre plusieurs rapports)
# ============================================================

def synthese_globale(resultats):
    resume = json.dumps(resultats, ensure_ascii=False, indent=2)

    prompt = f"""Voici l'analyse individuelle de plusieurs rapports de
maintenance. Croise ces informations et identifie :
1. les equipements a risque (pannes repetees)
2. les patterns communs entre rapports differents
3. tes recommandations prioritaires pour l'equipe maintenance

Donnees :
{resume}

Reponds en francais, de maniere claire et structuree."""

    reponse = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return reponse.choices[0].message.content


# ============================================================
# LANCER TOUT
# ============================================================

if __name__ == "__main__":
    historique = analyser_dossier(
        "data/reports_txt",
        "data/reports_pdf",
        "data/reports_docx",
    )

    print(f"\n-> output/historique.json ({len(historique)} rapport(s) au total)\n")

    if historique:
        print("=== SYNTHESE GLOBALE (basee sur tout l'historique) ===\n")
        try:
            synthese = synthese_globale(historique)
            print(synthese)

            with open("output/synthese_ia.txt", "w", encoding="utf-8") as f:
                f.write(synthese)
            print("\n-> output/synthese_ia.txt")

        except Exception as e:
            print(f"Synthese non generee (quota ?) : {e}")
    else:
        print("Aucun rapport dans l'historique, rien a synthetiser.")