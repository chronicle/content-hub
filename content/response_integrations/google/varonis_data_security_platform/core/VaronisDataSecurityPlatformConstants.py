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
INTEGRATION_IDENTIFIER = "VaronisDataSecurityPlatform"

UPDATE_ALERT_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Update Alert"
STORED_IDS_LIMIT = 3000
VENDOR_NAME = "Varonis"
PRODUCT_NAME = "Data Security Platform"
ALERT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
EVENT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
SEVERITY_MAPIING = {"Low": 40, "Medium": 60, "High": 80}
LAST_DAYS = "lastdays"
ALERT_SEQ_ID_DEFAULT = 0
ALERT_SEQ_ID_WITH_TIME = "alertseqid"
ALERT_SEQ_ID_INDEX = 0
ALERT_TIMESTAMP_INDEX = 1
ALERT_DAY_FORMAT = "%Y%m%d"
