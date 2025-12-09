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

import base64
import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from hypothesis import strategies as st
from hypothesis.provisional import urls
from pydantic import FileUrl, HttpUrl, TypeAdapter, ValidationError

import mp.core.constants

if TYPE_CHECKING:
    from enum import Enum

    from hypothesis.strategies import SearchStrategy

FILE_NAME: str = ""

SAFE_SCRIPT_DISPLAY_NAME_REGEX = mp.core.constants.SCRIPT_DISPLAY_NAME_REGEX.replace(r"\s", " ")
SAFE_PARAM_DISPLAY_NAME_REGEX = mp.core.constants.PARAM_DISPLAY_NAME_REGEX.replace(r"\s", " ")
SAFE_SCRIPT_IDENTIFIER_NAME_REGEX = mp.core.constants.SCRIPT_IDENTIFIER_REGEX.replace(r"\s", " ")


def _is_not_valid_json(s: str) -> bool:
    try:
        if not s:
            return True
        json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return True
    else:
        return False


def _is_pydantic_valid_url(url: str, adapter: TypeAdapter) -> bool:
    try:
        adapter.validate_python(url)
    except ValidationError:
        return False
    else:
        return True


st_json_serializable = st.recursive(
    st.none() | st.booleans() | st.floats(allow_nan=False) | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
)

st_pydantic_valid_https_url = urls().filter(
    lambda u: urlparse(u).scheme == "https" and _is_pydantic_valid_url(u, TypeAdapter(HttpUrl))
)

st_pydantic_valid_file_url = urls().filter(
    lambda u: urlparse(u).scheme == "file" and _is_pydantic_valid_url(u, TypeAdapter(FileUrl))
)

st_valid_url = st.one_of(st_pydantic_valid_https_url, st_pydantic_valid_file_url)

st_valid_param_name = (
    st.from_regex(SAFE_PARAM_DISPLAY_NAME_REGEX, fullmatch=True)
    .map(str.strip)
    .filter(
        lambda v: 0 < len(v) < mp.core.constants.PARAM_NAME_MAX_LENGTH
        and len(v.split()) <= mp.core.constants.PARAM_NAME_MAX_WORDS
    )
)
st_excluded_param_name = st.sampled_from(
    sorted(mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS)
)

st_valid_identifier_name = st.from_regex(SAFE_SCRIPT_IDENTIFIER_NAME_REGEX, fullmatch=True).filter(
    lambda s: len(s) <= mp.core.constants.DISPLAY_NAME_MAX_LENGTH
)

st_valid_display_name = st.from_regex(SAFE_SCRIPT_DISPLAY_NAME_REGEX, fullmatch=True).filter(
    lambda s: len(s) <= mp.core.constants.DISPLAY_NAME_MAX_LENGTH
)

st_valid_short_description = st.text(max_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH)

st_valid_long_description = st.text(max_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH)

st_valid_version = st.floats(min_value=mp.core.constants.MINIMUM_SCRIPT_VERSION)

st_valid_png_b64_string = st.binary(min_size=1).map(lambda b: base64.b64encode(b).decode("utf-8"))
st_valid_svg_string = st.just("<svg></svg>")


def st_valid_non_built_param_type(param_type: type[Enum]) -> SearchStrategy[dict[str, Any]]:
    return st.sampled_from(param_type).map(lambda e: e.to_string())


def st_valid_built_param_type(param_type: type[Enum]) -> SearchStrategy[dict[str, Any]]:
    return st.sampled_from(param_type).flatmap(lambda e: st.sampled_from([e.value, str(e.value)]))


def st_valid_built_type(param_type: type[Enum]) -> SearchStrategy[dict[str, Any]]:
    return st.sampled_from(param_type).map(lambda e: e.value)
