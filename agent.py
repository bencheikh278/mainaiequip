import json
import re
import requests


# ============================================================
# CONFIGURATION VLLM
# ============================================================

BASE_URL = "http://10.109.28.102:8000"
GENERATION_ENDPOINT = "/v1/chat/completions"
MODEL = "sonatrach-IA"

MAX_CARACTERES_RAPPORT = 12000
MAX_ACTIONS_PAR_EQUIPEMENT = 3


# ============================================================
# EXCEPTIONS
# ============================================================

class SynIAError(Exception):
    pass


class RapportVide(SynIAError):
    pass


class DocumentTropLong(SynIAError):
    pass


class JSONInvalide(SynIAError):
    pass


class VLLMIndisponible(SynIAError):
    pass


# ============================================================
# PROMPT SYSTEME
# ============================================================

SYSTEM_PROMPT = """
Tu es SYNIA, un agent spécialisé dans l'analyse intelligente
des documents de maintenance industrielle.

Tu analyses des rapports concernant des équipements industriels.

REGLES ABSOLUES :

1. Tu travailles uniquement à partir des informations présentes
   dans le document.

2. Tu ne dois jamais inventer :
   - une panne
   - une anomalie
   - une cause
   - une intervention
   - une date
   - une mesure
   - un résultat
   - un technicien

3. Si une information n'est pas présente, utilise null ou [].

4. Tu dois rechercher les informations dans tout le document.

5. Plusieurs équipements peuvent être présents dans un même rapport.
   Ils doivent être analysés séparément.

6. Tu dois distinguer :
   - intervention réellement réalisée
   - intervention planifiée
   - recommandation future de SYNIA

7. Une recommandation future peut être déduite logiquement
   d'une anomalie réellement constatée.

8. Les recommandations ne doivent jamais être présentées comme
   des interventions déjà réalisées.

9. Réponds toujours en français.

10. Lorsqu'un problème réel est présent dans le document,
    propose une recommandation future pertinente lorsque cela
    est techniquement justifié.
"""


# ============================================================
# UTILITAIRE JSON
# ============================================================

def nettoyer_json(contenu):

    if not contenu:
        raise JSONInvalide("Le modèle a retourné une réponse vide.")

    contenu = contenu.strip()

    # Retirer ```json
    contenu = re.sub(
        r"^```json\s*",
        "",
        contenu,
        flags=re.IGNORECASE
    )

    # Retirer ```
    contenu = re.sub(
        r"^```\s*",
        "",
        contenu
    )

    contenu = re.sub(
        r"\s*```$",
        "",
        contenu
    )

    # Premier essai
    try:
        return json.loads(contenu)
    except json.JSONDecodeError:
        pass

    # Chercher un objet JSON
    debut_objet = contenu.find("{")
    fin_objet = contenu.rfind("}")

    if debut_objet != -1 and fin_objet != -1:
        extrait = contenu[debut_objet:fin_objet + 1]

        try:
            return json.loads(extrait)
        except json.JSONDecodeError:
            pass

    # Chercher une liste JSON
    debut_liste = contenu.find("[")
    fin_liste = contenu.rfind("]")

    if debut_liste != -1 and fin_liste != -1:
        extrait = contenu[debut_liste:fin_liste + 1]

        try:
            return json.loads(extrait)
        except json.JSONDecodeError:
            pass

    print("\n========== REPONSE JSON INVALIDE ==========")
    print(contenu[:3000])
    print("============================================\n")

    raise JSONInvalide(
        "Le modèle n'a pas retourné un JSON valide."
    )


# ============================================================
# APPEL VLLM
# ============================================================

def appeler_modele(prompt, max_tokens=2500):

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

    print("\n--------------------------------------------")
    print("APPEL VLLM")
    print("--------------------------------------------")

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=120
        )

    except requests.exceptions.Timeout:

        raise VLLMIndisponible(
            "Timeout : le serveur vLLM ne répond pas."
        )

    except requests.exceptions.ConnectionError:

        raise VLLMIndisponible(
            f"Impossible de contacter vLLM : {url}"
        )

    except requests.exceptions.RequestException as e:

        raise VLLMIndisponible(
            f"Erreur réseau vLLM : {e}"
        )

    print(f"STATUS VLLM : {response.status_code}")

    if response.status_code != 200:

        print("REPONSE VLLM :")
        print(response.text[:3000])

        raise VLLMIndisponible(
            f"Erreur HTTP vLLM : {response.status_code}"
        )

    try:

        data = response.json()

    except Exception:

        print(response.text[:3000])

        raise JSONInvalide(
            "La réponse du serveur n'est pas du JSON."
        )

    try:

        contenu = data["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError):

        print("\n========== REPONSE VLLM INATTENDUE ==========")
        print(json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ))
        print("==============================================\n")

        raise SynIAError(
            "Structure de réponse vLLM inattendue."
        )

    print("\nREPONSE MODELE :")
    print(contenu[:5000])

    return nettoyer_json(contenu)


