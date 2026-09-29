import json
import re

from openai import OpenAI


# ============================================================
# CLIENT LOCAL — LM STUDIO
# ============================================================

client_local = OpenAI(
    api_key="lm-studio",
    base_url="http://localhost:1234/v1",
)

MODEL = "mistralai/ministral-3-3b"


# ============================================================
# CONFIGURATION
# ============================================================

# True :
# un équipement sans anomalie actuelle et sans problème historique
# n'aura pas de recommandation finale.
IGNORER_EQUIPEMENTS_SANS_PROBLEME = True

MAX_ACTIONS_PAR_EQUIPEMENT = 4

# Nombre maximum de caractères du rapport envoyé au modèle.
MAX_CARACTERES_RAPPORT = 12000

# Nombre maximum de rapports historiques examinés pour un équipement.
MAX_HISTORIQUE_PAR_EQUIPEMENT = 5

PRIORITES = [
    "élevée",
    "moyenne",
    "faible",
]

NIVEAUX = [
    "faible",
    "moyen",
    "élevé",
]


# ============================================================
# SCHEMA 1 — LISTE DES EQUIPEMENTS
# ============================================================

SCHEMA_LISTE = {
    "type": "json_schema",
    "json_schema": {
        "name": "liste_equipements",
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

                "equipements": {
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

                "recommandations_rapport": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
            },

            "required": [
                "reference",
                "date",
                "equipements",
                "techniciens",
                "recommandations_rapport",
            ],

            "additionalProperties": False,
        },
    },
}


# ============================================================
# SCHEMA 2 — FAITS POUR UN EQUIPMENT
# ============================================================

SCHEMA_FAITS_EQUIPEMENT = {
    "type": "json_schema",
    "json_schema": {
        "name": "faits_equipement",
        "strict": True,
        "schema": {

            "type": "object",

            "properties": {

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
                                "type": ["string", "null"],
                                "enum": NIVEAUX + [None]
                            },
                        },

                        "required": [
                            "description",
                            "niveau",
                        ],

                        "additionalProperties": False,
                    },
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

                "recommandations_technicien": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
            },

            "required": [
                "type",
                "anomalies",
                "causes",
                "interventions",
                "resultats",
                "recommandations_technicien",
            ],

            "additionalProperties": False,
        },
    },
}


# ============================================================
# SCHEMA 3 — SYNTHESE + RECOMMANDATIONS IA
# ============================================================

