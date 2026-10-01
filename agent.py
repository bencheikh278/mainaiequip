import json
import re
from typing import Any, Dict, List

import requests


# ============================================================
# CONFIGURATION VLLM
# ============================================================

BASE_URL = "http://10.109.28.102:8000"
GENERATION_ENDPOINT = "/v1/chat/completions"
MODEL = "sonatrach-IA"

TIMEOUT = 180


# ============================================================
# EXCEPTIONS
# ============================================================

class VLLMIndisponible(Exception):
    pass


class ReponseModeleInvalide(Exception):
    pass


# ============================================================
# PROMPT SYSTÈME
# ============================================================

SYSTEM_PROMPT = """
Tu es SYNIA, un assistant spécialisé dans l'analyse des
documents de maintenance des équipements industriels.

Tu travailles uniquement à partir de rapports de maintenance
réels fournis par l'utilisateur.

============================================================
RÈGLE PRINCIPALE : FIDÉLITÉ AU DOCUMENT
============================================================

Utilise UNIQUEMENT les informations présentes dans les
documents.

INTERDICTION ABSOLUE d'inventer :

- panne
- anomalie
- cause
- intervention
- pièce remplacée
- date
- mesure
- valeur
- résultat
- technicien
- équipement
- historique
- événement technique

Si une information n'est pas présente :

- utilise null pour une valeur unique ;
- utilise [] pour une liste ;
- ne devine pas.

============================================================
DISTINCTION DES ACTIONS
============================================================

1. INTERVENTION RÉALISÉE

Action réellement effectuée et documentée.

2. INTERVENTION PLANIFIÉE

Action prévue mais pas encore réalisée.

3. RECOMMANDATION SYNIA

Conseil futur généré par SYNIA à partir des informations
réellement présentes.

Ne présente JAMAIS une recommandation SYNIA comme une
intervention déjà réalisée.

============================================================
ÉQUIPEMENTS
============================================================

Un même équipement peut apparaître dans plusieurs rapports.

Lorsque plusieurs rapports concernent le même équipement,
leurs informations doivent être considérées comme son
historique.

Ne mélange jamais deux équipements différents.

============================================================
STYLE
============================================================

Les résultats doivent être :

- en français ;
- courts ;
- clairs ;
- professionnels ;
- naturels ;
- reformulés ;
- sans répétitions inutiles.

Ne copie pas inutilement les phrases des rapports.

============================================================
RECOMMANDATIONS
============================================================

Une recommandation peut être produite :

- après une intervention ;
- lorsqu'une anomalie est documentée ;
- lorsqu'un problème est signalé sans intervention ;
- lorsqu'un suivi est logiquement justifié par les informations
  disponibles.

Une intervention déjà réalisée ne signifie PAS qu'il ne faut
plus produire de recommandation.

Mais une recommandation doit toujours être justifiée par les
informations disponibles.

N'invente jamais une opération technique précise simplement
pour remplir la liste.

Si aucune recommandation raisonnable ne peut être déduite,
retourne [].

Priorités autorisées :

- faible
- moyenne
- élevée
"""


# ============================================================
# APPEL VLLM
# ============================================================

def appeler_modele(
    prompt: str,
    max_tokens: int = 2500
) -> Any:

    url = BASE_URL + GENERATION_ENDPOINT

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }

    print("\n==========================================")
    print(">>> APPEL VLLM")
    print(">>> URL :", url)
    print(">>> MODEL :", MODEL)
    print("==========================================\n")

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT
        )

    except requests.exceptions.RequestException as e:

        print(
            ">>> ERREUR CONNEXION VLLM :",
            e
        )

        raise VLLMIndisponible(
            f"Impossible de contacter le serveur VLLM : {e}"
        )

    print(
        ">>> STATUS VLLM :",
        response.status_code
    )

    if response.status_code != 200:

        print(
            ">>> REPONSE VLLM :",
            response.text[:2000]
        )

        raise VLLMIndisponible(
            f"VLLM a retourné HTTP {response.status_code}"
        )

    try:

        data = response.json()

    except Exception as e:

        raise ReponseModeleInvalide(
            f"Réponse VLLM non JSON : {e}"
        )

    try:

        content = data["choices"][0]["message"]["content"]

    except Exception:

        print(
            ">>> STRUCTURE VLLM INATTENDUE :",
            data
        )

        raise ReponseModeleInvalide(
            "Impossible de récupérer le contenu du modèle."
        )

    print("\n>>> REPONSE MODELE :")
    print(content)
    print("\n")

    return nettoyer_json(content)


