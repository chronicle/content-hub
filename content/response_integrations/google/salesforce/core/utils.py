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

from .constants import DEFAULT_MAX_RECORDS, INVALID_MAX_RECORDS_MSG, MAX_RECORDS_LIMIT
from .SalesforceManager import SalesforceManagerError


def parse_max_records(max_records: str | None) -> int:
    """Validate and normalize the "Max Records To Return" parameter.

    Args:
        max_records: Raw parameter value. None or blank returns DEFAULT_MAX_RECORDS.

    Returns:
        Validated integer within [1, MAX_RECORDS_LIMIT].

    Raises:
        SalesforceManagerError: If the value is not an integer within range.

    """
    if max_records is None or not max_records.strip():
        return DEFAULT_MAX_RECORDS

    try:
        limit = int(max_records.strip())
    except ValueError as err:
        raise SalesforceManagerError(INVALID_MAX_RECORDS_MSG) from err

    if not 1 <= limit <= MAX_RECORDS_LIMIT:
        raise SalesforceManagerError(INVALID_MAX_RECORDS_MSG)

    return limit