SCHEMA_EQUIPEMENT = {
    "type": "json_schema",
    "json_schema": {
        "name": "synthese_equipement",
        "strict": True,
        "schema": {

            "type": "object",

            "properties": {

                "resume": {
                    "type": "string"
                },

                "actions": {
                    "type": "array",
                    "items": {

                        "type": "object",

                        "properties": {

                            "priorite": {
                                "type": "string",
                                "enum": PRIORITES
                            },

                            "action": {
                                "type": "string"
                            },

                            "justification": {
                                "type": "string"
                            },
                        },

                        "required": [
                            "priorite",
                            "action",
                            "justification",
                        ],

                        "additionalProperties": False,
                    },
                },
            },

            "required": [
                "resume",
                "actions",
            ],

            "additionalProperties": False,
        },
    },
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Tu es SYNIA, un agent IA spécialisé dans l'analyse de documents
de maintenance industrielle.

RÈGLE ABSOLUE :
La fidélité au document est prioritaire.

Tu dois toujours :

- ne jamais inventer une information ;
- ne jamais inventer un chiffre ;
- ne jamais inventer un seuil ;
- ne jamais inventer une date ;
- ne jamais inventer une cause ;
- ne jamais inventer une intervention ;
- distinguer une intervention réellement réalisée
  d'une action seulement prévue ;
- distinguer une recommandation du technicien
  d'une recommandation produite par SYNIA ;
- considérer un problème persistant comme une information valide ;
- répondre uniquement en français.
"""


# ============================================================
# PETITS OUTILS
# ============================================================

def _liste(valeur):
    """
    Retourne une liste si la valeur est une liste,
    sinon une liste vide.
    """
    return valeur if isinstance(valeur, list) else []


def _cle(nom):
    """
    Normalise un nom pour les comparaisons.
    Exemple :
    ' C-102 ' -> 'c-102'
    """
    return " ".join(
        str(nom or "").lower().split()
    )


def _texte_brut(valeur):
    """
    Nettoie le texte produit par le modèle.
    """
    texte = str(valeur or "")

    texte = texte.replace("**", "")

    texte = re.sub(
        r"^```[a-zA-Z]*\s*",
        "",
        texte
    )

    texte = texte.replace("```", "")

    return texte.strip()


# ============================================================
# NETTOYAGE JSON
# ============================================================

def nettoyer_json(texte):
    """
    Récupère un objet JSON même si le modèle ajoute
    accidentellement des ```json ... ```.
    """

    if not texte:
        return ""

    texte = str(texte).strip()

    # Cas où le modèle écrit :
    # ```json
    # {...}
    # ```
    if "```" in texte:

        morceaux = texte.split("```")

        for morceau in morceaux:

            morceau = morceau.strip()

            if morceau.lower().startswith("json"):
                morceau = morceau[4:].strip()

            if (
                morceau.startswith("{")
                and morceau.endswith("}")
            ):
                return morceau

    # Recherche d'un objet JSON au milieu du texte
    debut = texte.find("{")
    fin = texte.rfind("}")

    if debut != -1 and fin > debut:
        return texte[debut:fin + 1]

    return texte


def parser_json(texte):
    """
    Parse la réponse du modèle.
    """

    propre = nettoyer_json(texte)

    try:

        resultat = json.loads(propre)

    except json.JSONDecodeError as erreur:

        extrait = propre[:500].replace(
            "\n",
            " "
        )

        raise ValueError(
            f"JSON invalide : {erreur}. "
            f"Début de réponse : {extrait}"
        ) from erreur

    if not isinstance(resultat, dict):
        raise ValueError(
            "La réponse JSON n'est pas un objet."
        )

    return resultat


# ============================================================
# APPEL LM STUDIO
# ============================================================

def appeler_modele(
    prompt,
    schema,
    max_tokens=2000
):
    """
    Appel direct à LM Studio.

    Première tentative :
    JSON Schema structuré.

    Si le serveur/modèle refuse :
    seconde tentative avec json_object.
    """

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    try:

        response = client_local.chat.completions.create(
            model=MODEL,
            messages=messages,
            response_format=schema,
            temperature=0.1,
            max_tokens=max_tokens,
        )

    except Exception as erreur:

        print(
            "⚠️ Sortie structurée échouée."
        )

        print(
            f"Nouvelle tentative JSON : {erreur}"
        )

        prompt_json = (
            prompt
            + "\n\n"
            + "IMPORTANT : réponds uniquement avec "
              "un objet JSON valide, sans markdown."
        )

        response = client_local.chat.completions.create(

            model=MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt_json,
                },
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0.1,

            max_tokens=max_tokens,
        )

    if not response.choices:
        raise RuntimeError(
            "LM Studio n'a retourné aucun choix."
        )

    choix = response.choices[0]

    contenu = choix.message.content

    if not contenu:

        raison = getattr(
            choix,
            "finish_reason",
            "inconnue"
        )

        raise RuntimeError(
            "Réponse vide du modèle "
            f"(finish_reason={raison})."
        )

    return contenu


def appeler_et_parser(
    prompt,
    schema,
    max_tokens=2000
):
    """
    Appelle le modèle puis convertit
    sa réponse en dictionnaire Python.
    """

    texte = appeler_modele(
        prompt,
        schema,
        max_tokens=max_tokens,
    )

    return parser_json(texte)


# ============================================================
# NORMALISATION
# ============================================================

def normaliser_resultat(resultat):

    if not isinstance(resultat, dict):
        resultat = {}

    resultat.setdefault(
        "reference",
        None
    )

    resultat.setdefault(
        "date",
        None
    )

    for cle in (
        "equipements",
        "techniciens",
        "recommandations_rapport",
    ):
        resultat[cle] = _liste(
            resultat.get(cle)
        )

    equipements_valides = []

    for equipement in resultat["equipements"]:

        if not isinstance(
            equipement,
            dict
        ):
            continue

        equipement.setdefault(
            "nom",
            None
        )

        equipement.setdefault(
            "type",
            None
        )

        for cle in (
            "anomalies",
            "causes",
            "interventions",
            "resultats",
            "recommandations_technicien",
        ):

            equipement[cle] = _liste(
                equipement.get(cle)
            )

        # ----------------------------
        # ANOMALIES
        # ----------------------------

        anomalies_valides = []

        for anomalie in equipement["anomalies"]:

            if not isinstance(
                anomalie,
                dict
            ):
                continue

            description = _texte_brut(
                anomalie.get("description")
            )

            if not description:
                continue

            niveau = anomalie.get(
                "niveau"
            )

            if niveau not in NIVEAUX:
                niveau = None

            anomalies_valides.append(
                {
                    "description": description,
                    "niveau": niveau,
                }
            )

        equipement["anomalies"] = (
            anomalies_valides
        )

        # ----------------------------
        # AUTRES LISTES
        # ----------------------------

        for cle in (
            "causes",
            "interventions",
            "resultats",
            "recommandations_technicien",
        ):

            valeurs = []

            vus = set()

            for valeur in equipement[cle]:

                texte = _texte_brut(
                    valeur
                )

                if (
                    texte
                    and texte.lower() not in vus
                ):

                    vus.add(
                        texte.lower()
                    )

                    valeurs.append(
                        texte
                    )

            equipement[cle] = valeurs

        equipements_valides.append(
            equipement
        )

    resultat["equipements"] = (
        equipements_valides
    )

    return resultat


# ============================================================
# 1. TROUVER TOUS LES EQUIPEMENTS
# ============================================================

def _lister_equipements(texte):

    prompt = f"""
Lis TOUT le rapport de maintenance ci-dessous.

Retourne :

1. reference
La référence du rapport, sinon null.

2. date
La date du rapport, sinon null.

3. equipements
TOUS les équipements mentionnés dans le rapport,
avec leur code ou nom exact, sans doublon.

4. techniciens
Les noms des techniciens cités.

5. recommandations_rapport
Les recommandations explicitement écrites dans le rapport.

RÈGLES :

- Cherche dans tout le texte.
- Ne prends pas seulement le premier équipement.
- Une pompe, vanne, moteur, compresseur,
  échangeur, turbine, transformateur,
  réservoir, etc. peut être un équipement.
- Ne crée aucun équipement qui n'existe pas dans le document.
- N'invente rien.

RAPPORT :

{texte}
"""

    return appeler_et_parser(
        prompt,
        SCHEMA_LISTE,
        max_tokens=1800,
    )


# ============================================================
# 2. EXTRAIRE LES FAITS D'UN SEUL EQUIPEMENT
# ============================================================

def _extraire_equipement(
    texte,
    nom
):

    prompt = f"""
Lis le rapport de maintenance ci-dessous.

Analyse UNIQUEMENT l'équipement :

{nom}

Ignore complètement les autres équipements.

============================================================
RÈGLES STRICTES
============================================================

TYPE
Donne le type de l'équipement uniquement
s'il est clairement indiqué.
Sinon : null.

============================================================
ANOMALIES
============================================================

Mets uniquement les problèmes réellement
constatés pour {nom}.

Exemples :

"Aucune anomalie"
"RAS"
"aucun défaut"

=> anomalies = []

Ne transforme jamais une recommandation
future en anomalie.

niveau doit être :

- faible
- moyen
- élevé
- null

Ne déduis jamais la gravité.

============================================================
CAUSES
============================================================

Uniquement les causes explicitement
mentionnées pour {nom}.

============================================================
INTERVENTIONS
============================================================

Mets UNIQUEMENT les actions réellement effectuées.

Ces expressions ne sont PAS des interventions :

- prévu
- sera remplacé
- il faudra remplacer
- à prévoir
- demande de travaux émise
- remplacement prévu
- si la vibration augmente
- si le problème continue
- prochainement

IMPORTANT :

Une intervention prévue n'est pas une intervention réalisée.

============================================================
RESULTATS
============================================================

Extrais le résultat du contrôle ou
de l'intervention concernant {nom}.

Un résultat négatif est valide.

Exemples :

- le problème persiste
- aucune amélioration
- toujours présent
- résultat non conforme
- température conforme

============================================================
RECOMMANDATIONS DU TECHNICIEN
============================================================

Extrais uniquement les recommandations
explicitement écrites dans le rapport
pour {nom}.

ATTENTION :

Ces recommandations sont du CONTEXTE.

Elles ne doivent PAS être considérées
comme les recommandations finales de SYNIA.

============================================================
NON RENSEIGNE
============================================================

Si une information est :

- non renseignée
- non notée
- inconnue

=> ne l'invente pas.

============================================================
PLUSIEURS EQUIPEMENTS
============================================================

Si le rapport parle de plusieurs équipements
dans le même paragraphe :

prends uniquement les informations
concernant explicitement {nom}.

Ne mélange jamais les informations
d'un autre équipement.

============================================================

RAPPORT :

{texte}
"""

    return appeler_et_parser(
        prompt,
        SCHEMA_FAITS_EQUIPEMENT,
        max_tokens=1800,
    )


# ============================================================
# ANALYSER UN RAPPORT
# ============================================================

def analyser_rapport(texte):

    if not texte or not str(texte).strip():
        raise ValueError(
            "Le texte du rapport est vide."
        )

    texte = str(texte)

    # Protection contre les NaN provenant d'Excel
    texte = texte.replace(
        "NaN",
        "non renseigné"
    )

    # Limitation du texte
    texte = texte[
        :MAX_CARACTERES_RAPPORT
    ]

    # ----------------------------------------
    # ETAPE 1 :
    # trouver les équipements
    # ----------------------------------------

    liste = _lister_equipements(
        texte
    )

    noms = []

    vus = set()

    for nom in _liste(
        liste.get("equipements")
    ):

        nom = _texte_brut(nom)

        if not nom:
            continue

        cle = _cle(nom)

        if cle not in vus:

            vus.add(cle)

            noms.append(nom)

    print(
        f"🔎 Équipements trouvés : {noms}"
    )

    # ----------------------------------------
    # ETAPE 2 :
    # analyser chaque équipement
    # ----------------------------------------

    equipements = []

    for nom in noms:

        try:

            faits = _extraire_equipement(
                texte,
                nom
            )

            faits["nom"] = nom

            equipements.append(
                faits
            )

        except Exception as erreur:

            print(
                f"⚠️ Équipement {nom} ignoré : "
                f"{erreur}"
            )

    resultat = {

        "reference": liste.get(
            "reference"
        ),

        "date": liste.get(
            "date"
        ),

        "equipements": equipements,

        "techniciens": _liste(
            liste.get("techniciens")
        ),

        "recommandations_rapport": _liste(
            liste.get(
                "recommandations_rapport"
            )
        ),
    }

    return normaliser_resultat(
        resultat
    )


# ============================================================
# REGROUPER LES EQUIPEMENTS
# ============================================================

def regrouper_equipements(
    nouveaux_resultats
):
    """
    Si C-102 apparaît dans plusieurs nouveaux
    rapports, on regroupe ses informations.
    """

    groupes = {}

    for rapport in (
        nouveaux_resultats or []
    ):

        for equipement in _liste(
            rapport.get("equipements")
        ):

            if not isinstance(
                equipement,
                dict
            ):
                continue

            nom = _texte_brut(
                equipement.get("nom")
            )

            if not nom:
                continue

            cle = _cle(nom)

            groupe = groupes.setdefault(
                cle,
                {
                    "nom": nom,
                    "type": None,
                    "anomalies": [],
                    "causes": [],
                    "interventions": [],
                    "resultats": [],
                    "recommandations_technicien": [],
                }
            )

            # Type
            if (
                not groupe["type"]
                and equipement.get("type")
            ):

                groupe["type"] = (
                    _texte_brut(
                        equipement.get("type")
                    )
                )

            # Anomalies
            for anomalie in _liste(
                equipement.get(
                    "anomalies"
                )
            ):

                if not isinstance(
                    anomalie,
                    dict
                ):
                    continue

                description = _texte_brut(
                    anomalie.get(
                        "description"
                    )
                )

                if not description:
                    continue

                niveau = anomalie.get(
                    "niveau"
                )

                if niveau not in NIVEAUX:
                    niveau = None

                existe = any(
                    _cle(
                        a.get("description")
                    )
                    == _cle(description)

                    for a in groupe[
                        "anomalies"
                    ]
                )

                if not existe:

                    groupe[
                        "anomalies"
                    ].append(
                        {
                            "description":
                                description,

                            "niveau":
                                niveau,
                        }
                    )

            # Listes simples
            for champ in (
                "causes",
                "interventions",
                "resultats",
                "recommandations_technicien",
            ):

                existants = {
                    str(x).lower()
                    for x in groupe[champ]
                }

                for valeur in _liste(
                    equipement.get(
                        champ
                    )
                ):

                    valeur = _texte_brut(
                        valeur
                    )

                    if (
                        valeur
                        and valeur.lower()
                        not in existants
                    ):

                        groupe[
                            champ
                        ].append(
                            valeur
                        )

                        existants.add(
                            valeur.lower()
                        )

    return groupes


# ============================================================
# HASH / FICHIERS ACTUELS
# ============================================================

def _hashes_et_fichiers(
    nouveaux_resultats
):

    hashes = set()
    fichiers = set()

    for rapport in (
        nouveaux_resultats or []
    ):

        hash_contenu = (
            rapport.get(
                "hash_contenu"
            )
        )

        if hash_contenu:
            hashes.add(
                hash_contenu
            )

        fichier = rapport.get(
            "fichier"
        )

        if fichier:
            fichiers.add(
                _cle(fichier)
            )

    return hashes, fichiers


# ============================================================
# HISTORIQUE PERTINENT
# ============================================================

def analyser_historique_equipements(
    nouveaux_resultats,
    historique
):
    """
    Ne cherche que l'historique des équipements
    présents dans les nouveaux rapports.
    """

    groupes = regrouper_equipements(
        nouveaux_resultats
    )

    hashes_courants, fichiers_courants = (
        _hashes_et_fichiers(
            nouveaux_resultats
        )
    )

    resultat = {
        "equipements_concernes": []
    }

    for cle, groupe in groupes.items():

        rapports_historiques = []

        for rapport in (
            historique or []
        ):

            hash_rapport = rapport.get(
                "hash_contenu"
            )

            # Ne pas considérer le document actuel
            # comme ancien historique
            if (
                hash_rapport
                and hash_rapport
                in hashes_courants
            ):
                continue

            if not hash_rapport:

                nom_fichier = _cle(
                    rapport.get(
                        "fichier"
                    )
                )

                if (
                    nom_fichier
                    in fichiers_courants
                ):
                    continue

            # Cherche cet équipement
            # dans ce rapport historique
            for equipement in _liste(
                rapport.get(
                    "equipements"
                )
            ):

                if not isinstance(
                    equipement,
                    dict
                ):
                    continue

                ancien_nom = (
                    equipement.get(
                        "nom"
                    )
                )

                if (
                    ancien_nom
                    and _cle(
                        ancien_nom
                    )
                    == cle
                ):

                    rapports_historiques.append(
                        {
                            "fichier":
                                rapport.get(
                                    "fichier"
                                ),

                            "date":
                                rapport.get(
                                    "date"
                                ),

                            "equipement":
                                equipement,
                        }
                    )

        # Limite de sécurité
        rapports_historiques = (
            rapports_historiques[
                :MAX_HISTORIQUE_PAR_EQUIPEMENT
            ]
        )

        problemes_precedents = []

        for ancien in (
            rapports_historiques
        ):

            equipement = ancien[
                "equipement"
            ]

            interventions = "; ".join(
                _texte_brut(x)
                for x in _liste(
                    equipement.get(
                        "interventions"
                    )
                )
                if _texte_brut(x)
            )

            for anomalie in _liste(
                equipement.get(
                    "anomalies"
                )
            ):

                if not isinstance(
                    anomalie,
                    dict
                ):
                    continue

                description = _texte_brut(
                    anomalie.get(
                        "description"
                    )
                )

                if not description:
                    continue

                problemes_precedents.append(
                    {
                        "description":
                            description,

                        "fichier":
                            ancien.get(
                                "fichier"
                            ),

                        "date":
                            ancien.get(
                                "date"
                            ),

                        "intervention":
                            interventions,
                    }
                )

        resultat[
            "equipements_concernes"
        ].append(
            {
                "nom":
                    groupe["nom"],

                "present_dans_historique":
                    bool(
                        rapports_historiques
                    ),

                "nb_occurrences_historiques":
                    len(
                        rapports_historiques
                    ),

                "problemes_precedents":
                    problemes_precedents,
            }
        )

    return resultat


# ============================================================
# FONCTIONS FACTUELLES
# ============================================================

def _constat(groupe):

    valeurs = []

    for anomalie in groupe.get(
        "anomalies",
        []
    ):

        description = _texte_brut(
            anomalie.get(
                "description"
            )
        )

        if not description:
            continue

        niveau = anomalie.get(
            "niveau"
        )

        if niveau:

            valeurs.append(
                f"{description} "
                f"(niveau : {niveau})"
            )

        else:

            valeurs.append(
                description
            )

    if valeurs:

        return "; ".join(
            valeurs
        )

    return "Aucune anomalie constatée."


def _intervention(groupe):

    valeurs = [
        _texte_brut(x)
        for x in groupe.get(
            "interventions",
            []
        )
    ]

    valeurs = [
        x for x in valeurs
        if x
    ]

    if valeurs:

        return "; ".join(
            valeurs
        )

    return (
        "Aucune intervention réalisée."
    )


def _resultat(groupe):

    valeurs = [
        _texte_brut(x)
        for x in groupe.get(
            "resultats",
            []
        )
    ]

    valeurs = [
        x for x in valeurs
        if x
    ]

    if valeurs:

        return "; ".join(
            valeurs
        )

    return (
        "Résultat non renseigné."
    )


# ============================================================
# RECUPERER HISTORIQUE D'UN EQUIPEMENT
# ============================================================

def _historique_de(
    analyse_historique,
    nom
):

    for item in _liste(
        (
            analyse_historique or {}
        ).get(
            "equipements_concernes"
        )
    ):

        if (
            _cle(
                item.get("nom")
            )
            == _cle(nom)
        ):

            return item

    return {
        "nom": nom,
        "present_dans_historique": False,
        "nb_occurrences_historiques": 0,
        "problemes_precedents": [],
    }


def _resume_historique(
    historique
):

    problemes = _liste(
        historique.get(
            "problemes_precedents"
        )
    )

    if not problemes:

        return (
            "Aucun problème antérieur "
            "connu pour cet équipement."
        )

    lignes = []

    for probleme in problemes[:3]:

        date = _texte_brut(
            probleme.get("date")
        )

        if not date:
            date = "date inconnue"

        description = _texte_brut(
            probleme.get(
                "description"
            )
        )

        intervention = _texte_brut(
            probleme.get(
                "intervention"
            )
        )

        ligne = (
            f"- {date} : {description}"
        )

        if intervention:

            ligne += (
                " | intervention : "
                f"{intervention}"
            )

        lignes.append(
            ligne
        )

    return (
        "Problèmes historiques :\n"
        + "\n".join(lignes)
    )


# ============================================================
# PROMPT FINAL DE L'IA
# ============================================================

def _prompt_equipement(
    groupe,
    historique
):

    constat = _constat(
        groupe
    )

    intervention = _intervention(
        groupe
    )

    resultat = _resultat(
        groupe
    )

    anomalies = "; ".join(
        _texte_brut(
            a.get("description")
        )
        for a in groupe.get(
            "anomalies",
            []
        )
        if _texte_brut(
            a.get("description")
        )
    )

    if not anomalies:
        anomalies = "aucune"

    causes = "; ".join(
        _texte_brut(x)
        for x in groupe.get(
            "causes",
            []
        )
        if _texte_brut(x)
    )

    if not causes:
        causes = "aucune"

    recommandations_technicien = (
        "; ".join(
            _texte_brut(x)
            for x in groupe.get(
                "recommandations_technicien",
                []
            )
            if _texte_brut(x)
        )
    )

    if not recommandations_technicien:
        recommandations_technicien = (
            "aucune"
        )

    return f"""
ÉQUIPEMENT
{groupe["nom"]}

TYPE
{groupe.get("type") or "inconnu"}

============================================================
FAITS DU RAPPORT ACTUEL
============================================================

Constat :
{constat}

Anomalies :
{anomalies}

Causes connues :
{causes}

Intervention réellement réalisée :
{intervention}

Résultat :
{resultat}

============================================================
HISTORIQUE DU MÊME ÉQUIPEMENT
============================================================

{_resume_historique(historique)}

============================================================
RECOMMANDATIONS ECRITES PAR LE TECHNICIEN
============================================================

{recommandations_technicien}

============================================================
TA MISSION
============================================================

A) RESUME