# ============================================================
# 1. IDENTIFIER LES EQUIPEMENTS
# ============================================================

def _lister_equipements(texte):

    prompt = f"""
Analyse ce rapport de maintenance et identifie TOUS les
équipements industriels mentionnés.

IMPORTANT :

- Cherche dans tout le document.
- Plusieurs équipements peuvent être présents.
- Ne retourne pas uniquement le premier équipement.
- Ignore les pièces ou petits composants lorsqu'ils ne sont
  pas eux-mêmes considérés comme des équipements.
- Retourne uniquement les noms des équipements.

Réponds EXACTEMENT avec ce format JSON :

{{
    "equipements": [
        "Equipement 1",
        "Equipement 2"
    ]
}}

DOCUMENT :

{texte}
"""

    resultat = appeler_modele(
        prompt,
        max_tokens=1200
    )

    equipements = resultat.get("equipements", [])

    if not isinstance(equipements, list):
        equipements = []

    equipements_nettoyes = []

    for equipement in equipements:

        if isinstance(equipement, str):

            equipement = equipement.strip()

            if equipement:
                equipements_nettoyes.append(equipement)

    print("\n========== EQUIPEMENTS DETECTES ==========")

    if equipements_nettoyes:

        for equipement in equipements_nettoyes:
            print(" -", equipement)

    else:

        print("AUCUN EQUIPEMENT")

    print("===========================================\n")

    return equipements_nettoyes


# ============================================================
# 2. EXTRAIRE LES INFORMATIONS DE L'EQUIPEMENT
# ============================================================

def _extraire_equipement(texte, equipement):

    prompt = f"""
Tu dois analyser le document de maintenance ci-dessous.

EQUIPEMENT A ANALYSER :
{equipement}

DOCUMENT :
{texte}

Cherche dans TOUT le document toutes les informations
concernant cet équipement.

Tu dois rechercher obligatoirement :

1. DESCRIPTION
- type
- fonction
- rôle
- caractéristiques

2. ANOMALIES / PROBLEMES
- panne
- défaut
- anomalie
- fuite
- vibration
- bruit
- température anormale
- pression anormale
- arrêt
- dérive
- dégradation
- problème récurrent

3. CAUSES
Uniquement les causes explicitement indiquées dans le document.

4. INTERVENTIONS REALISEES
Toutes les actions réellement effectuées :
- réparation
- remplacement
- nettoyage
- réglage
- inspection
- contrôle
- maintenance corrective
- maintenance préventive

5. INTERVENTIONS PLANIFIEES
Actions prévues mais qui ne sont pas encore réalisées.

6. RESULTATS
- problème résolu
- problème toujours présent
- équipement remis en service
- résultat du contrôle
- mesures après intervention
- état final

7. INFORMATIONS TECHNIQUES
- températures
- pressions
- vibrations
- valeurs mesurées
- références
- dates
- heures
- fréquences
- autres paramètres techniques

8. TECHNICIENS
Noms des techniciens ou équipes lorsqu'ils sont présents.

IMPORTANT :

Ne te limite surtout pas au nom et à la description.

Si une anomalie est présente dans le document,
elle doit apparaître dans "anomalies".

Si une intervention a été réalisée,
elle doit apparaître dans "interventions_realisees".

Si une intervention est seulement prévue,
elle doit apparaître dans "interventions_planifiees".

Ne rien inventer.

Si une information n'existe pas, retourne [] ou null.

Réponds EXACTEMENT avec ce JSON :

{{
    "equipement": "{equipement}",
    "description": null,
    "anomalies": [
        {{
            "description": "...",
            "niveau": "faible"
        }}
    ],
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
        max_tokens=3000
    )

    print("\n========== EXTRACTION ==========")
    print(f"EQUIPEMENT : {equipement}")
    print(
        json.dumps(
            resultat,
            ensure_ascii=False,
            indent=2
        )
    )
    print("================================\n")

    return resultat


# ============================================================
# 3. ANALYSER LES FAITS
# ============================================================

def _analyser_equipement(faits):

    prompt = f"""
Voici les informations extraites d'un rapport de maintenance.

FAITS EXTRAITS :

{json.dumps(
    faits,
    ensure_ascii=False,
    indent=2
)}

À partir de ces faits, construis l'analyse finale de
l'équipement.

Tu dois conserver :

- description
- anomalies
- causes
- interventions réalisées
- interventions planifiées
- résultats
- informations techniques

Pour chaque anomalie, indique :

- description
- niveau : faible, moyen ou élevé
- statut : active, résolue, en cours ou null

IMPORTANT :

Ne crée aucune nouvelle information factuelle.

Les recommandations sont différentes des interventions.

Une recommandation est une ACTION FUTURE proposée par SYNIA.

Par exemple :

Si le document indique :
"vibration anormale détectée"

SYNIA peut recommander :
"Surveiller l'évolution des vibrations et effectuer
un contrôle mécanique."

