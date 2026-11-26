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

import os

CONFIG_FILE_NAME = os.path.join(os.path.dirname(__file__), "config.json")
FILE_NAME = os.path.join(os.path.dirname(__file__), "ABC.txt")
DUMMY_CONTENT = {"status": "200"}
STATUS_CODE = 201
CREATED_STATUS = "created"
STATUS_IN_PROGRESS = "in_progress"
SUCCESS_STATUS = "succeeded"
DUMMY_CONTENT_CREATED = {"status": "201"}
ANALYSIS_ID = "c7d93465-d680-4a80-b2b3-1adca96b0525"
DETONATE_HASH = "0e8f3171993588715643b05d0015a571604d4b1c152de99707a210497305e7ec"
DETONATE_URL = "https://analyze.intezer.com"
DEFAULT_VALUE = "Default Value"
TRUSTED = "trusted"
SHA256 = "0e8f3171993588715643b05d0015a571604d4b1c152de99707a210497305e7ec"
EMAIL_FILEPATH = os.path.join(os.path.dirname(__file__), "file.eml")
ALERT_ID = "3385f4f9aec655dfac9d59d54e8ff1f12343501ebc62bf1a91ad1954bb6ae0b9"
URL_ANALYSIS_ID = "Aef96e22-e0b1-45de-b7fa-2b9596ecb922"
RESULT_URL = "/analyses/59e82c3b-9598-4e36-b6bc-c9b8416a33ae"
ALERT_SOURCE = "cs"
