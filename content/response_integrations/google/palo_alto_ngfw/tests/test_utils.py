from __future__ import annotations

from palo_alto_ngfw.core.utils import normalize_string


def test_normalize_string_simple_text() -> None:
    text: str = "validText"
    result: str = normalize_string(text)
    assert result == "validtext"


def test_normalize_string_with_capitals() -> None:
    text: str = "CapitalizedText"
    result: str = normalize_string(text)
    assert result == "capitalizedtext"


def test_normalize_string_with_spaces() -> None:
    text: str = " text with spaces "
    result: str = normalize_string(text)
    assert result == "text_with_spaces"


def test_normalize_string_contiguous_spaces() -> None:
    text: str = "  text   with    many    spaces  "
    result: str = normalize_string(text)
    assert result == "text_with_many_spaces"


def test_normalize_string_special_characters() -> None:
    text: str = "env-PROD.test@identifier!"
    result: str = normalize_string(text)
    assert result == "env_prod_test_identifier"


def test_normalize_string_empty() -> None:
    text: str = ""
    result: str = normalize_string(text)
    assert result == ""