Rédige un seul petit paragraphe de 2 à 4 phrases.

Le paragraphe doit résumer les faits de CET équipement :

- le constat ou problème ;
- l'intervention réalisée ;
- le résultat.

Ne mélange jamais les informations
d'un autre équipement.

N'invente rien.

Ne parle pas de l'IA.

Pas de markdown.

------------------------------------------------------------

B) ACTIONS

Génère de 0 à {MAX_ACTIONS_PAR_EQUIPEMENT}
recommandations FUTURES de SYNIA.

IMPORTANT :

Les recommandations du technicien sont uniquement
du contexte.

NE LES RECOPIE PAS MOT POUR MOT.

NE LES AJOUTE PAS DIRECTEMENT.

Tu dois produire tes propres recommandations
à partir des faits du rapport et de l'historique.

------------------------------------------------------------

UNE ACTION IA DOIT :

- être future ;
- être concrète ;
- concerner uniquement cet équipement ;
- être justifiée par les faits disponibles.

------------------------------------------------------------

NE FAIS PAS :

- transformer une intervention réalisée
  en recommandation future ;
- transformer une recommandation conditionnelle
  en intervention réalisée ;
- inventer des valeurs numériques ;
- inventer des seuils ;
- inventer une fréquence ;
- inventer une cause ;
- inventer une pièce ;
- inventer un résultat.

