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

from hypothesis import strategies as st

import mp.core.constants

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

st_non_json_string = st.text().filter(_is_not_valid_json)


st_valid_param_name = st.from_regex(SAFE_PARAM_DISPLAY_NAME_REGEX).filter(
    lambda v: 0 < len(v) < mp.core.constants.PARAM_NAME_MAX_LENGTH
    and len(v.split()) <= mp.core.constants.PARAM_NAME_MAX_WORDS
)
st_excluded_param_name = st.sampled_from(
    sorted(mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS)
)

st_valid_identifier_name = st.from_regex(r"^[a-zA-Z0-9- ]+$").filter(
    lambda s: len(s) <= mp.core.constants.DISPLAY_NAME_MAX_LENGTH
)
