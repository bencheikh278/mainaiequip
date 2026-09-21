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


# ============================================================
# 1. ANALYSE D'UN RAPPORT
# ============================================================

def analyser_rapport(texte):

    prompt = f"""
Tu es un agent IA spécialisé dans l'analyse
des rapports de maintenance industrielle.

Analyse le rapport suivant.

IMPORTANT :
Un même rapport peut contenir plusieurs équipements.
Analyse chaque équipement séparément.

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
- Identifier les causes lorsqu'elles sont mentionnées.
- Identifier uniquement les interventions QUI ONT RÉELLEMENT ÉTÉ EFFECTUÉES.
- Identifier les résultats après intervention.
- Identifier les techniciens uniquement s'ils sont mentionnés.
- Identifier les recommandations déjà présentes dans le rapport.
- Le niveau d'anomalie peut être :
  "faible", "moyen", "élevé" ou null.

IMPORTANT :

"interventions" représente uniquement ce qui a déjà été fait.

"recommandations" représente ce qui est proposé ou conseillé
dans le rapport.

Ne transforme jamais une recommandation en intervention réalisée.

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
# 2. ANALYSE DE L'HISTORIQUE DES ÉQUIPEMENTS CONCERNÉS
# ============================================================

def analyser_historique_equipements(
    nouveaux_resultats,
    historique
):

    # ========================================================
    # ÉQUIPEMENTS PRÉSENTS DANS LES NOUVEAUX RAPPORTS
    # ========================================================

    equipements_nouveaux = set()

    fichiers_nouveaux = set()

    for rapport in nouveaux_resultats:

        fichier = rapport.get("fichier")

        if fichier:
            fichiers_nouveaux.add(fichier)

        for equipement in rapport.get(
            "equipements",
            []
        ):

            nom = equipement.get("nom")

            if nom:
                equipements_nouveaux.add(nom)

    if not equipements_nouveaux:

        return {
            "equipements_concernes": []
        }

    # ========================================================
    # RECHERCHER UNIQUEMENT CES ÉQUIPEMENTS
    # DANS L'HISTORIQUE
    # ========================================================

    historique_pertinent = []

    for rapport in historique:

        fichier = rapport.get("fichier")

        # IMPORTANT :
        # Ne pas considérer les nouveaux rapports
        # comme faisant partie de leur propre historique.
        if fichier in fichiers_nouveaux:
            continue

        equipements_rapport = []

        for equipement in rapport.get(
            "equipements",
            []
        ):

            nom = equipement.get("nom")

            if nom in equipements_nouveaux:

                equipements_rapport.append(
                    equipement
                )

        if equipements_rapport:

            historique_pertinent.append({

                "fichier": fichier,

                "date": rapport.get("date"),

                "equipements": equipements_rapport

            })

    
    nouveaux_donnees = json.dumps(
        nouveaux_resultats,
        ensure_ascii=False,
        indent=2
    )

    historique_donnees = json.dumps(
        historique_pertinent,
        ensure_ascii=False,
        indent=2
    )

    
    prompt = f"""
Tu es un système intelligent d'aide à la maintenance industrielle.

Tu dois analyser l'historique UNIQUEMENT pour les équipements
présents dans les nouveaux rapports.

OBJECTIF :

Vérifier si les équipements actuellement concernés ont déjà
rencontré des problèmes dans des rapports précédents.

IMPORTANT :

- Analyse uniquement les équipements des nouveaux rapports.
- Ignore complètement les autres équipements.
- Les nouveaux rapports eux-mêmes ne font PAS partie de
  l'historique.
- Identifie les problèmes précédents réellement présents.
- Identifie les interventions précédentes.
- Compare les problèmes actuels avec les problèmes précédents.
- Indique une similarité uniquement lorsqu'elle est justifiée.
- Ne considère pas automatiquement un équipement comme
  récurrent simplement parce qu'il apparaît dans l'historique.
- Ne rien inventer.

Retourne UNIQUEMENT un JSON valide.

Format :

{{
    "equipements_concernes": [
        {{
            "nom": "...",
            "present_dans_historique": true,
            "nb_occurrences_historiques": 0,

            "problemes_precedents": [
                {{
                    "description": "...",
                    "fichier": "...",
                    "date": "...",
                    "intervention": "..."
                }}
            ],

            "probleme_similaire": false,
            "rechute_possible": false,

            "explication": "..."
        }}
    ]
}}

Règles :

1. Une entrée par équipement présent dans les nouveaux rapports.

2. "present_dans_historique" indique si cet équipement apparaît
   dans un ancien rapport.

3. "nb_occurrences_historiques" indique le nombre de rapports
   précédents dans lesquels cet équipement apparaît.

4. "probleme_similaire" = true uniquement lorsqu'un problème
   actuel ressemble réellement à un problème précédent.

5. "rechute_possible" = true uniquement lorsque les informations
   disponibles permettent de considérer qu'un problème similaire
   réapparaît après une intervention précédente.

6. Si aucun historique n'existe :

   "present_dans_historique": false
   "nb_occurrences_historiques": 0
   "problemes_precedents": []
   "probleme_similaire": false
   "rechute_possible": false

7. Ne parle jamais des équipements absents des nouveaux rapports.

================ NOUVEAUX RAPPORTS ================

{nouveaux_donnees}

================ HISTORIQUE PERTINENT ================

