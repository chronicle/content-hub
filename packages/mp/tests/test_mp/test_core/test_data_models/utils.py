# Copyright 2025 Google LLC
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

import json
from typing import TYPE_CHECKING, Any

from hypothesis import strategies as st

import mp.core.constants

if TYPE_CHECKING:
    from hypothesis.strategies import SearchStrategy

FILE_NAME: str = ""

SAFE_SCRIPT_DISPLAY_NAME_REGEX = mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX.replace(r"\s", " ")
SAFE_PARAM_DISPLAY_NAME_REGEX = mp.core.constants.PARAM_DISPLAY_NAME_REGEX.replace(r"\s", " ")


def _is_not_valid_json(s: str) -> bool:
    try:
        if not s:
            return True
        json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return True
    else:
        return False


st_json_serializable = st.recursive(
    st.none() | st.booleans() | st.floats(allow_nan=False) | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)

st_non_json_string = st.text().filter(_is_not_valid_json).filter(lambda s: s != "")


st_valid_param_name = st.from_regex(SAFE_PARAM_DISPLAY_NAME_REGEX).filter(
    lambda v: 0 < len(v) < mp.core.constants.PARAM_NAME_MAX_LENGTH
    and len(v.split()) <= mp.core.constants.PARAM_NAME_MAX_WORDS
)
st_excluded_param_name = st.sampled_from(
    sorted(mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS)
)

st_valid_identifier_name = st.from_regex(SAFE_SCRIPT_DISPLAY_NAME_REGEX).filter(
    lambda s: len(s) <= mp.core.constants.DISPLAY_NAME_MAX_LENGTH
)


@st.composite
def st_invalid_regex(draw: st.DrawFn) -> str:
    return draw(st.just("!@#$%^&*"))


@st.composite
def st_invalid_long_identifier(draw: st.DrawFn) -> str:
    return draw(st.text(min_size=mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1))


@st.composite
def st_invalid_long_description(draw: st.DrawFn) -> str:
    return draw(st.text(min_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH + 1))


@st.composite
def st_invalid_long_param_name(draw: st.DrawFn) -> str:
    return draw(st.text(min_size=mp.core.constants.PARAM_NAME_MAX_LENGTH + 1))


@st.composite
def st_invalid_too_many_words_param_name(draw: st.DrawFn) -> str:
    return draw(st.text().filter(lambda s: len(s.split()) > mp.core.constants.PARAM_NAME_MAX_WORDS))


def st_with_invalid_field(
    base_strategy: SearchStrategy[dict[str, Any]],
    field_name: str,
    invalid_value_strategy: SearchStrategy[Any],
) -> SearchStrategy[dict[str, Any]]:
    """Creates a strategy that injects an invalid value into a specific field."""

    @st.composite
    def invalid_field_strategy(draw: st.DrawFn) -> dict[str, Any]:
        data = draw(base_strategy)
        data[field_name] = draw(invalid_value_strategy)
        return data

    return invalid_field_strategy()
