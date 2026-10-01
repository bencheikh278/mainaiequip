import json
import re
import requests


# ============================================================
# SERVEUR vLLM SONATRACH
# ============================================================

BASE_URL = "http://10.109.28.102:8000"
GENERATION_ENDPOINT = "/v1/chat/completions"
MODEL = "sonatrach-IA"


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


class ModeleIndisponible(SynIAError):
    pass


# ============================================================
# PARAMETRES
# ============================================================

IGNORER_EQUIPEMENTS_SANS_PROBLEME = True
MAX_ACTIONS_PAR_EQUIPEMENT = 3
MAX_CARACTERES_RAPPORT = 12000
MAX_HISTORIQUE_PAR_EQUIPEMENT = 5

PRIORITES = ["élevée", "moyenne", "faible"]
NIVEAUX = ["faible", "moyen", "élevé"]


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


SCHEMA_FAITS_EQUIPEMENT = {
    "type": "json_schema",
    "json_schema": {
        "name": "faits_equipement",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": ["string", "null"]
                },
                "date": {
                    "type": ["string", "null"]
                },
                "equipement": {
                    "type": "string"
                },
                "type": {
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
                            "cause": {
                                "type": ["string", "null"]
                            }
                        },
                        "required": [
                            "description",
                            "niveau",
                            "cause"
                        ],
                        "additionalProperties": False
                    }
                },
                "interventions": {
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
                "reference",
                "date",
                "equipement",
                "type",
                "anomalies",
                "interventions",
                "resultats",
                "techniciens"
            ],
            "additionalProperties": False
        }
    }
}


SCHEMA_EQUIPEMENT = {
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
                "statut": {
                    "type": "string"
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
                "interventions": {
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
                },
                "recommandations": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "equipement",
                "statut",
                "anomalies",
                "causes",
                "interventions",
                "resultats",
                "techniciens",
                "recommandations"
            ],
            "additionalProperties": False
        }
    }
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Tu es SYNIA, un agent intelligent spécialisé dans l'analyse
des documents de maintenance des équipements industriels.

Tu dois répondre uniquement en français.

REGLES IMPORTANTES :

1. Utilise uniquement les informations présentes dans le document.
2. N'invente jamais une date.
3. N'invente jamais une cause.
4. N'invente jamais une intervention.
5. N'invente jamais un résultat.
6. Si une information n'est pas présente, utilise null ou une liste vide.
7. Distingue clairement :
   - les interventions réellement réalisées ;
   - les interventions planifiées ;
   - les recommandations proposées par SYNIA.
8. Une anomalie doit être basée sur une information réellement présente
   dans le document.
9. Si plusieurs équipements sont présents dans le document,
   analyse-les séparément.
10. Les recommandations doivent être clairement présentées comme
    des recommandations de SYNIA et non comme des interventions réalisées.
