import json
import re
import requests


# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "http://10.109.28.102:8000"
GENERATION_ENDPOINT = "/v1/chat/completions"
MODEL = "sonatrach-IA"

MAX_CARACTERES_RAPPORT = 12000
MAX_ACTIONS_PAR_EQUIPEMENT = 3

PRIORITES = ["élevée", "moyenne", "faible"]
NIVEAUX = ["faible", "moyen", "élevé"]


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
Tu es SYNIA, un agent spécialisé dans l'analyse de documents
de maintenance industrielle.

Tu travailles uniquement à partir des informations présentes
dans le document fourni.

REGLES IMPORTANTES :

1. Ne jamais inventer une information.
2. Ne jamais inventer une date, une cause, une intervention,
   un résultat ou une mesure.
3. Si une information n'est pas présente, utiliser null ou [].
4. Identifier séparément chaque équipement.
5. Identifier les anomalies, pannes, défauts, dérives ou problèmes
   réellement mentionnés dans le document.
6. Identifier les interventions réellement réalisées.
7. Identifier les interventions prévues ou planifiées.
8. Identifier les résultats des interventions lorsqu'ils sont
   présents.
9. Identifier les causes uniquement lorsqu'elles sont indiquées
   ou clairement établies dans le document.
10. Les recommandations de SYNIA sont des ACTIONS FUTURES.
    Elles peuvent être déduites logiquement d'un problème
    réellement constaté dans le document.
11. Une recommandation ne doit jamais être présentée comme une
    intervention déjà réalisée.
12. Toujours répondre en français.
13. Pour un équipement ayant un problème documenté, essayer de
    proposer au moins une recommandation future pertinente.
14. Ne pas créer de problème lorsqu'il n'y en a pas.
"""


# ============================================================
# SCHEMAS JSON
# ============================================================

SCHEMA_LISTE = {
    "type": "json_schema",
    "json_schema": {
        "name": "liste_equipements",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "equipements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["equipements"],
            "additionalProperties": False
        }
    }
}


SCHEMA_FAITS = {
    "type": "json_schema",
    "json_schema": {
        "name": "faits_equipement",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "equipement": {
                    "type": "string"
                },
                "description": {
                    "type": ["string", "null"]
                },
                "anomalies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string"
                            },
                            "niveau": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": [
                            "description",
                            "niveau"
                        ],
                        "additionalProperties": False
                    }
                },
                "causes": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "interventions_realisees": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "interventions_planifiees": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "resultats": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "techniciens": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "equipement",
                "description",
                "anomalies",
                "causes",
                "interventions_realisees",
                "interventions_planifiees",
                "resultats",
                "techniciens"
            ],
            "additionalProperties": False
        }
    }
}


SCHEMA_ANALYSE = {
    "type": "json_schema",
    "json_schema": {
        "name": "analyse_equipement",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "equipement": {
                    "type": "string"
                },
                "description": {
                    "type": ["string", "null"]
                },
                "anomalies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string"
                            },
                            "niveau": {
                                "type": ["string", "null"]
                            },
                            "statut": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": [
                            "description",
                            "niveau",
                            "statut"
                        ],
                        "additionalProperties": False
                    }
                },
                "causes": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "interventions_realisees": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "interventions_planifiees": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "resultats": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "recommandations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string"
                            },
                            "priorite": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "action",
                            "priorite"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "equipement",
                "description",
                "anomalies",
                "causes",
                "interventions_realisees",
                "interventions_planifiees",
                "resultats",
                "recommandations"
            ],
            "additionalProperties": False
        }
    }
}


SCHEMA_SYNTHESE = {
    "type": "json_schema",
    "json_schema": {
        "name": "synthese_globale",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "synthese_interventions": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "recommandations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "equipement": {
                                "type": "string"
                            },
                            "action": {
                                "type": "string"
                            },
                            "priorite": {
                                "type": "string"
                            }
                        },
                        "required": [
                            "equipement",
                            "action",
                            "priorite"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "synthese_interventions",
                "recommandations"
            ],
            "additionalProperties": False
        }
    }
}


# ============================================================
# NETTOYAGE JSON
# ============================================================

def nettoyer_json(contenu):

    if not contenu:
        raise JSONInvalide("Réponse vide du modèle.")

    contenu = contenu.strip()

    # Enlever ```json ... ```
    contenu = re.sub(
        r"^```json\s*",
        "",
        contenu,
        flags=re.IGNORECASE
    )

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

    try:
        return json.loads(contenu)
    except json.JSONDecodeError:

        # Chercher un objet JSON dans la réponse
        debut = contenu.find("{")
        fin = contenu.rfind("}")

        if debut != -1 and fin != -1 and fin > debut:

            extrait = contenu[debut:fin + 1]

            try:
                return json.loads(extrait)
            except json.JSONDecodeError:
                pass

        raise JSONInvalide(
            f"JSON invalide reçu du modèle : {contenu[:500]}"
        )


# ============================================================
# APPEL VLLM
# ============================================================

def appeler_modele(prompt, schema, max_tokens=2500):

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
        "max_tokens": max_tokens,
        "response_format": schema
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=120
        )

        print(f"[vLLM] HTTP {response.status_code}")

        if response.status_code != 200:
            print("[vLLM] Réponse :")
            print(response.text[:2000])

            raise VLLMIndisponible(
                f"Erreur vLLM HTTP {response.status_code}"
            )

        data = response.json()

        contenu = (
            data["choices"][0]["message"]["content"]
        )

        print("[vLLM] Réponse reçue.")

        return nettoyer_json(contenu)

    except requests.exceptions.Timeout:
        raise VLLMIndisponible(
            "Timeout lors de l'appel au serveur vLLM."
        )

    except requests.exceptions.ConnectionError:
        raise VLLMIndisponible(
            f"Impossible de contacter vLLM : {url}"
        )

    except requests.exceptions.RequestException as e:
        raise VLLMIndisponible(
            f"Erreur réseau vLLM : {e}"
        )


# ============================================================
# ETAPE 1 — IDENTIFIER LES EQUIPEMENTS
# ============================================================

def _lister_equipements(texte):

    prompt = f"""
