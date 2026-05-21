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
INTEGRATION_NAME = "GoogleTranslate"
INTEGRATION_DISPLAY_NAME = "Google Translate"

# Actions
PING_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Ping"
TRANSLATE_TEXT_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - Translate Text"
LIST_LANGUAGES_SCRIPT_NAME = f"{INTEGRATION_DISPLAY_NAME} - List Languages"

ENDPOINTS = {
    "ping": "/language/translate/v2/languages",
    "get_languages": "/language/translate/v2/languages",
    "translate": "/language/translate/v2",
}

DEFAULT_RECORDS_LIMIT = 50
FILTER_KEY_MAPPING = {"Select One": "", "Name": "name"}

FILTER_STRATEGY_MAPPING = {
    "Not Specified": "",
    "Equal": lambda item, value: str(item).lower() == str(value).lower(),
    "Contains": lambda item, value: str(value).lower() in str(item).lower(),
}
