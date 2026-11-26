# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
