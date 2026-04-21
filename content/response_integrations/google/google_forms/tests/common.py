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
import pathlib

from TIPCommon.types import SingleJson

from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)

INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent

DEFAULT_SA: str = (
    "{\n"
    '  "type": "service_account",\n'
    '  "project_id": "project",\n'
    '  "private_key_id": "c9",\n'
    '  "private_key": "-----BEGIN PRIVATE KEY-----key-----'
    'END PRIVATE KEY-----",\n'
    '  "client_email": "email@domain.iam.gserviceaccount.com",\n'
    '  "client_id": "id",\n'
    '  "auth_uri": "https://accounts.google.com/o/oauth2/auth",\n'
    '  "token_uri": "https://oauth2.googleapis.com/token",\n'
    '  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/'
    'certs",\n'
    '  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/'
    'x509/project.iam.gserviceaccount.com",\n'
    '  "universe_domain": "googleapis.com"\n'
    "}"
)