# ============================================================
# NETTOYAGE JSON
# ============================================================

def nettoyer_json(
    texte: str
) -> Any:

    if not texte:

        raise ReponseModeleInvalide(
            "Réponse du modèle vide."
        )

    texte = texte.strip()

    # Retirer ```json
    texte = re.sub(
        r"^```json\s*",
        "",
        texte,
        flags=re.IGNORECASE
    )

    # Retirer ```
    texte = re.sub(
        r"^```\s*",
        "",
        texte
    )

    texte = re.sub(
        r"\s*```$",
        "",
        texte
    )

    texte = texte.strip()

    # Essai direct
    try:

        return json.loads(texte)

    except json.JSONDecodeError:

        pass

    # Chercher un objet JSON
    debut_objet = texte.find("{")
    fin_objet = texte.rfind("}")

    if (
        debut_objet != -1
        and fin_objet != -1
        and fin_objet > debut_objet
    ):

        extrait = texte[
            debut_objet:fin_objet + 1
        ]

        try:

            return json.loads(extrait)

        except json.JSONDecodeError:

            pass

    # Chercher un tableau JSON
    debut_liste = texte.find("[")
    fin_liste = texte.rfind("]")

    if (
        debut_liste != -1
        and fin_liste != -1
        and fin_liste > debut_liste
    ):

        extrait = texte[
            debut_liste:fin_liste + 1
        ]

        try:

            return json.loads(extrait)

        except json.JSONDecodeError:

            pass

    print(
        ">>> JSON IMPOSSIBLE À PARSER :"
    )

    print(texte)

    raise ReponseModeleInvalide(
        "Le modèle n'a pas retourné un JSON valide."
    )


# ============================================================
# NORMALISATION LISTE
# ============================================================

def normaliser_liste(
    valeur: Any
) -> List[Any]:

    if valeur is None:

        return []

    if isinstance(
        valeur,
        list
    ):

        return valeur

    return [valeur]


# ============================================================
# NORMALISATION NOM ÉQUIPEMENT
# ============================================================

def normaliser_nom_equipement(
    nom: str
) -> str:

    nom = nom.strip().lower()

    # Espaces multiples
    nom = re.sub(
        r"\s+",
        " ",
        nom
    )

    # Quelques séparateurs fréquents
    nom = nom.replace(
        "–",
        "-"
    )

    nom = nom.replace(
        "—",
        "-"
    )

    return nom


# ============================================================
# LISTER LES ÉQUIPEMENTS
# ============================================================

def _lister_equipements(
    texte: str
) -> List[str]:

    prompt = f"""
Analyse le document de maintenance ci-dessous.

DOCUMENT :
{texte}

Ta tâche est UNIQUEMENT d'identifier tous les équipements
explicitement présents dans le document.

Règles :

- conserve tous les équipements clairement identifiés ;
- plusieurs équipements peuvent être présents ;
- ne crée aucun équipement absent du document ;
- ne transforme pas une pièce ou une valeur en équipement ;
- utilise le nom utilisé dans le document lorsque possible.

Retourne UNIQUEMENT :

{{
  "equipements": [
    "Equipement 1",
    "Equipement 2"
  ]
}}
"""

    resultat = appeler_modele(
        prompt,
        max_tokens=1200
    )

    if not isinstance(
        resultat,
        dict
    ):

        return []

    equipements = resultat.get(
        "equipements",
        []
    )

    equipements = normaliser_liste(
        equipements
    )

    resultat_final = []

    noms_normalises = set()

    for equipement in equipements:

        if not isinstance(
            equipement,
            str
        ):

            continue

        equipement = equipement.strip()

        if not equipement:

            continue

        cle = normaliser_nom_equipement(
            equipement
        )

        if cle not in noms_normalises:

            resultat_final.append(
                equipement
            )

            noms_normalises.add(
                cle
            )

    print(
        ">>> EQUIPEMENTS IDENTIFIÉS :",
        resultat_final
    )

    return resultat_final


