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
import pathlib

from TIPCommon.types import SingleJson
from extrahop.core.datamodels import Detection
from extrahop.core.ExtrahopParser import ExtrahopParser
from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
OAUTH_TOKEN_JSON: SingleJson = MOCK_DATA["oauth_token"]
GET_DEVICES_JSON: SingleJson = MOCK_DATA["get_devices"]
GET_DETECTION_JSON: SingleJson = MOCK_DATA["get_detection"]
INVALID_DEVICE_JSON: SingleJson = MOCK_DATA["get_device_not_found"]
INVALID_DETECTION_JSON: SingleJson = MOCK_DATA["get_detection_not_found"]
INVALID_DETECTION_ID: str = "invalid_detection_id"
INVALID_DEVICE_ID: str = "invalid_device_id"
INVALID_TOKEN: SingleJson = MOCK_DATA["invalid_oauth_token"]
INVALID_TIME: str = "invalid_time"


DETECTION: Detection = ExtrahopParser().build_detection(GET_DETECTION_JSON)
DEVICE: Detection = ExtrahopParser().build_device(GET_DEVICES_JSON[0])


class DetectionNotFoundError(Exception):
    """Accessed Detection ID cannot be found"""


class DeviceNotFoundError(Exception):
    """Accessed Device ID cannot be found"""
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
