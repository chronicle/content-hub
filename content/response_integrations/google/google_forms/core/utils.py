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

import json

from TIPCommon.types import SingleJson

from .exceptions import InvalidJSONFormatException


def parse_string_to_dict(json_string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        json_string(str): string to parse.

    Returns:
        SingleJson: parsed dict.
    """
    try:
        return json.loads(json_string)

    except json.JSONDecodeError as err:
        raise InvalidJSONFormatException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err
