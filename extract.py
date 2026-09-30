import os

import pymupdf as fitz
from docx import Document
from docx.opc.exceptions import PackageNotFoundError


EXTENSIONS_ACCEPTEES = (".pdf", ".docx", ".txt")


class ExtractionError(Exception):
    """Erreur d'extraction d'un document de maintenance."""


class FormatNonSupporte(ExtractionError):
    """Format de fichier refusé."""


class FichierVide(ExtractionError):
    """Fichier sans contenu exploitable."""


class FichierIllisible(ExtractionError):
    """PDF, DOCX ou TXT illisible."""


def extension_fichier(chemin):
    return os.path.splitext(chemin or "")[1].lower()


def format_accepte(chemin):
    return extension_fichier(chemin) in EXTENSIONS_ACCEPTEES


def extract_text_from_pdf(file_path):
    try:
        document = fitz.open(file_path)
    except Exception as erreur:
        raise FichierIllisible(
            "Le fichier PDF est illisible ou corrompu."
        ) from erreur

    try:
        if document.is_encrypted:
            try:
                ouvert = document.authenticate("")
            except Exception:
                ouvert = False

            if not ouvert:
                raise FichierIllisible(
                    "Le fichier PDF est protégé et ne peut pas être lu."
                )

        texte = ""
        for page in document:
            texte += page.get_text() or ""
    finally:
        document.close()

    return texte


def extract_text_from_docx(file_path):
    try:
        document = Document(file_path)
    except PackageNotFoundError as erreur:
        raise FichierIllisible(
            "Le fichier DOCX est illisible ou corrompu."
        ) from erreur
    except Exception as erreur:
        raise FichierIllisible(
            "Le fichier DOCX est illisible ou corrompu."
        ) from erreur

    parties = [paragraph.text for paragraph in document.paragraphs]

    for tableau in document.tables:
        for ligne in tableau.rows:
            for cellule in ligne.cells:
                if cellule.text:
                    parties.append(cellule.text)

    return "\n".join(parties)


def extract_text_from_txt(file_path):
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    dernier_erreur = None

    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError as erreur:
            dernier_erreur = erreur
            continue
        except OSError as erreur:
            raise FichierIllisible(
                "Le fichier TXT est illisible."
            ) from erreur

    raise FichierIllisible(
        "Le fichier TXT est illisible (encodage non reconnu)."
    ) from dernier_erreur


def extract_text(file_path):
    if not file_path or not os.path.isfile(file_path):
        raise FichierIllisible(
            "Le fichier est introuvable ou illisible."
        )

    if os.path.getsize(file_path) == 0:
        raise FichierVide("Le fichier est vide.")

    extension = extension_fichier(file_path)

    if extension not in EXTENSIONS_ACCEPTEES:
        raise FormatNonSupporte(
            "Format non supporté. Formats acceptés : PDF, DOCX, TXT."
        )

    try:
        if extension == ".pdf":
            texte = extract_text_from_pdf(file_path)
        elif extension == ".docx":
            texte = extract_text_from_docx(file_path)
        else:
            texte = extract_text_from_txt(file_path)
    except ExtractionError:
        raise
    except Exception as erreur:
        raise FichierIllisible(
            "Le document n'a pas pu être lu."
        ) from erreur

    texte = (texte or "").strip()

    if not texte:
        raise FichierVide(
            "Le document ne contient aucun texte exploitable."
        )

    return texte