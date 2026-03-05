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

"""consts
======

A module containing all constant in use by TIPCommon package,
and common constant used in Marketplace Integrations.

Usage Example::

    import TIPCommon

    print(TIPCommon.ALLOWLIST_FILTER)
    # 1
"""

from __future__ import annotations

import re

_CAMEL_TO_SNAKE_PATTERN1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_TO_SNAKE_PATTERN2 = re.compile(r"([a-z0-9])([A-Z])")

TRUE_VAL_LOWER_STRINGS = ("true", str(True).lower())
FALSE_VAL_LOWER_STRINGS = ("false", str(False).lower())

ALLOWLIST_FILTER = 1
BLOCKLIST_FILTER = 2

UNIX_FORMAT = 1
DATETIME_FORMAT = 2

STORED_IDS_LIMIT = 1000
ACCEPTABLE_TIME_INTERVAL_IN_MINUTES = 5
TIMEOUT_THRESHOLD = 0.9
ACTION_TIMEOUT_THRESHOLD_IN_SEC = 10

NUM_OF_HOURS_IN_DAY = 24
NUM_OF_HOURS_IN_3_DAYS = 72
NUM_OF_SEC_IN_SEC = 1
NUM_OF_MILLI_IN_SEC = 1000
NUM_OF_MILLI_IN_MINUTE = 60000
NUM_OF_MIN_IN_HOUR = 60
NUM_OF_SEC_IN_MIN = 60
ONE_DAY_IN_MILLISECONDS = NUM_OF_MILLI_IN_MINUTE * NUM_OF_MIN_IN_HOUR * NUM_OF_HOURS_IN_DAY

GLOBAL_CONTEXT_SCOPE = 0
CONNECTOR_CONTEXT_SCOPE = 4

SIEM_ID_ATTR_KEY = "siem_alert_id"

IDS_DB_KEY = "ids"
IDS_FILE_NAME = "ids.json"

NONE_VALS = [None, "", [], {}, ()]

ENTITY_OG_ID_KEY = "OriginalIdentifier"

SOAR_COMMENT_PREFIX = "Chronicle SOAR: "
SLO_APPROACHING_COMMENT = "SLO will be breached in {} days."
SLO_BREACHED_COMMENT = "SLO was breached."
SLO_APPROACHING_REGEXP = r"^SLO will be breached in (\d{1,3}) days\.$"

DT_FORAMT_RFC3339 = "%Y-%m-%dT%H:%M:%SZ"

RFC_3339_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
_TIMEFRAME_MAPPING = {
    "Last Hour": {"hours": 1},
    "Last 6 Hours": {"hours": 6},
    "Last 24 Hours": {"hours": 24},
    "Last Week": "last_week",
    "Last Month": "last_month",
    "Custom": "custom",
}

ONE_PLATFORM_ARG: str = "--onePlatformSupport"

DEFAULT_ENVIRONMENT: str = "Default Environment"

ACTION_NOT_SUPPORTED_PLATFORM_VERSION_MSG: str = (
    "Action is not available for the current platform version please use higher platform version"
)
NO_CONTENT_STATUS_CODE: int = 204
DATAPLANE_1P_HEADER: str = "x-goog-api-version"
DEFAULT_1P_PAGE_SIZE: int = 1000
