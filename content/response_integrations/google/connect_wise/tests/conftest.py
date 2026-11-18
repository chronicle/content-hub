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
from typing import TYPE_CHECKING

import pytest
import soar_sdk  # noqa: F401

from connect_wise.core import ConnectWiseManager

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@pytest.fixture(name="load_config")
def fixture_load_config() -> SingleJson:
    """Load integration configuration from config.json file and return it as dict."""
    config_path = pathlib.Path(__file__).parent / "config.json"
    config: SingleJson = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "company_url": config["Api Root"],
        "company_name": config["Company Name"],
        "public_key": config["Public Key"],
        "private_key": config["Private Key"],
        "client_id": config["Client Id"],
    }


@pytest.fixture(name="api_manager")
def fixture_manager(
    load_config: SingleJson,
) -> ConnectWiseManager.ConnectWiseManager:
    return ConnectWiseManager.ConnectWiseManager(**load_config)