# ============================================================
# EXTRACTION DES FAITS PAR ÉQUIPEMENT
# ============================================================

def _extraire_equipement(
    texte: str,
    equipement: str
) -> Dict[str, Any]:

    prompt = f"""
Analyse uniquement les informations du document concernant
l'équipement suivant :

ÉQUIPEMENT :
{equipement}

DOCUMENT :
{texte}

============================================================
OBJECTIF
============================================================

Extraire uniquement les faits réellement présents dans
le document.

Ne rien inventer.

============================================================
À EXTRAIRE
============================================================

1. description

Description courte de l'équipement ou de sa situation
si elle est explicitement documentée.

2. anomalies

Chaque anomalie doit contenir :

- description
- niveau
- statut

Niveau :
- faible
- moyen
- élevé
- null

Statut :
- active
- résolue
- planifiée
- inconnue

3. causes

Uniquement les causes explicitement indiquées.

4. interventions_realisees

Uniquement les actions réellement effectuées.

5. interventions_planifiees

Uniquement les actions prévues mais non encore réalisées.

6. resultats

Résultats réellement documentés après intervention.

7. informations_techniques

Informations techniques réellement présentes.

8. techniciens

Techniciens explicitement mentionnés.

============================================================
IMPORTANT
============================================================

Ne transforme jamais une recommandation en intervention.

Ne transforme jamais une intervention prévue en intervention
réalisée.

Ne crée aucune anomalie si elle n'est pas documentée.

Si une information est absente :

- null pour une valeur ;
- [] pour une liste.

============================================================
FORMAT
============================================================

Retourne uniquement :

{{
  "description": null,
  "anomalies": [],
  "causes": [],
  "interventions_realisees": [],
  "interventions_planifiees": [],
  "resultats": [],
  "informations_techniques": [],
  "techniciens": []
}}
"""

    resultat = appeler_modele(
        prompt,
        max_tokens=2200
    )

    if not isinstance(
        resultat,
        dict
    ):

        resultat = {}

    resultat.setdefault(
        "description",
        None
    )

    resultat.setdefault(
        "anomalies",
        []
    )

    resultat.setdefault(
        "causes",
        []
    )

    resultat.setdefault(
        "interventions_realisees",
        []
    )

    resultat.setdefault(
        "interventions_planifiees",
        []
    )

    resultat.setdefault(
        "resultats",
        []
    )

    resultat.setdefault(
        "informations_techniques",
        []
    )

    resultat.setdefault(
        "techniciens",
        []
    )

    for champ in [
        "anomalies",
        "causes",
        "interventions_realisees",
        "interventions_planifiees",
        "resultats",
        "informations_techniques",
        "techniciens"
    ]:

        resultat[champ] = normaliser_liste(
            resultat.get(champ)
        )

    print(
        "\n>>> EXTRACTION :",
        equipement
    )

    print(
        json.dumps(
            resultat,
            ensure_ascii=False,
            indent=2
        )
    )

    return resultat


# ============================================================
# ANALYSE D'UN ÉQUIPEMENT
# ============================================================

