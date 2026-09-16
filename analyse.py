import re

# les information a decouper
TITRES = {
    "reference":       "Référence",
    "date":            "Date d'intervention",
    "site":            "Site",
    "equipement":      "Équipement concerné",
    "technicien":      "Technicien",
    "duree":           "Durée d'intervention",
    "description":     "Description du problème",
    "diagnostic":      "Diagnostic",
    "action":          "Action réalisée",
    "recommandations": "Recommandations",
    "pieces":          "Pièces utilisées",
    "statut":          "Statut",
}


def decouper(texte):
    #  find the differnt title in the text
    positions = []
    for champ, titre in TITRES.items():
        trouve = re.search(titre + r"\s*:", texte)
        if trouve:
            positions.append((trouve.start(), trouve.end(), champ))

    #ordre selon l'order de doc 
    positions.sort()

    # le contenu d'un titre = tout ce qu'il y a jusqu'au titre suivant
    resultat = {}
    for i, (debut, fin, champ) in enumerate(positions):
        if i + 1 < len(positions):
            fin_du_contenu = positions[i + 1][0] #on pred toujour le debut du prochain titre[0] en 2eme indx
        else:
            fin_du_contenu = len(texte) 

        resultat[champ] = texte[fin:fin_du_contenu].strip() #enlève ces espaces seulement au début et à la fin

    # pour les champ non exister
    for champ in TITRES:
        if champ not in resultat:
            resultat[champ] = None

    return resultat
 # this for later to detect if the raport is exactly abot the equip
def compter_champs_remplis(donnees):
    """Combien de champs sur 12 ont ete trouves (sert a detecter un doc suspect)."""
    return sum(1 for champ in TITRES if donnees.get(champ))

