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

import copy
import dataclasses
import json
import pathlib
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from azure_active_directory.core.AzureADManager import (
    AzureADManager,
)
from azure_active_directory.core.AzureADParser import AzureADParser
from azure_active_directory.tests.core.product import AzureADProduct
from azure_active_directory.tests.core.session import AzureADSession

_ACTION_MODULE_PREFIX = "azure_active_directory.actions"

_PATCHED_ACTIONS = [
    "GetManagerContactDetails",
    "EnrichUser",
    "ListGroups",
    "Ping",
    "AddUserToGroup",
    "DisableAccount",
    "EnableAccount",
    "EnrichHost",
    "ForcePasswordUpdate",
    "IsUserInGroup",
    "ListMembersInGroup",
    "ListUsers",
    "ListUsersGroupsMembership",
    "RemoveUserFromTheGroup",
    "ResetUserPassword",
    "RevokeUserSession",
]

def get_json_file_content(path: pathlib.Path) -> dict:
    """Loads JSON file content."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"

MOCK_DATA_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"

CONFIG: dict = get_json_file_content(CONFIG_PATH)

MOCK_RESPONSES: dict = get_json_file_content(MOCK_DATA_PATH)

@dataclasses.dataclass(unsafe_hash=True)
class MockSiemplifyEntity:
    identifier: str
    entity_type: str
    additional_properties: dict[str, Any] = dataclasses.field(
        default_factory=dict,
        hash=False
    )
    is_enriched: bool = dataclasses.field(default=False, hash=False)
    is_suspicious: bool = dataclasses.field(default=False, hash=False)

@dataclasses.dataclass
class LegacyActionOutput:
    """Class to hold legacy action output data."""
    output_message: str | None = None
    result_value: bool | str | None = None
    status: str | int | None = None

    def set_output(
        self,
        output_message: str,
        result_value: bool | str,
        status: str | int = EXECUTION_STATE_COMPLETED,
    ):
        """Sets the action output values."""
        self.output_message = output_message
        self.result_value = result_value
        self.status = status

@dataclasses.dataclass
class LegacyJsonResults:
    """Class to hold legacy JSON results."""
    json_results: list[Any] | dict[str, Any] = dataclasses.field(
        default_factory=list
    )

    def set_json_results(self, json_data: list[Any] | dict[str, Any]):
        """Sets the JSON results."""
        self.json_results = json_data

@pytest.fixture
def mock_data() -> dict:
    """Provides a deep copy of the mock data for isolation."""
    return copy.deepcopy(MOCK_RESPONSES)

@pytest.fixture
def product(mock_data: dict) -> AzureADProduct:
    """Fixture for AzureADProduct."""
    prod = AzureADProduct()

    if "user_details" in mock_data:
        user_data = mock_data["user_details"]
        if isinstance(user_data, list):
            for user in user_data:
                upn = user.get("userPrincipalName")
                if upn:
                    prod.add_user(upn, user)
        elif isinstance(user_data, dict):
            upn = user_data.get("userPrincipalName")
            if upn:
                prod.add_user(upn, user_data)

    if "user_registration_details" in mock_data:
        value = mock_data["user_registration_details"].get("value", [])
        for detail in value:
            upn = detail.get("userPrincipalName")
            if upn:
                prod.add_user_registration_details(upn, detail)

    return prod

@pytest.fixture
def azure_ad_product(product: AzureADProduct) -> AzureADProduct:
    """Fixture for AzureADProduct."""
    return product

@pytest.fixture
def action_output() -> LegacyActionOutput:
    """Fixture for LegacyActionOutput."""
    return LegacyActionOutput()

@pytest.fixture
def json_results() -> LegacyJsonResults:
    """Fixture for LegacyJsonResults."""
    return LegacyJsonResults()

@pytest.fixture(name="action_params")
def action_params_fixture() -> dict[str, Any]:
    """Fixture for action parameters."""
    return {}

@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch, product: AzureADProduct, mock_data: dict
) -> Generator[AzureADSession, Any, None]:
    """
    Patches requests.Session to use AzureADSession.
    """
    parser = AzureADParser()
    session = AzureADSession(product, raw_mock_data=mock_data, parser=parser)

    session.get = MagicMock(wraps=session.get)
    session.post = MagicMock(wraps=session.post)
    session.patch = MagicMock(wraps=session.patch)
    session.delete = MagicMock(wraps=session.delete)
    session.request = MagicMock(wraps=session.request)

    monkeypatch.setattr("requests.Session", lambda: session)
    monkeypatch.setattr(
        "azure_active_directory.core.AzureADManager."
        "requests.Session",
        lambda: session,
    )
    return session

@pytest.fixture
def azure_ad_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[AzureADManager, Any, None]:
    """
    Fixture for AzureADManager.
    """
    mock_session_instance = MagicMock()
    mock_session_instance.headers = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": []}
    mock_response.raise_for_status.return_value = None

    mock_session_instance.get.return_value = mock_response
    mock_session_instance.post.return_value = mock_response
    mock_session_instance.patch.return_value = mock_response
    mock_session_instance.delete.return_value = mock_response

    monkeypatch.setattr(requests, "Session", lambda: mock_session_instance)
    monkeypatch.setattr(
        AzureADManager, "generate_token", lambda *args: "mock_access_token"
    )

    manager = AzureADManager(
        client_id=CONFIG["Client ID"],
        client_secret=CONFIG["Secret ID"],
        tenant=CONFIG["Tenant"],
        verify_ssl=CONFIG["Verify SSL"],
        api_root=CONFIG.get("API Root"),
        login_api_root=CONFIG.get("Login API Root"),
    )

    manager.session = mock_session_instance
    yield manager

@pytest.fixture(autouse=True)
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
    action_params: dict[str, Any],
) -> Generator[MagicMock, Any, None]:
    """
    Mocks SiemplifyAction and parameter extraction functions for every action.
    """
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()
    mock_api.target_entities = []
    mock_api.execution_deadline_unix_time_ms = 9999999999999
    mock_api.parameters = action_params

    def mock_update_entities(_entities_to_update: list[Any]):
        pass

    mock_api.update_entities.side_effect = mock_update_entities

    def mock_end(
        output_message: str,
        result_value: bool | str,
        status: str | int = EXECUTION_STATE_COMPLETED,
    ):
        action_output.set_output(output_message, result_value, status)

    mock_api.end.side_effect = mock_end
    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results

    def mock_extract_action_param(*args, **kwargs):
        name = kwargs.get("param_name") or (args[1] if len(args) > 1 else None)
        default = kwargs.get("default_value")
        input_type = kwargs.get("input_type")
        value = action_params.get(name, mock_api.parameters.get(name, default))
        if input_type is not None and value is not None:
            try:
                value = input_type(value)
            except (ValueError, TypeError):
                pass
        return value

    def mock_extract_config_param(*args, **kwargs):
        name = kwargs.get("param_name") or (args[2] if len(args) > 2 else None)
        if not name and len(args) > 1:
            name = args[1]
        default = kwargs.get("default_value")
        input_type = kwargs.get("input_type")
        value = CONFIG.get(name, default)
        if input_type is not None and value is not None:
            try:
                value = input_type(value)
            except (ValueError, TypeError):
                pass
        return value

    for action_name in _PATCHED_ACTIONS:
        action_module = f"{_ACTION_MODULE_PREFIX}.{action_name}"
        monkeypatch.setattr(
            f"{action_module}.SiemplifyAction",
            lambda: mock_api,
        )
        monkeypatch.setattr(
            f"{action_module}.extract_action_param",
            mock_extract_action_param,
            raising=False,
        )
        monkeypatch.setattr(
            f"{action_module}.extract_configuration_param",
            mock_extract_config_param,
            raising=False,
        )

    yield mock_api

@pytest.fixture
def _script_session(script_session: AzureADSession) -> AzureADSession:
    """Alias for script_session (side-effect only)."""
    return script_session

@pytest.fixture
def _product(product: AzureADProduct) -> AzureADProduct:
    """Alias for product (side-effect only)."""
    return product

@pytest.fixture
def _mock_siemplify(mock_siemplify: MagicMock) -> MagicMock:
    """Alias for mock_siemplify (side-effect only)."""
    return mock_siemplify

@pytest.fixture(name="_action_params")
def _action_params_fixture(action_params: dict[str, Any]) -> dict[str, Any]:
    """Alias for action_params (side-effect only)."""
    return action_params

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
