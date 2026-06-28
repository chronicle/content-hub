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

from service_desk_plus.core import data_parser
from service_desk_plus.core.datamodels import WorkOrder
from integration_testing.common import get_def_file_content

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)

REQUEST: WorkOrder = data_parser.build_request(MOCK_DATA["GET_REQUESTS_RESPONSE_FULL"])
ADD_REQUEST_MOCK: WorkOrder = data_parser.build_request(
    MOCK_DATA["ADD_REQUEST_SUCCESS_FULL"]
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
