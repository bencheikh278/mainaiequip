import os
import json

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()


client = OpenAI(
    api_key=os.environ["GEMINI_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


MODEL = "gemini-3.5-flash-lite"


def analyser_rapport(texte):

    prompt = f"""
Tu es un agent IA spécialisé dans l'analyse
des rapports de maintenance industrielle.

Analyse le rapport suivant.

Un même rapport peut contenir plusieurs équipements.
Il faut donc analyser chaque équipement séparément.

Retourne UNIQUEMENT un JSON valide.


Format obligatoire :

{{
    "reference": null,
    "date": null,

    "equipements": [
        {{
            "nom": null,
            "type": null,

            "anomalies": [
                {{
                    "description": null,
                    "niveau": null
                }}
            ],

            "causes": [],

            "interventions": [],

            "resultats": []
        }}
    ],

    "techniciens": [],

    "recommandations": []
}}

Règles :


- Si une information n'existe pas, utiliser null.
- Ne rien inventer.
- Garder les informations de chaque équipement séparées.
- Identifier toutes les anomalies présentes.
- Identifier les interventions réalisées.
- Identifier les causes lorsqu'elles sont mentionnées.
- Identifier le résultat après intervention.
- Le niveau d'anomalie peut être :
  "faible", "moyen", "élevé" ou null.

RAPPORT :

--------------------

{texte}

--------------------
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        }
    )


    return json.loads(
        response.choices[0].message.content
    )


# ============================================================
# DETECTION D'ANOMALIES PAR L'IA 
# ============================================================

def detecter_anomalies_ia(historique):
    """
    Demande a l'IA d'analyser tout l'historique et de detecter
    elle-meme les equipements recurrents et les rechutes (probleme
    marque resolu puis redevenu actif plus tard).
    """
    donnees = json.dumps(historique, ensure_ascii=False, indent=2)

    prompt = f"""
Tu es un agent IA specialise dans la detection d'anomalies de
maintenance industrielle.

Voici l'historique complet des rapports deja analyses. Chaque
rapport contient une date, un fichier source, et une liste
d'equipements avec leurs anomalies et resultats d'intervention.

Ta mission :

1. Regroupe les equipements par nom (le meme equipement peut
   apparaitre dans plusieurs rapports differents).
2. Pour chaque equipement qui apparait 2 fois ou plus, retrace

   la chronologie de ses interventions dans l'ordre des dates.
3. Pour chaque intervention, determine si le resultat indique que
   le probleme est "resolu" ou reste "actif" (base-toi sur le champ
   "resultats" de chaque equipement).
4. Detecte les RECHUTES : un equipement dont le statut passe de
   "resolu" a "actif" a un moment ulterieur.
5. Determine le statut actuel de chaque equipement recurrent.

Retourne UNIQUEMENT un JSON valide, dans ce format exact :

{{
    "equipements_recurrents": [
        {{
            "nom": "...",
            "nb_occurrences": 0,
            "fichiers_concernes": ["..."],
            "chronologie": [
                {{"fichier": "...", "date": "...", "statut": "resolu ou actif"}}
            ],
            "nb_rechutes": 0,
            "statut_actuel": "resolu ou actif",
            "alerte": "description courte du niveau de risque"
        }}
    ]
}}

Ne considere PAS un equipement qui n'apparait qu'une seule fois.
Ne rien inventer.

HISTORIQUE :
--------------------
{donnees}

--------------------
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        }
    )

    return json.loads(
        response.choices[0].message.content
    )


# ============================================================
# SYNTHESE GLOBALE : 2 livrables
# -- "synthese des interventions realisees" + "recommandations"
# ============================================================

def synthese_globale(resultats):

    anomalies = detecter_anomalies_ia(resultats)

    donnees = json.dumps(
        resultats,

        ensure_ascii=False,
        indent=2
    )

    anomalies_json = json.dumps(
        anomalies,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
Tu es un système intelligent d'aide à la maintenance industrielle.

Voici l'historique complet des interventions de maintenance, ainsi
qu'une analyse des équipements récurrents et de leurs rechutes
(information de contexte, à utiliser pour prioriser, mais à ne
pas restituer telle quelle) :

{anomalies_json}

Produis UNIQUEMENT un JSON valide avec exactement 2 sections :

{{
    "synthese_interventions": [
        {{
            "equipement": "...",
            "nb_interventions": 0,
            "resume": "resume factuel de 1 a 2 phrases : quel
                probleme, quelle action realisee, quel resultat"
        }}
    ],


    "recommandations": [
        {{
            "equipement": "...",
            "priorite": "haute, moyenne ou basse",
            "action": "action concrete et courte a realiser",
            "justification": "pourquoi, en une phrase"
        }}
    ]
}}

Une entree par equipement dans "synthese_interventions" (pas de
paragraphe global). Trie "recommandations" par priorite (haute en
premier). Un equipement en recidive (rechute detectee) passe
automatiquement en priorite haute.

Ne crée aucune information qui n'existe pas dans les données.

Données complètes :

{donnees}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"

        }
    )

    return json.loads(
        response.choices[0].message.content
    )