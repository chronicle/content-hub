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

"""Constants for MicrosoftAzureSentinel Integration Unit Tests."""
import json
import os
from typing import Union, Any, Dict

JSON = Union[Dict[str, Any], list]


def get_json_data(file_path: str) -> JSON:
  return json.load(
    open(
      os.path.join(
        os.path.dirname(__file__),
        file_path
        )
      )
  )


MOCK_DATA = get_json_data(
    "mock_data.json"
)

GET_INCIDENTS_BY_FILTER = MOCK_DATA.get(
    "get_incidents_by_filter"
)

GET_INCIDENT_BY_INCIDENT_NUMBER = MOCK_DATA.get(
  "get_incident_by_incident_number"
)