Voici un document de maintenance industrielle.

Identifie TOUS les équipements réellement mentionnés
dans le document.

Ne donne pas les pièces ou composants comme équipements
indépendants sauf s'ils sont explicitement traités comme
un équipement.

DOCUMENT :

{texte}
"""

    resultat = appeler_modele(
        prompt,
        SCHEMA_LISTE,
        max_tokens=1000
    )

    equipements = resultat.get("equipements", [])

    equipements = [
        e.strip()
        for e in equipements
        if isinstance(e, str) and e.strip()
    ]

    print("\n========== EQUIPEMENTS ==========")

    for e in equipements:
        print("-", e)

    print("=================================\n")

    return equipements


# ============================================================
# ETAPE 2 — EXTRAIRE LES FAITS
# ============================================================

def _extraire_equipement(texte, equipement):

    prompt = f"""
Analyse UNIQUEMENT l'équipement suivant :

ÉQUIPEMENT :
{equipement}

À partir du document ci-dessous, extrais toutes les informations
qui concernent cet équipement.

Il faut rechercher particulièrement :

- description
- anomalies
- pannes
- défauts
- niveaux de gravité
- causes mentionnées
- interventions réalisées
- interventions planifiées
- résultats
- techniciens

IMPORTANT :

Ne te limite PAS au nom et à la description.

Si une anomalie, une intervention ou un résultat concernant
l'équipement est présent dans le document, il faut le récupérer.

Ne rien inventer.

DOCUMENT :

{texte}
"""

    resultat = appeler_modele(
        prompt,
        SCHEMA_FAITS,
        max_tokens=2500
    )

    print("\n========== FAITS EXTRAITS ==========")
    print(f"Équipement : {equipement}")
    print(json.dumps(
        resultat,
        ensure_ascii=False,
        indent=2
    ))
    print("====================================\n")

    return resultat


# ============================================================
# ETAPE 3 — ANALYSE DE L'EQUIPEMENT
# ============================================================

def _analyser_equipement(faits):

    prompt = f"""
Tu dois construire l'analyse finale d'un équipement industriel.

Voici les faits extraits directement du document :

{json.dumps(
    faits,
    ensure_ascii=False,
    indent=2
)}

Construis une analyse structurée.

IMPORTANT :

- Conserve les anomalies réellement présentes.
- Conserve les interventions réellement réalisées.
- Conserve les interventions planifiées.
- Conserve les résultats réellement présents.
- Ne transforme jamais une recommandation en intervention réalisée.
- Ne crée aucune cause absente du document.

