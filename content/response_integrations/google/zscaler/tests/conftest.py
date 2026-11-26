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

import dataclasses
import importlib
import json
import pathlib
import pkgutil
import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
import soar_sdk

pytest_plugins = ("integration_testing.conftest",)

sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from TIPCommon.base.utils import CreateSession  # noqa: E402

from zscaler.core import auth, base_action  # noqa: E402
from zscaler.core.data_models import IntegrationParameters  # noqa: E402
from zscaler.tests.core.session import ZscalerSession  # noqa: E402
from zscaler.tests.core.zscaler import Zscaler  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@dataclasses.dataclass
class LegacyActionOutput:
    """
    Local replacement for MockActionOutput.
    Captures the output from siemplify.end().
    """

    output_message: str | None = None
    result_value: bool | str | None = None
    status: str | None = None
    is_success: bool = False

    def set_output(self, *args: Any, **kwargs: Any) -> None:
        """Mock implementation of siemplify.end()"""
        if args:
            self.output_message = args[0]
            self.result_value = args[1] if len(args) > 1 else False
            self.status = args[2] if len(args) > 2 else "COMPLETED"
        else:
            self.output_message = kwargs.get("output_message") or kwargs.get("message")
            self.result_value = kwargs.get("result_value")
            self.status = kwargs.get("status")

        self.is_success = self.result_value in [True, "true"]


@pytest.fixture
def action_output() -> Iterator[LegacyActionOutput]:
    """Fixture providing an instance of LegacyActionOutput."""
    yield LegacyActionOutput()


@dataclasses.dataclass
class LegacyJsonResults:
    """
    Local replacement for MockJsonResults.
    Captures data from siemplify.result.add_result_json().
    """

    json_results_str: str = "[]"

    def set_json_results(self, json_data: list | dict) -> None:
        """Mock implementation of siemplify.result.add_result_json()"""
        self.json_results_str = json.dumps(json_data)


@pytest.fixture
def json_results() -> Iterator[LegacyJsonResults]:
    """Fixture providing an instance of LegacyJsonResults."""
    yield LegacyJsonResults()


@pytest.fixture(autouse=True)
# pylint: disable=redefined-outer-name
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
) -> Iterator[MagicMock]:
    """
    (autouse=True)
    Fully mocks the SiemplifyAction object for legacy scripts
    that import it directly.
    """
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()

    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results
    mock_api.result.add_entity_table = MagicMock()

    mock_api.get_configuration.return_value = CONFIG
    mock_api.target_entities = []  # Default, tests can override
    mock_api.end.side_effect = action_output.set_output
    mock_api.execution_deadline_unix_time_ms = 2000000000000  # Year 2033

    try:
        monkeypatch.setattr(
            "zscaler.actions.AddToWhitelist.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "zscaler.actions.AddToBlacklist.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    try:
        monkeypatch.setattr(
            "zscaler.actions.LookupEntity.SiemplifyAction",
            lambda: mock_api,
        )
    except AttributeError:
        pass

    def mock_extract_param(
        siemplify: Any,  # noqa: ANN401
        provider_name: str,
        **kwargs: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """
        Mock implementation of extract_configuration_param
        that respects is_mandatory and default_value.
        """
        _ = siemplify
        _ = provider_name
        param_name = kwargs.get("param_name")
        is_mandatory = kwargs.get("is_mandatory", False)
        default_value = kwargs.get("default_value")

        if default_value is not None:
            return CONFIG.get(param_name, default_value)
        if is_mandatory:
            return CONFIG[param_name]
        return CONFIG.get(param_name)

    try:
        monkeypatch.setattr(
            "zscaler.actions.LookupEntity."
            "extract_configuration_param",
            mock_extract_param,
        )
    except AttributeError:
        pass

    monkeypatch.setattr(
        "TIPCommon.base.action.base_action.create_soar_action",
        lambda: mock_api,
    )

    yield mock_api


@pytest.fixture
def mock_data() -> dict[str, Any]:
    """
    Loads mock API response data from the JSON file.
    """
    mock_data_path = pathlib.Path(__file__).parent / "mock_data.json"
    return json.loads(mock_data_path.read_text(encoding="utf-8"))


@pytest.fixture
def zscaler_product() -> Iterator[Zscaler]:
    """
    Provides an instance of the mock Zscaler product (our mock database).
    """
    yield Zscaler()


@pytest.fixture(autouse=True)
def script_session(  # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
    zscaler_product: Zscaler,
    mock_data: dict[str, Any],
) -> Iterator[ZscalerSession]:
    """Patch the requests.Session used by ZscalerManager."""
    session = ZscalerSession(zscaler_product)
    zscaler_product.mock_data = mock_data

    monkeypatch.setattr(
        base_action,
        "build_auth_params",
        lambda _soar_sdk_object: IntegrationParameters(
            api_root="https://admin.zscalertwo.net",
            login_id="dummy@test.com",
            api_key="dummy_key",
            password="dummy_password",
            verify_ssl=False,
        ),
    )

    monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
    monkeypatch.setattr(
        auth.AuthenticatedSession,
        "_obfuscate_api_key",
        lambda _self, _api_key, _timestamp: zscaler_product.expected_api_key,
    )
    yield session

