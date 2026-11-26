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
import pathlib
import json

from TIPCommon.types import SingleJson


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"


def get_json_file_content(json_file_path: str | pathlib.Path | None) -> SingleJson:
    """Get the content of a json file"""

    if isinstance(json_file_path, str):
        json_file_path: pathlib.Path = pathlib.Path(json_file_path)

    return json.loads(json_file_path.read_text(encoding="utf-8"))
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
CONFIG: dict = get_def_file_content(CONFIG_PATH) if CONFIG_PATH.exists() else {}
