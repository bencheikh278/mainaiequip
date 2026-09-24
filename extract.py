import fitz #pdf
from docx import Document #docx
import pandas as pd #exel
from PIL import Image #png
import pytesseract #png


def extract_text_from_pdf(file_path):
    text = ""
    document = fitz.open(file_path)
    for page in document:
        text += page.get_text()
    document.close()
    return text


def extract_text_from_docx(file_path):
    text = ""
    document = Document(file_path)
    for paragraph in document.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    return text


def extract_text_from_excel(file_path):
    """

    Lit toutes les feuilles d'un classeur Excel et les convertit en
    texte lisible. Chaque ligne devient une suite "colonne: valeur",
    proche du format des rapports texte 
    """
    text = ""
    feuilles = pd.read_excel(file_path, sheet_name=None)  # toutes les feuilles

    for nom_feuille, df in feuilles.items():
        text += f"--- Feuille : {nom_feuille} ---\n"
        for _, ligne in df.iterrows():
            paires = [
                f"{colonne}: {valeur}"
                for colonne, valeur in ligne.items()
                if pd.notna(valeur)
            ]
            text += " | ".join(paires) + "\n"
        text += "\n"

    return text


def extract_text_from_image(file_path):
    """
    OCR : convertit une image (photo ou scan de rapport papier) en
    texte via Tesseract.
    """
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image, lang="fra")

    return text


def extract_text(file_path):
    # Detect the file type and extract its text.
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        return extract_text_from_docx(file_path)
    elif file_path.endswith(".txt"):
        return extract_text_from_txt(file_path)
    elif file_path.endswith((".xlsx", ".xls")):
        return extract_text_from_excel(file_path)
    elif file_path.endswith((".png", ".jpg", ".jpeg")):
        return extract_text_from_image(file_path)
    else:
        return "Unsupported file type"