"""


# ============================================================
# OUTILS TEXTE
# ============================================================

def _liste(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _cle(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def _texte_brut(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    return json.dumps(
        value,
        ensure_ascii=False
    )


# ============================================================
# NETTOYAGE JSON
# ============================================================

def nettoyer_json(texte):
    if not texte:
        raise JSONInvalide("Réponse vide du modèle.")

    texte = texte.strip()

    if texte.startswith("```"):
        texte = re.sub(
            r"^```(?:json)?\s*",
            "",
            texte,
            flags=re.IGNORECASE
        )

        texte = re.sub(
            r"\s*```$",
            "",
            texte
        )

    try:
        return json.loads(texte)

    except json.JSONDecodeError:

        debut_objet = texte.find("{")
        fin_objet = texte.rfind("}")

        if debut_objet != -1 and fin_objet != -1:
            try:
                return json.loads(
                    texte[debut_objet:fin_objet + 1]
                )
            except json.JSONDecodeError:
                pass

        debut_liste = texte.find("[")
        fin_liste = texte.rfind("]")

        if debut_liste != -1 and fin_liste != -1:
            try:
                return json.loads(
                    texte[debut_liste:fin_liste + 1]
                )
            except json.JSONDecodeError:
                pass

    raise JSONInvalide(
        "Le modèle a renvoyé un JSON invalide."
    )


# ============================================================
# APPEL DU SERVEUR vLLM
# ============================================================

def appeler_modele(prompt, schema, max_tokens=2000):

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

        response.raise_for_status()

        data = response.json()

        if "choices" not in data:
            raise JSONInvalide(
                "La réponse du serveur ne contient pas 'choices'."
            )

        if not data["choices"]:
            raise JSONInvalide(
                "Le serveur n'a retourné aucun résultat."
            )

        message = data["choices"][0].get(
            "message",
            {}
        )

        contenu = message.get("content")

        if not contenu:
            raise JSONInvalide(
                "Le modèle n'a retourné aucun contenu."
            )

        return contenu

    except requests.exceptions.ConnectionError as e:

        raise VLLMIndisponible(
            f"Impossible de contacter le serveur vLLM Sonatrach : {url}"
        ) from e

    except requests.exceptions.Timeout as e:

        raise VLLMIndisponible(
            "Le serveur vLLM Sonatrach n'a pas répondu dans le délai prévu."
        ) from e

    except requests.exceptions.HTTPError as e:

        raise VLLMIndisponible(
            f"Erreur HTTP du serveur vLLM : "
            f"{response.status_code} - {response.text}"
        ) from e

    except requests.exceptions.RequestException as e:

        raise VLLMIndisponible(
            f"Erreur de communication avec le serveur vLLM : {e}"
        ) from e


# ============================================================
# APPEL + PARSING
# ============================================================

def appeler_et_parser(prompt, schema, max_tokens=2000):

    contenu = appeler_modele(
        prompt,
        schema,
        max_tokens
    )

    return nettoyer_json(contenu)


# ============================================================
# NORMALISATION
# ============================================================

def normaliser_niveau(niveau):

    if niveau is None:
        return None

    niveau = str(niveau).strip().lower()

    correspondances = {
        "low": "faible",
        "medium": "moyen",
        "high": "élevé",
        "eleve": "élevé",
        "élevée": "élevé"
    }

    return correspondances.get(
        niveau,
        niveau if niveau in NIVEAUX else None
    )


def normaliser_statut(statut):

    if not statut:
        return "inconnu"

    statut = str(statut).strip().lower()

    if "résolu" in statut or "resolu" in statut:
        return "résolu"

    if "actif" in statut:
        return "actif"

    if "plan" in statut:
        return "planifié"

    return statut


# ============================================================
# LISTER LES EQUIPEMENTS
# ============================================================

def _lister_equipements(texte):

    prompt = f"""
Analyse le document de maintenance suivant.

Identifie uniquement les équipements réellement mentionnés
dans le document.

Si plusieurs équipements sont présents, retourne-les tous.

DOCUMENT :

{texte}
"""

    resultat = appeler_et_parser(
        prompt,
        SCHEMA_LISTE,
        max_tokens=1000
    )

    equipements = resultat.get(
        "equipements",
        []
    )

    return [
        str(e).strip()
        for e in equipements
        if str(e).strip()
    ]


# ============================================================
# EXTRAIRE UN EQUIPEMENT
# ============================================================

def _extraire_equipement(
    texte,
    equipement
):

    prompt = f"""
Analyse uniquement les informations concernant
l'équipement suivant :

ÉQUIPEMENT :
{equipement}

DOCUMENT :
{texte}

Extrais uniquement les faits réellement présents
dans le document.
"""

    return appeler_et_parser(
        prompt,
        SCHEMA_FAITS_EQUIPEMENT,
        max_tokens=1800
    )


# ============================================================
# ANALYSER UN RAPPORT
# ============================================================

def analyser_rapport(texte):

    if not texte or not texte.strip():
        raise RapportVide(
            "Le rapport est vide."
        )

    if len(texte) > MAX_CARACTERES_RAPPORT:
        texte = texte[:MAX_CARACTERES_RAPPORT]

    equipements = _lister_equipements(texte)

    resultats = []

    for equipement in equipements:

        faits = _extraire_equipement(
            texte,
            equipement
        )

        prompt = f"""
Analyse les informations suivantes concernant
l'équipement "{equipement}".

Informations extraites du document :

{json.dumps(
    faits,
    ensure_ascii=False,
    indent=2
)}

IMPORTANT :

- Ne crée aucune information absente.
- Les anomalies doivent correspondre aux faits du document.
- Les interventions sont uniquement celles réellement indiquées.
- Les recommandations doivent être formulées comme des recommandations
  de SYNIA.