{historique_donnees}
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
# 3. SYNTHÈSE DES INTERVENTIONS + RECOMMANDATIONS
# ============================================================

def synthese_globale(
    nouveaux_resultats,
    historique
):

    analyse_historique = (
        analyser_historique_equipements(
            nouveaux_resultats,
            historique
        )
    )

    nouveaux_donnees = json.dumps(
        nouveaux_resultats,
        ensure_ascii=False,
        indent=2
    )

    historique_pertinent_json = json.dumps(
        analyse_historique,
        ensure_ascii=False,
        indent=2
    )

 
    prompt = f"""
Tu es un système intelligent d'aide à la maintenance industrielle.

Tu dois produire :

1. Une SYNTHÈSE DES INTERVENTIONS RÉALISÉES.
2. Des RECOMMANDATIONS DE MAINTENANCE.

Ces deux éléments doivent rester strictement séparés.

============================================================
PARTIE 1 — SYNTHÈSE DES INTERVENTIONS
============================================================

La synthèse doit répondre à :

"Qu'est-ce qui a réellement été fait ?"

Elle doit utiliser UNIQUEMENT les nouveaux rapports.

Elle peut contenir :

- équipement concerné ;
- problème constaté ;
- cause mentionnée ;
- intervention réalisée ;
- pièces remplacées ;
- résultat obtenu ;
- date si disponible ;
- technicien si disponible ;
- durée d'arrêt si disponible dans les données.

IMPORTANT :

Ne jamais présenter une recommandation comme une intervention
déjà réalisée.

Exemple :

Intervention :
"Remplacement du roulement."

Recommandation :
"Effectuer une analyse vibratoire."

La synthèse doit uniquement parler de l'intervention réalisée.

============================================================
PARTIE 2 — RECOMMANDATIONS
============================================================

Les recommandations sont des ACTIONS PROPOSÉES par l'IA.

Elles ne représentent PAS des interventions déjà réalisées.

Elles répondent à :

"Que pourrait-on faire ensuite pour surveiller,
prévenir une récidive ou améliorer la fiabilité ?"

Les recommandations peuvent être basées sur :

- les anomalies détectées ;
- les causes mentionnées ;
- le type d'équipement ;
- les interventions réalisées ;
- les résultats obtenus ;
- l'historique pertinent ;
- les problèmes similaires précédents ;
- les récidives possibles ;
- les règles de maintenance disponibles dans les données.

IMPORTANT :

- Ne jamais inventer une règle constructeur.
- Ne jamais prétendre qu'une action a déjà été réalisée.
- Les recommandations sont des suggestions générées par l'IA.
- Elles doivent être validées par un professionnel de maintenance
  avant exécution.
- Ne recommande pas une action si elle n'est pas justifiée par
  les informations disponibles.

============================================================
HISTORIQUE
============================================================

L'historique fourni concerne UNIQUEMENT les équipements présents
dans les nouveaux rapports.

Ne parle jamais d'un autre équipement.

L'historique peut être utilisé pour améliorer les recommandations.

Par exemple :

Si le nouveau rapport concerne le compresseur C-102 et que
l'historique montre que C-102 a déjà eu un problème similaire,
l'information peut être utilisée dans la justification.

============================================================
FORMAT OBLIGATOIRE
============================================================

Retourne UNIQUEMENT un JSON valide avec exactement ces deux
sections :

{{
    "synthese_interventions": [
        {{
            "equipement": "...",

            "nb_interventions": 0,

            "resume": "Résumé factuel des interventions réellement
réalisées sur cet équipement dans les nouveaux rapports."
        }}
    ],

    "recommandations": [
        {{
            "equipement": "...",

            "priorite": "haute",

            "action": "Action proposée par l'IA.",

            "justification": "Pourquoi cette recommandation est
pertinente selon les rapports et éventuellement l'historique.",

            
        }}
    ]
}}

============================================================
RÈGLES DE LA SYNTHÈSE
============================================================

- Une entrée par équipement présent dans les nouveaux rapports.
- "nb_interventions" concerne uniquement les interventions
  réellement réalisées dans les nouveaux rapports.
- Le résumé doit être factuel.
- Ne pas ajouter une action future dans la synthèse.
- Ne pas utiliser l'historique pour inventer ou modifier
  les interventions réalisées.
- Ne pas présenter une recommandation comme une intervention.


Règles pour les recommandations :

- Les recommandations concernent uniquement les équipements
  présents dans les nouveaux rapports.

- Pour chaque équipement, générer au moins une recommandation
  lorsque les informations disponibles permettent de justifier
  une action future.

- Une recommandation doit être une action FUTURE.

- Ne jamais présenter une intervention déjà réalisée comme
  une recommandation.

- Une recommandation peut être basée sur :
  l'anomalie actuelle,
  la cause,
  l'intervention réalisée,
  le résultat,
  ou l'historique pertinent.

- Si une recommandation est déjà explicitement présente dans
  le rapport, elle peut être reprise ou reformulée.

- Si aucune recommandation pertinente ne peut être justifiée,
  ne pas inventer une action.
============================================================
NOUVEAUX RAPPORTS
============================================================

{nouveaux_donnees}

============================================================
HISTORIQUE PERTINENT
============================================================

{historique_pertinent_json}
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

    # RETOURNER LE RÉSULTAT

    return json.loads(
        response.choices[0].message.content
    )