from app.parsers import ios_style


def normalize_cisco(text: str) -> dict:
    return ios_style.normalize(text)
