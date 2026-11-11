from __future__ import annotations

from typing import Any


def extract_text_from_adf(content: Any) -> str:
    """Extracts plain text from an Atlassian Document Format (ADF) structure.

    This function recursively navigates through a nested structure of dictionaries
    and lists that represent a document in Atlassian's standard format for
    rich text. It extracts and concatenates the text from various node types.

    Args:
        content (Any): The ADF content, which can be a dictionary representing a
            node, a list of nodes, or a simple string.

    Returns:
        str: The extracted plain text content from the ADF structure.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        if content.get("type") == "text":
            return str(content.get("text", ""))

        node_type: str = str(content.get("type", ""))
        extracted: str = ""

        if "content" in content:
            parts: list[str] = [
                extract_text_from_adf(item) for item in content["content"]
            ]
            extracted = "".join(parts)

        if node_type == "paragraph":
            return extracted + "\n"

        return extracted

    if isinstance(content, list):
        list_parts: list[str] = [extract_text_from_adf(item) for item in content]
        return "".join(list_parts)

    return str(content) if content is not None else ""
