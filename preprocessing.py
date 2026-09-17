import re


def clean_text(text):

    if not text:
        return ""

    # Replace multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Replace too many new lines
    text = re.sub(r"\n+", "\n", text)

    # Remove spaces at beginning/end of lines
    lines = []

    for line in text.split("\n"):
        line = line.strip()

        if line:
            lines.append(line)

    text = "\n".join(lines)

    return text.strip()