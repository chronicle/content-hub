from __future__ import annotations
import re

def normalize_string(text: str) -> str:
    """Normalize a string by replacing non-alphanumeric characters with underscores.

    - Replace all non-alphanumeric characters with an underscore
    - Compress multiple consecutive underscores into one
    - Convert to lowercase
    - Strip leading/trailing underscores

    :param text: String to normalize
    :return: Normalized string
    """
    if text:
        # Replace all non-alphanumeric characters with an underscore
        text = re.sub(r'[^a-zA-Z0-9]', '_', text.lower())
        # Compress multiple consecutive underscores into one
        return re.sub(r'_+', '_', text).strip('_')
    return text
