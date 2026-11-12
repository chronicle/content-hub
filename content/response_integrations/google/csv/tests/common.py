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
from integration_testing.common import get_def_file_content

import json
import pathlib
from typing import Any


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
MOCK_DATA_PATH: pathlib.Path = (
    pathlib.Path(__file__).parent / "mock_data.json"
)


def load_mock_data() -> dict[str, Any]:
    """Loads and caches mock data from the JSON file."""
    with MOCK_DATA_PATH.open("r") as f:
        return json.load(f)


def get_mock_data(key: str) -> Any:
    """Retrieves a specific value from the cached mock data."""
    data = load_mock_data()
    if key not in data:
        raise KeyError(
            f"Key '{key}' not found in mock_data.json. "
            f"Available keys: {list(data.keys())}"
        )
    return data[key]
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
