import re
import unicodedata


def sanitize_string(string: str) -> str:
    string = unicodedata.normalize("NFKD", string).encode("ASCII", "ignore").decode()
    string = re.sub(r"[^a-z0-9_-]+", "-", string.lower())
    return re.sub(r"-+", "-", string).strip("-")