def _analyser_equipement(
    equipement: str,
    faits: Dict[str, Any]
) -> Dict[str, Any]:

    prompt = f"""
Tu es SYNIA.

Tu dois analyser les informations déjà extraites pour
l'équipement suivant.

ÉQUIPEMENT :
{equipement}

FAITS EXTRAITS :
{json.dumps(
    faits,
    ensure_ascii=False,
    indent=2
)}

============================================================
SYNTHÈSE DE L'ÉQUIPEMENT
============================================================

Produis une description courte et reformulée.

Ne copie pas inutilement les données.

La synthèse doit rester strictement fidèle aux faits.

Si une intervention a été réalisée :
mentionne brièvement ce qui a été fait.

Si aucune intervention n'a été réalisée :
mentionne quand même l'équipement.

Si un problème ou une anomalie est documenté :
mentionne-le brièvement.

Si aucune information importante n'est disponible :
reste très court.

============================================================
ANOMALIES
============================================================

Conserve uniquement les anomalies présentes dans les faits.

Ne crée aucune anomalie.

============================================================
RECOMMANDATIONS
============================================================

Tu peux produire une recommandation même si une intervention
a déjà été réalisée.

Exemples :

- suivi après intervention ;
- surveillance de l'évolution ;
- contrôle périodique ;
- suivi d'une anomalie documentée ;
- contrôle lorsqu'un problème est signalé.

Mais la recommandation doit être liée aux faits.

NE PAS inventer :

- panne ;
- cause ;
- pièce ;
- mesure ;
- réparation ;
- opération technique non justifiée.

Une recommandation est un CONSEIL FUTUR de SYNIA.

Elle ne doit jamais être présentée comme une action déjà
réalisée.

Si aucune recommandation raisonnable n'est possible :
retourne [].

============================================================
FORMAT OBLIGATOIRE
============================================================

Retourne uniquement :

{{
  "equipement": "{equipement}",
  "description": null,
  "anomalies": [],
  "causes": [],
  "interventions_realisees": [],
  "interventions_planifiees": [],
  "resultats": [],
  "informations_techniques": [],
  "recommandations": [
    {{
      "action": "...",
      "priorite": "faible"
    }}
  ]
}}

Priorités autorisées :

- faible
- moyenne
- élevée
"""

    resultat = appeler_modele(
        prompt,
        max_tokens=2200
    )

    if not isinstance(
        resultat,
        dict
    ):

        resultat = {}

    resultat["equipement"] = equipement

    resultat.setdefault(
        "description",
        faits.get("description")
    )

    resultat.setdefault(
        "anomalies",
        faits.get("anomalies", [])
    )

    resultat.setdefault(
        "causes",
        faits.get("causes", [])
    )

    resultat.setdefault(
        "interventions_realisees",
        faits.get("interventions_realisees", [])
    )

    resultat.setdefault(
        "interventions_planifiees",
        faits.get("interventions_planifiees", [])
    )

    resultat.setdefault(
        "resultats",
        faits.get("resultats", [])
    )

    resultat.setdefault(
        "informations_techniques",
        faits.get("informations_techniques", [])
    )

    resultat.setdefault(
        "recommandations",
        []
    )

    for champ in [
        "anomalies",
        "causes",
        "interventions_realisees",
        "interventions_planifiees",
        "resultats",
        "informations_techniques",
        "recommandations"
    ]:

        resultat[champ] = normaliser_liste(
            resultat.get(champ)
        )

    print(
        "\n>>> ANALYSE ÉQUIPEMENT :",
        equipement
    )

    print(
        json.dumps(
            resultat,
            ensure_ascii=False,
            indent=2
        )
    )

    return resultat


# ============================================================
# ANALYSER UN RAPPORT COMPLET
# ============================================================

def analyser_rapport(
    texte: str
) -> List[Dict[str, Any]]:

    if not texte or not texte.strip():

        raise ValueError(
            "Le texte du rapport est vide."
        )

    print("\n")
    print("==========================================")
    print(">>> ANALYSE DU RAPPORT")
    print("==========================================")

    print(
        ">>> Nombre de caractères :",
        len(texte)
    )

    # --------------------------------------------------------
    # 1. Identifier les équipements
    # --------------------------------------------------------

    equipements = _lister_equipements(
        texte
    )

    if not equipements:

        print(
            ">>> Aucun équipement identifié."
        )

        return []

    print(
        ">>> Nombre d'équipements :",
        len(equipements)
    )

    analyses = []

    # --------------------------------------------------------
    # 2. Analyser chaque équipement
    # --------------------------------------------------------

    for equipement in equipements:

        try:

            faits = _extraire_equipement(
                texte,
                equipement
            )

            analyse = _analyser_equipement(
                equipement,
                faits
            )

            analyses.append(
                analyse
            )

        except Exception as e:

            print(
                f">>> ERREUR équipement "
                f"{equipement} : {e}"
            )

            continue

    print("\n")
    print("==========================================")
    print(">>> ANALYSE RAPPORT TERMINÉE")

    print(
        ">>> Équipements analysés :",
        len(analyses)
    )

    print("==========================================")

    return analyses


# ============================================================
# REGROUPER LES ÉQUIPEMENTS DES DIFFÉRENTS RAPPORTS
# ============================================================