Mais SYNIA ne doit PAS écrire :
"Les roulements ont été remplacés"

si le document ne dit pas que les roulements ont été remplacés.

Pour chaque anomalie réelle, propose une recommandation future
pertinente lorsque cela est justifié.

Réponds EXACTEMENT avec ce format JSON :

{{
    "equipement": "...",
    "description": null,
    "anomalies": [
        {{
            "description": "...",
            "niveau": "moyen",
            "statut": "active"
        }}
    ],
    "causes": [],
    "interventions_realisees": [],
    "interventions_planifiees": [],
    "resultats": [],
    "informations_techniques": [],
    "recommandations": [
        {{
            "action": "...",
            "priorite": "moyenne"
        }}
    ]
}}
"""

    resultat = appeler_modele(
        prompt,
        max_tokens=3000
    )

    print("\n========== ANALYSE EQUIPEMENT ==========")

    print(
        json.dumps(
            resultat,
            ensure_ascii=False,
            indent=2
        )
    )

    print("=========================================\n")

    return resultat


# ============================================================
# 4. ANALYSER LE RAPPORT COMPLET
# ============================================================

def analyser_rapport(texte):

    if not texte or not texte.strip():

        raise RapportVide(
            "Le rapport est vide."
        )

    print("\n")
    print("================================================")
    print("          SYNIA - ANALYSE RAPPORT")
    print("================================================")

    if len(texte) > MAX_CARACTERES_RAPPORT:

        print(
            f"[WARNING] Document trop long : {len(texte)} caractères."
        )

        texte = texte[:MAX_CARACTERES_RAPPORT]

    # --------------------------------------------------------
    # ETAPE 1
    # --------------------------------------------------------

    print("\n[1/3] Recherche des équipements...")

    equipements = _lister_equipements(texte)

    if not equipements:

        print(
            "[SYNIA] Aucun équipement détecté."
        )

        return []

    # --------------------------------------------------------
    # ETAPE 2 + 3
    # --------------------------------------------------------

    resultats = []

    for equipement in equipements:

        print(
            f"\n[2/3] Extraction : {equipement}"
        )

        faits = _extraire_equipement(
            texte,
            equipement
        )

        print(
            f"\n[3/3] Analyse : {equipement}"
        )

        analyse = _analyser_equipement(
            faits
        )

        # Sécurité
        if not analyse.get("equipement"):

            analyse["equipement"] = equipement

        resultats.append(analyse)

    # --------------------------------------------------------
    # RESULTAT
    # --------------------------------------------------------

    print("\n")
    print("================================================")
    print("       RESULTATS COMPLETS DU RAPPORT")
    print("================================================")

    print(
        json.dumps(
            resultats,
            ensure_ascii=False,
            indent=2
        )
    )

    print("================================================\n")

    return resultats


# ============================================================
# 5. SYNTHESE GLOBALE
# ============================================================

def synthese_globale(resultats):

    if not resultats:

        print(
            "[SYNTHESE] Aucun résultat à synthétiser."
        )

        return {
            "synthese_interventions": [],
            "problemes_identifies": [],
            "recommandations": []
        }

    print("\n")
    print("================================================")
    print("             SYNIA - SYNTHESE")
    print("================================================")

    prompt = f"""
Voici les analyses complètes des équipements d'un rapport
de maintenance.

ANALYSES :

{json.dumps(
    resultats,
    ensure_ascii=False,
    indent=2
)}

À partir UNIQUEMENT de ces analyses, produis une synthèse.

Tu dois fournir :

1. synthese_interventions

Résumé des interventions réellement réalisées.

2. problemes_identifies

Résumé des anomalies ou problèmes réellement constatés.

3. recommandations

Actions FUTURES proposées par SYNIA.

Les recommandations doivent être liées aux problèmes
réellement identifiés.

Exemples :

- Vérifier l'état de l'équipement.
- Contrôler les vibrations.
- Surveiller l'évolution de la température.
- Effectuer une inspection.
- Planifier une maintenance.
- Prévoir un remplacement si nécessaire.

IMPORTANT :

- Ne jamais inventer une intervention réalisée.
- Ne jamais inventer une cause.
- Ne jamais inventer une anomalie.
- Ne jamais présenter une recommandation comme une intervention.
- Une recommandation doit être une action future.
- Associer chaque recommandation à l'équipement concerné.
- S'il existe des problèmes documentés, ne laisse pas
  systématiquement la liste des recommandations vide.

Réponds EXACTEMENT avec :

{{
    "synthese_interventions": [],
    "problemes_identifies": [],
    "recommandations": [
        {{
            "equipement": "...",
            "action": "...",
            "priorite": "moyenne"
        }}
    ]
}}
"""

    synthese = appeler_modele(
        prompt,
        max_tokens=2500
    )

    print("\n========== SYNTHESE FINALE ==========")

    print(
        json.dumps(
            synthese,
            ensure_ascii=False,
            indent=2
        )
    )

    print("=====================================\n")

    return synthese