------------------------------------------------------------

EQUIPEMENT SANS PROBLEME

Si l'équipement n'a :

- aucune anomalie actuelle
- et aucun problème historique

alors :

actions = []

------------------------------------------------------------

EVITER LES ACTIONS VAGUES

Ne donne pas simplement :

"Surveiller l'équipement."

L'action doit préciser ce qui doit être fait
en fonction du problème réel décrit.

------------------------------------------------------------

PRIORITE

Utilise uniquement :

- élevée
- moyenne
- faible

------------------------------------------------------------

FORMAT

Réponds uniquement avec le JSON demandé.
Pas de texte avant ou après.
"""


# ============================================================
# NETTOYER LES ACTIONS
# ============================================================

def _normaliser_priorite(
    valeur
):

    v = str(
        valeur or ""
    ).strip().lower()

    correspondances = {

        "élevée":
            "élevée",

        "elevee":
            "élevée",

        "élevé":
            "élevée",

        "eleve":
            "élevée",

        "haute":
            "élevée",

        "high":
            "élevée",

        "moyenne":
            "moyenne",

        "moyen":
            "moyenne",

        "medium":
            "moyenne",

        "faible":
            "faible",

        "basse":
            "faible",

        "low":
            "faible",
    }

    return correspondances.get(
        v,
        "moyenne"
    )


def _nettoyer_actions(
    actions
):

    actions_propres = []

    vues = set()

    for action in _liste(
        actions
    ):

        if not isinstance(
            action,
            dict
        ):
            continue

        texte = _texte_brut(
            action.get("action")
        )

        justification = _texte_brut(
            action.get(
                "justification"
            )
        )

        if not texte:
            continue

        cle = texte.lower()

        if cle in vues:
            continue

        vues.add(cle)

        actions_propres.append(
            {
                "priorite":
                    _normaliser_priorite(
                        action.get(
                            "priorite"
                        )
                    ),

                "action":
                    texte,

                "justification":
                    (
                        justification
                        or
                        "Action proposée à partir "
                        "des faits disponibles."
                    ),
            }
        )

        if len(
            actions_propres
        ) >= MAX_ACTIONS_PAR_EQUIPEMENT:

            break

    # Tri par priorité
    ordre = {
        "élevée": 0,
        "moyenne": 1,
        "faible": 2,
    }

    actions_propres.sort(
        key=lambda x:
        ordre.get(
            x["priorite"],
            1
        )
    )

    return actions_propres


# ============================================================
# GENERER LE RESULTAT FINAL
# ============================================================

def generer_resultat_final(
    nouveaux_resultats,
    analyse_historique
):

    groupes = regrouper_equipements(
        nouveaux_resultats
    )

    syntheses = []

    recommandations = []

    for groupe in groupes.values():

        nom = groupe[
            "nom"
        ]

        historique = _historique_de(
            analyse_historique,
            nom
        )

        # Un équipement est considéré problématique
        # s'il possède une anomalie actuelle
        # ou un problème historique.
        a_un_probleme = (
            bool(
                groupe.get(
                    "anomalies"
                )
            )
            or
            bool(
                historique.get(
                    "problemes_precedents"
                )
            )
        )

        resume = ""
        actions_ia = []

        try:

            reponse = appeler_et_parser(
                _prompt_equipement(
                    groupe,
                    historique
                ),
                SCHEMA_EQUIPEMENT,
                max_tokens=1800,
            )

            resume = _texte_brut(
                reponse.get(
                    "resume"
                )
            )

            actions_ia = _nettoyer_actions(
                reponse.get(
                    "actions"
                )
            )

        except Exception as erreur:

            print(
                f"⚠️ Échec IA pour {nom} : "
                f"{erreur}"
            )

        # ----------------------------------------------------
        # FALLBACK DE LA SYNTHESE
        # ----------------------------------------------------

        if not resume:

            resume = (
                f"{_constat(groupe)} "
                f"{_intervention(groupe)} "
                f"{_resultat(groupe)}"
            )

        # ----------------------------------------------------
        # EQUIPEMENT SANS PROBLEME
        # ----------------------------------------------------

        if (
            IGNORER_EQUIPEMENTS_SANS_PROBLEME
            and not a_un_probleme
        ):

            actions_ia = []

        # ----------------------------------------------------
        # IMPORTANT
        #
        # Les recommandations du technicien
        # NE SONT PAS COPIEES ici.
        #
        # L'IA est la seule source des actions finales.
        # ----------------------------------------------------

        syntheses.append(
            {
                "equipement":
                    nom,

                "resume":
                    resume,
            }
        )

        # Un bloc pour l'équipement seulement
        # s'il existe des recommandations
        if actions_ia:

            recommandations.append(
                {
                    "equipement":
                        nom,

                    "actions":
                        actions_ia,
                }
            )

    return {
        "synthese_interventions":
            syntheses,

        "recommandations":
            recommandations,
    }


# ============================================================
# NETTOYER LE RESULTAT FINAL
# ============================================================

def nettoyer_resultat_final(
    resultat
):

    if not isinstance(
        resultat,
        dict
    ):

        return {
            "synthese_interventions": [],
            "recommandations": [],
        }

    # ========================================================
    # SYNTHESES
    # ========================================================

    syntheses = []

    vus_synthese = set()

    for element in _liste(
        resultat.get(
            "synthese_interventions"
        )
    ):

        if not isinstance(
            element,
            dict
        ):
            continue

        nom = _texte_brut(
            element.get(
                "equipement"
            )
        )

        resume = _texte_brut(
            element.get(
                "resume"
            )
        )

        if not nom:
            continue

        cle = _cle(nom)

        if cle in vus_synthese:
            continue

        vus_synthese.add(
            cle
        )

        # Seulement ce que le frontend doit afficher
        syntheses.append(
            {
                "equipement":
                    nom,

                "resume":
                    resume,
            }
        )

    # ========================================================
    # RECOMMANDATIONS
    # ========================================================

    groupes = {}

    for groupe in _liste(
        resultat.get(
            "recommandations"
        )
    ):

        if not isinstance(
            groupe,
            dict
        ):
            continue

        nom = _texte_brut(
            groupe.get(
                "equipement"
            )
        )

        if not nom:
            continue

        cle = _cle(
            nom
        )

        cible = groupes.setdefault(
            cle,
            {
                "equipement":
                    nom,

                "actions":
                    [],
            }
        )

        nouvelles_actions = (
            _nettoyer_actions(
                groupe.get(
                    "actions"
                )
            )
        )

        existantes = {
            a["action"].lower()
            for a in cible[
                "actions"
            ]
        }

        for action in (
            nouvelles_actions
        ):

            if (
                action["action"].lower()
                in existantes
            ):
                continue

            cible[
                "actions"
            ].append(
                action
            )

            existantes.add(
                action["action"].lower()
            )

            if len(
                cible["actions"]
            ) >= MAX_ACTIONS_PAR_EQUIPEMENT:

                break

    recommandations = []

    for groupe in (
        groupes.values()
    ):

        if not groupe[
            "actions"
        ]:
            continue

        recommandations.append(
            {
                "equipement":
                    groupe[
                        "equipement"
                    ],

                "actions":
                    groupe[
                        "actions"
                    ],
            }
        )

    return {
        "synthese_interventions":
            syntheses,

        "recommandations":
            recommandations,
    }


# ============================================================
# FONCTION PRINCIPALE UTILISEE PAR API.PY
# ============================================================

def synthese_globale(
    nouveaux_resultats,
    historique
):

    # --------------------------------------------------------
    # 1. Historique pertinent
    # --------------------------------------------------------

    analyse_historique = (
        analyser_historique_equipements(
            nouveaux_resultats,
            historique
        )
    )

    # --------------------------------------------------------
    # 2. Synthèse + recommandations IA
    # --------------------------------------------------------

    resultat = generer_resultat_final(
        nouveaux_resultats,
        analyse_historique
    )

    # --------------------------------------------------------
    # 3. Nettoyage final
    # --------------------------------------------------------

    resultat = nettoyer_resultat_final(
        resultat
    )

    # --------------------------------------------------------
    # DEBUG
    # --------------------------------------------------------

    print(
        "\n===== SYNTHESE ====="
    )

    print(
        json.dumps(
            resultat[
                "synthese_interventions"
            ],
            ensure_ascii=False,
            indent=2
        )
    )

    print(
        "\n===== RECOMMANDATIONS IA ====="
    )

    print(
        json.dumps(
            resultat[
                "recommandations"
            ],
            ensure_ascii=False,
            indent=2
        )
    )

    # --------------------------------------------------------
    # RESULTAT POUR API.PY
    # --------------------------------------------------------

    return {

        "synthese_interventions":
            resultat[
                "synthese_interventions"
            ],

        "recommandations":
            resultat[
                "recommandations"
            ],

        "analyse_historique":
            analyse_historique,
    }