"""

        analyse = appeler_et_parser(
            prompt,
            SCHEMA_EQUIPEMENT,
            max_tokens=2000
        )

        analyse["equipement"] = equipement

        if "anomalies" in analyse:
            for anomalie in analyse["anomalies"]:
                anomalie["niveau"] = normaliser_niveau(
                    anomalie.get("niveau")
                )

        analyse["statut"] = normaliser_statut(
            analyse.get("statut")
        )

        resultats.append(analyse)

    return resultats


# ============================================================
# GROUPEMENT DES EQUIPEMENTS
# ============================================================

def grouper_par_equipement(resultats):

    groupes = {}

    for resultat in resultats:

        nom = resultat.get(
            "equipement",
            "Inconnu"
        )

        cle = _cle(nom)

        if cle not in groupes:
            groupes[cle] = []

        groupes[cle].append(resultat)

    return groupes


# ============================================================
# DETECTION DES ANOMALIES RECURRENTES
# ============================================================

def detecter_anomalies_recurrentes(
    historiques
):

    recurrentes = []

    groupes = grouper_par_equipement(
        historiques
    )

    for cle, rapports in groupes.items():

        if len(rapports) < 2:
            continue

        anomalies = []

        for rapport in rapports:

            for anomalie in _liste(
                rapport.get("anomalies")
            ):

                description = anomalie.get(
                    "description"
                )

                if description:
                    anomalies.append(
                        description
                    )

        if anomalies:

            recurrentes.append({
                "equipement": rapports[0].get(
                    "equipement"
                ),
                "nombre_rapports": len(rapports),
                "anomalies": anomalies
            })

    return recurrentes


# ============================================================
# PROMPT EQUIPEMENT
# ============================================================

def _prompt_equipement(
    equipement,
    rapports
):

    return f"""
Analyse l'historique de maintenance suivant
pour l'équipement :

{equipement}

HISTORIQUE :

{json.dumps(
    rapports,
    ensure_ascii=False,
    indent=2
)}

Identifie :

1. Les anomalies récurrentes.
2. Les évolutions ou répétitions observables.
3. Les interventions déjà réalisées.
4. Les recommandations utiles.

Ne jamais inventer de cause ou d'intervention.
Les recommandations doivent être clairement identifiées
comme recommandations de SYNIA.
"""


# ============================================================
# RESULTAT FINAL
# ============================================================

def generer_resultat_final(
    equipements
):

    resultat_final = []

    for equipement in equipements:

        nom = equipement.get(
            "equipement",
            "Inconnu"
        )

        anomalies = _liste(
            equipement.get("anomalies")
        )

        interventions = _liste(
            equipement.get("interventions")
        )

        recommandations = _liste(
            equipement.get("recommandations")
        )

        resultat_final.append({
            "equipement": nom,
            "statut": equipement.get(
                "statut",
                "inconnu"
            ),
            "anomalies": anomalies,
            "interventions": interventions,
            "recommandations": recommandations
        })

    return resultat_final


# ============================================================
# NETTOYAGE RESULTAT FINAL
# ============================================================

def nettoyer_resultat_final(resultats):

    nettoyes = []

    for resultat in resultats:

        anomalies = []

        for anomalie in _liste(
            resultat.get("anomalies")
        ):

            if isinstance(anomalie, dict):

                description = anomalie.get(
                    "description"
                )

                if description:

                    anomalies.append({
                        "description": description,
                        "niveau": normaliser_niveau(
                            anomalie.get("niveau")
                        )
                    })

        nettoyes.append({
            "equipement": resultat.get(
                "equipement"
            ),
            "statut": normaliser_statut(
                resultat.get("statut")
            ),
            "anomalies": anomalies,
            "interventions": _liste(
                resultat.get("interventions")
            )[:MAX_ACTIONS_PAR_EQUIPEMENT],
            "recommandations": _liste(
                resultat.get("recommandations")
            )[:MAX_ACTIONS_PAR_EQUIPEMENT]
        })

    return nettoyes


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
À partir des analyses de maintenance suivantes :

{json.dumps(
    resultats,
    ensure_ascii=False,
    indent=2
)}

Génère une synthèse globale.

La synthèse doit contenir :

- les principales interventions réellement réalisées ;
- les principales anomalies détectées ;
- les recommandations de SYNIA.

IMPORTANT :

Ne jamais présenter une recommandation comme une intervention
déjà réalisée.

Ne jamais inventer une information absente des analyses.
"""

    schema = {
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
                            "type": "string"
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

    return appeler_et_parser(
        prompt,
        schema,
        max_tokens=1500
    )