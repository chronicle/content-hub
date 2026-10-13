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
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout
import json
import pathlib
from unittest.mock import MagicMock

import pytest
import requests

from azure_ad_identity_protection.core import (
    AzureADIdentityProtectionManager,
)


def get_json_file_content(path: pathlib.Path) -> dict:
    """Loads JSON file content."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = get_json_file_content(CONFIG_PATH)


@pytest.fixture
def aad_ip_manager(monkeypatch: pytest.MonkeyPatch) -> AzureADIdentityProtectionManager:
    """
    Provides a properly mocked AzureADIdentityProtectionManager instance
    for the URL validation tests.
    """
    mock_session_instance: MagicMock = MagicMock(spec=requests.Session)
    mock_session_instance.headers = {}

    mock_response: MagicMock = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": [], "access_token": "mock_token"}
    mock_response.raise_for_status.return_value = None

    mock_session_instance.get.return_value = mock_response
    mock_session_instance.post.return_value = mock_response

    monkeypatch.setattr(requests, "session", lambda: mock_session_instance)

    monkeypatch.setattr(
        AzureADIdentityProtectionManager, "set_auth_token", lambda *args: None
    )

    manager: AzureADIdentityProtectionManager = AzureADIdentityProtectionManager(
        client_id=CONFIG.get("Client ID"),
        client_secret=CONFIG.get("Client Secret"),
        tenant_id=CONFIG.get("Tenant ID"),
        verify_ssl=CONFIG.get("Verify SSL"),
        api_root=CONFIG.get("API Root"),
        login_api_root=CONFIG.get("Login API Root"),
    )

    manager.session = mock_session_instance
    yield manager
