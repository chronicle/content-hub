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

"""Common test constants and helper utilities."""

from __future__ import annotations

import pathlib

from integration_testing.common import get_def_file_content

INTEGRATION_PATH = pathlib.Path(__file__).parent.parent
CONFIG_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "config.json")
CONFIG = get_def_file_content(CONFIG_PATH)

MOCKS_PATH = pathlib.Path.joinpath(INTEGRATION_PATH, "tests", "mocks")
MOCK_DATA_FILE = pathlib.Path.joinpath(MOCKS_PATH, "mock_data.json")
MOCK_DATA = get_def_file_content(MOCK_DATA_FILE)

INDICATOR_MOCK_RAW = MOCK_DATA.get("indicators_response", {})
INDICATORS_LIST_MOCK = MOCK_DATA.get("indicators_list_response", {})
SECURITY_LABELS_MOCK = MOCK_DATA.get("security_labels_response", {})
ALERT_FULL_DETAILS_MOCK = MOCK_DATA.get("alert_full_details_response", {})
