import pymupdf as fitz
from docx import Document

#include the 3  possible type of files report .txt .doc or .pdf
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


def extract_text(file_path):
  
    # Detect the file type and extract its text.


    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)

    elif file_path.endswith(".docx"):
        return extract_text_from_docx(file_path)

    elif file_path.endswith(".txt"):
        return extract_text_from_txt(file_path)

    else:
        return "Unsupported file type"
        