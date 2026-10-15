from __future__ import annotations

import string

import pytest
from core.constants import MIN_PASSWORD_LENGTH, PASSWORD_SYMBOLS
from core.utils import generate_random_password


def test_generate_random_password_meets_okta_complexity() -> None:
    password = generate_random_password()
    assert len(password) == 16
    assert any(char in string.ascii_lowercase for char in password)
    assert any(char in string.ascii_uppercase for char in password)
    assert any(char in string.digits for char in password)
    assert any(char in PASSWORD_SYMBOLS for char in password)
    assert all(char in string.ascii_letters + string.digits + PASSWORD_SYMBOLS for char in password)
    assert not any(char in "\"'\\[]{}|" for char in password)


def test_generate_random_password_respects_length() -> None:
    password = generate_random_password(20)
    assert len(password) == 20


def test_generate_random_password_rejects_short_length() -> None:
    with pytest.raises(ValueError, match="at least"):
        generate_random_password(MIN_PASSWORD_LENGTH - 1)


def test_generate_random_password_is_not_constant() -> None:
    samples = {generate_random_password() for _ in range(8)}
    assert len(samples) == 8