Pour chaque anomalie :

- donne son niveau si le document permet de le déterminer ;
- sinon utilise null ;
- indique le statut si possible :
  "active", "résolue", "en cours" ou null.

RECOMMANDATIONS :

Les recommandations sont des actions FUTURES proposées par SYNIA.

Elles peuvent être déduites logiquement des anomalies
réellement constatées.

Exemples de formulation :

- Vérifier ...
- Contrôler ...
- Surveiller ...
- Inspecter ...
- Prévoir ...
- Effectuer un contrôle ...
- Remplacer si nécessaire ...

Ne jamais affirmer qu'une action future a déjà été réalisée.

Si un problème réel est identifié, proposer au moins
une recommandation pertinente lorsque cela est justifié.
"""

    resultat = appeler_modele(
        prompt,
        SCHEMA_ANALYSE,
        max_tokens=2500
    )

    print("\n========== ANALYSE EQUIPEMENT ==========")
    print(json.dumps(
        resultat,
        ensure_ascii=False,
        indent=2
    ))
    print("=========================================\n")

    return resultat


# ============================================================
# ANALYSE COMPLETE DU RAPPORT
# ============================================================

def analyser_rapport(texte):

    if not texte or not texte.strip():
        raise RapportVide(
            "Le rapport est vide."
        )

    if len(texte) > MAX_CARACTERES_RAPPORT:

        print(
            f"[SYNIA] Document trop long : "
            f"{len(texte)} caractères."
        )

        texte = texte[:MAX_CARACTERES_RAPPORT]

    print("\n")
    print("==============================================")
    print("        SYNIA — ANALYSE DU RAPPORT")
    print("==============================================")

    # 1. Identifier les équipements
    equipements = _lister_equipements(texte)

    if not equipements:

        print("[SYNIA] Aucun équipement détecté.")

        return []

    resultats = []

    # 2. Traiter chaque équipement
    for equipement in equipements:

        print(
            f"\n[SYNIA] Analyse de : {equipement}"
        )

        try:

            # Extraction des faits
            faits = _extraire_equipement(
                texte,
                equipement
            )

            # Analyse complète
            analyse = _analyser_equipement(
                faits
            )

            # Sécurité : vérifier que le modèle a bien renvoyé
            # l'équipement
            if not analyse.get("equipement"):
                analyse["equipement"] = equipement

            resultats.append(analyse)

        except Exception as e:

            print(
                f"[SYNIA] ERREUR pour {equipement} : {e}"
            )

            raise

    print("\n==============================================")
    print("        RESULTAT FINAL DE L'ANALYSE")
    print("==============================================")

    print(
        json.dumps(
            resultats,
            ensure_ascii=False,
            indent=2
        )
    )

    print("==============================================\n")

    return resultats


# ============================================================
# SYNTHESE GLOBALE
# ============================================================

def synthese_globale(resultats):

    if not resultats:

        return {
            "synthese_interventions": [],
            "recommandations": []
        }

    prompt = f"""
Tu es SYNIA.

Voici les analyses complètes des équipements du rapport :

{json.dumps(
    resultats,
    ensure_ascii=False,
    indent=2
)}

À partir UNIQUEMENT de ces analyses :

1. Fais une synthèse claire des interventions réalisées.
2. Identifie les problèmes/anomalies importants.
3. Génère des recommandations FUTURES pertinentes.

IMPORTANT :

Une recommandation est une action à effectuer dans le futur.

Elle peut être déduite logiquement d'une anomalie réellement
présente dans les analyses.

Exemples :

- contrôler un équipement présentant une anomalie ;
- surveiller une dérive ;
- effectuer une inspection ;
- prévoir une maintenance ;
- vérifier un composant lié à un problème documenté.

Ne jamais inventer une panne, une cause ou une intervention.

Ne jamais dire qu'une recommandation a déjà été réalisée.

Les recommandations doivent être associées à l'équipement
concerné.

S'il existe des anomalies documentées, les recommandations
ne doivent pas rester systématiquement vides.
"""

    print("\n========== APPEL SYNTHESE ==========")

    synthese = appeler_modele(
        prompt,
        SCHEMA_SYNTHESE,
        max_tokens=2000
    )

    print(
        json.dumps(
            synthese,
            ensure_ascii=False,
            indent=2
        )
    )

    print("====================================\n")

    return synthese