def regrouper_par_equipement(
    resultats: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    groupes = {}

    for resultat in resultats:

        if not isinstance(
            resultat,
            dict
        ):
            continue

        equipement = resultat.get(
            "equipement",
            ""
        )

        if not equipement:
            continue

        cle = normaliser_nom_equipement(
            equipement
        )

        if cle not in groupes:

            groupes[cle] = {
                "equipement": equipement,
                "historique": []
            }

        groupes[cle]["historique"].append(
            resultat
        )

    groupes_final = list(
        groupes.values()
    )

    print("\n")
    print("==========================================")
    print(">>> REGROUPEMENT DES ÉQUIPEMENTS")
    print("==========================================")

    for groupe in groupes_final:

        print(
            f">>> {groupe['equipement']} : "
            f"{len(groupe['historique'])} occurrence(s)"
        )

    print("==========================================")

    return groupes_final


# ============================================================
# SYNTHÈSE GLOBALE
# ============================================================

def synthese_globale(
    resultats: List[Dict[str, Any]]
) -> Dict[str, Any]:

    if not resultats:

        return {
            "synthese_interventions": [],
            "recommandations": []
        }

    # --------------------------------------------------------
    # Regrouper les mêmes équipements
    # --------------------------------------------------------

    resultats_groupes = regrouper_par_equipement(
        resultats
    )

    # --------------------------------------------------------
    # Prompt de synthèse
    # --------------------------------------------------------

    prompt = f"""
Tu es SYNIA, spécialisé dans la synthèse de rapports
de maintenance industrielle.

Les données ci-dessous sont déjà regroupées par équipement.

DONNÉES :

{json.dumps(
    resultats_groupes,
    ensure_ascii=False,
    indent=2
)}

============================================================
OBJECTIF
============================================================

Produire :

1. UNE synthèse pour CHAQUE équipement ;

2. des recommandations futures pertinentes.

Un équipement peut apparaître dans plusieurs rapports.

Tu dois donc considérer toutes les informations de son
historique disponible.

Ne crée jamais plusieurs synthèses pour le même équipement.

============================================================
SYNTHÈSE PAR ÉQUIPEMENT
============================================================

Pour chaque équipement, produis UNE synthèse globale.

Prends en compte uniquement les événements importants.

Tu peux mentionner :

- problème ou anomalie documenté ;
- intervention réalisée ;
- résultat documenté ;
- évolution clairement documentée ;
- intervention planifiée si elle est importante.

Ne répète pas plusieurs fois la même information.

Ne copie pas les phrases originales.

============================================================
LONGUEUR
============================================================

La longueur doit être adaptée à la quantité d'information :

- 1 phrase si les informations sont limitées ;
- 2 phrases dans un cas normal ;
- 3 phrases maximum si plusieurs événements importants
  doivent être résumés.

Ne dépasse JAMAIS 3 phrases par équipement.

Ne remplis pas artificiellement la synthèse.

============================================================
CAS PARTICULIERS
============================================================

CAS 1 — intervention réalisée

Résume brièvement ce qui a été réalisé.

CAS 2 — problème ou anomalie sans intervention

Mentionne brièvement le problème documenté.

Ne crée aucune intervention.

CAS 3 — équipement présent sans problème important

Mentionne simplement l'équipement de manière courte.

Exemple :

"Le ventilateur V-301 est mentionné dans les rapports,
sans intervention détaillée."

============================================================
ÉVOLUTION ENTRE RAPPORTS
============================================================

Si plusieurs rapports concernent le même équipement,
tu peux mentionner une évolution UNIQUEMENT si elle est
explicitement présente dans les données.

Par exemple :

- problème puis intervention ;
- intervention puis résultat ;
- anomalie puis résolution documentée.

Ne déduis jamais une amélioration ou une aggravation
si elle n'est pas documentée.

============================================================
RECOMMANDATIONS
============================================================

Les recommandations doivent être produites au niveau
de l'équipement.

Ne crée pas une recommandation séparée pour chaque rapport.

Si plusieurs rapports concernent le même équipement,
évite les recommandations répétitives.

Une seule recommandation claire peut suffire lorsqu'elle
couvre correctement la situation.

Une recommandation peut être produite même lorsqu'une
intervention a déjà été réalisée, si les informations
justifient un suivi.

Exemple :

Intervention :
"Remplacement du joint."

Recommandation :
"Surveiller l'étanchéité après l'intervention."

Un équipement ayant un problème sans intervention peut
recevoir une recommandation de suivi ou de contrôle si
cela est cohérent avec les informations disponibles.

NE JAMAIS inventer :

- panne ;
- cause ;
- réparation ;
- pièce ;
- mesure ;
- valeur ;
- intervention future précise non justifiée.

Les recommandations sont des CONSEILS FUTURS DE SYNIA.

Elles ne sont pas des interventions déjà réalisées.

============================================================
PRIORITÉS
============================================================

Utilise uniquement :

"faible"
"moyenne"
"élevée"

La priorité doit être cohérente avec la gravité
réellement documentée.

Ne donne pas automatiquement "élevée".

============================================================
FORMAT OBLIGATOIRE
============================================================

Retourne UNIQUEMENT un JSON valide :

{{
  "synthese_interventions": [
    {{
      "equipement": "Nom",
      "resume": "Résumé court et reformulé."
    }}
  ],

  "recommandations": [
    {{
      "equipement": "Nom",
      "action": "Conseil futur court.",
      "priorite": "moyenne"
    }}
  ]
}}

Ne retourne aucun texte avant ou après le JSON.
"""

    try:

        resultat = appeler_modele(
            prompt,
            max_tokens=3500
        )

    except Exception as e:

        print(
            ">>> ERREUR SYNTHÈSE :",
            e
        )

        return {
            "synthese_interventions": [],
            "recommandations": []
        }

    if not isinstance(
        resultat,
        dict
    ):

        return {
            "synthese_interventions": [],
            "recommandations": []
        }

    synthese_interventions = resultat.get(
        "synthese_interventions",
        []
    )

    recommandations = resultat.get(
        "recommandations",
        []
    )

    synthese_interventions = normaliser_liste(
        synthese_interventions
    )

    recommandations = normaliser_liste(
        recommandations
    )

    # ========================================================
    # NETTOYAGE SYNTHÈSE
    # ========================================================

    synthese_finale = []

    for item in synthese_interventions:

        if isinstance(
            item,
            str
        ):

            if item.strip():

                synthese_finale.append(
                    {
                        "equipement": "",
                        "resume": item.strip()
                    }
                )

            continue

        if not isinstance(
            item,
            dict
        ):

            continue

        equipement = item.get(
            "equipement",
            ""
        )

        resume = item.get(
            "resume",
            ""
        )

        if not resume:

            resume = item.get(
                "synthese",
                ""
            )

        if not resume:

            continue

        synthese_finale.append(
            {
                "equipement": str(
                    equipement
                ).strip(),

                "resume": str(
                    resume
                ).strip()
            }
        )

    # ========================================================
    # NETTOYAGE RECOMMANDATIONS
    # ========================================================

    recommandations_finales = []

    for item in recommandations:

        if isinstance(
            item,
            str
        ):

            if item.strip():

                recommandations_finales.append(
                    {
                        "equipement": "",
                        "action": item.strip(),
                        "priorite": "faible"
                    }
                )

            continue

        if not isinstance(
            item,
            dict
        ):

            continue

        equipement = item.get(
            "equipement",
            ""
        )

        action = item.get(
            "action",
            ""
        )

        priorite = item.get(
            "priorite",
            "faible"
        )

        if priorite not in [
            "faible",
            "moyenne",
            "élevée"
        ]:

            priorite = "faible"

        if not action:

            continue

        recommandations_finales.append(
            {
                "equipement": str(
                    equipement
                ).strip(),

                "action": str(
                    action
                ).strip(),

                "priorite": priorite
            }
        )

    # ========================================================
    # RESULTAT FINAL
    # ========================================================

    resultat_final = {
        "synthese_interventions": synthese_finale,
        "recommandations": recommandations_finales
    }

    print("\n")
    print("==========================================")
    print(">>> SYNTHESE FINALE")
    print("==========================================")

    print(
        json.dumps(
            resultat_final,
            ensure_ascii=False,
            indent=2
        )
    )

    print("==========================================")
    print("\n")

    return resultat_final
