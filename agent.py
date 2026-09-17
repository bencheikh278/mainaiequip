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


def synthese_globale(resultats):

    donnees = json.dumps(
        resultats,
        ensure_ascii=False,
        indent=2
    )

    prompt = f"""
Tu es un système intelligent d'aide à la maintenance industrielle.

Voici l'historique des analyses de plusieurs rapports.

Analyse ces données et produis une synthèse.

Tu dois identifier :

1. Les équipements présentant des problèmes répétés.
2. Les anomalies récurrentes.
3. Les tendances observées.
4. Les équipements nécessitant une surveillance.
5. Les recommandations de maintenance.

Ne crée aucune information qui n'existe pas
dans les données.

Données :

{donnees}

Réponds en français avec une structure claire.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content