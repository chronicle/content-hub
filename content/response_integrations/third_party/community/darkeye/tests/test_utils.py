from __future__ import annotations

import pytest

from darkeye.core.exceptions import DarkEyeInvalidEntityError
from darkeye.core.utils import clean, is_about_domain, mentions_email, normalize_domain, normalize_email


def test_clean_normalizes_text_and_drops_controls() -> None:
    assert clean("  𝐄𝐱𝐚𝐦𝐩𝐥𝐞‮  group\n") == "Example group"
    assert clean(True) == ""
    assert clean(None) == ""
    assert clean(42) == "42"


@pytest.mark.parametrize("value", ["*.example.com", "exa?mple.com", "example", "10.0.0.1", "example.com/path"])
def test_normalize_domain_rejects_non_plain_domains(value: str) -> None:
    with pytest.raises(DarkEyeInvalidEntityError):
        normalize_domain(value)


def test_normalize_domain_and_email() -> None:
    assert normalize_domain("Mail.EXAMPLE.com.") == "mail.example.com"
    assert normalize_email("Bob.Smith+tag@Example.COM") == "bob.smith+tag@example.com"
    with pytest.raises(DarkEyeInvalidEntityError):
        normalize_email("bob*@example.com")


@pytest.mark.parametrize(
    ("website", "title", "expected"),
    [
        ("example.com", "", True),
        ("mail.example.com", "", True),
        ("notexample.com", "", False),
        ("", "example.com user table", True),
        ("", "mail.example.com dump", True),
        ("", "example.com.other.org user table", False),
        ("", "notexample.com user table", False),
    ],
)
def test_is_about_domain(website: str, title: str, expected: bool) -> None:
    assert is_about_domain(website, title, "example.com") is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("rows include bob@example.com and others", True),
        ("<BOB@EXAMPLE.COM>", True),
        ("bob@example.com.", True),
        ("rob.bob@example.com", False),
        ("xbob@example.com", False),
        ("bob@example.com.au", False),
        ("bob@example.community", False),
        ("o'bob@example.com", False),
    ],
)
def test_mentions_email(text: str, expected: bool) -> None:
    assert mentions_email("bob@example.com", text) is expected
