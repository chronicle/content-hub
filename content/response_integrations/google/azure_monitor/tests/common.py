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
from integration_testing.common import get_def_file_content

import pathlib

from TIPCommon.types import SingleJson
from azure_monitor.core.data_models import AzureLogEntry
from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
LIST_LOGS: SingleJson = MOCK_DATA["search_logs"]
LIST_LOG_ENTRY: list[AzureLogEntry] = AzureLogEntry.from_json(LIST_LOGS)


def azure_log_entries_to_api_json(entries: list[AzureLogEntry]) -> SingleJson:
    """Convert list of AzureLogEntry objects into API-style JSON format.

    Args:
        entries (list[AzureLogEntry]): List of AzureLogEntry instances.

    Returns:
        SingleJson: JSON object following Azure Monitor API format.
    """
    return {
        "tables": [
            {
                "name": "PrimaryResult",
                "columns": [
                    {"name": "TimeGenerated", "type": "datetime"},
                    {"name": "OperationName", "type": "string"},
                ],
                "rows": [
                    [entry.time_generated, entry.operation_name]
                    for entry in entries
                ],
            }
        ]
    }
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
