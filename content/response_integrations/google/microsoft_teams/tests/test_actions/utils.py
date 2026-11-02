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

import json
from unittest.mock import MagicMock


class MockSiemplifyEntity:
    def __init__(self, identifier, entity_type):
        self.identifier = identifier
        self.entity_type = entity_type


def create_mock_response(json_data, status_code=200):
    """Create a MagicMock response object."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.content = json.dumps(json_data).encode("utf-8")
    response.raise_for_status.return_value = None
    return response
