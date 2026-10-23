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

import dataclasses
import json
import pathlib
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest

from url_scan_io.tests.core.session import UrlScanIoSession
from url_scan_io.tests.core.url_scan_io import UrlScanIo


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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

    def set_output(
        self,
        output_message: str,
        result_value: bool | str,
        status: str = "COMPLETED"
    ) -> None:
        """Mock implementation of siemplify.end()"""
        self.output_message = output_message
        self.result_value = result_value
        self.status = status
        self.is_success = result_value in [True, "true"]


@pytest.fixture
def action_output() -> Generator[LegacyActionOutput, Any, None]:
    """Fixture providing an instance of LegacyActionOutput."""
    yield LegacyActionOutput()


@dataclasses.dataclass
class LegacyJsonResults:
    """
    Local replacement for MockJsonResults.
    Captures data from siemplify.result.add_result_json().
    """
    json_results: list | dict = dataclasses.field(default_factory=list)

    def set_json_results(self, json_data: list | dict) -> None:
        """Mock implementation of siemplify.result.add_result_json()"""
        self.json_results = json_data


@pytest.fixture
def json_results() -> Generator[LegacyJsonResults, Any, None]:
    """Fixture providing an instance of LegacyJsonResults."""
    yield LegacyJsonResults()


@pytest.fixture(autouse=True)
# pylint: disable=redefined-outer-name
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,
    json_results: LegacyJsonResults,
) -> Generator[MagicMock, Any, None]:
    """
    (autouse=True)
    Fully mocks the SiemplifyAction object for legacy scripts
    that import it directly.
    """
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()

    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results
    mock_api.result.add_data_table = MagicMock()
    mock_api.result.add_entity_link = MagicMock()
    mock_api.result.add_attachment = MagicMock()

    mock_api.get_configuration.return_value = CONFIG
    mock_api.target_entities = []
    mock_api.end.side_effect = action_output.set_output

    actions = ["SearchForScans", "UrlCheck"]
    for action in actions:
        monkeypatch.setattr(
            f"url_scan_io.actions.{action}.SiemplifyAction",
            lambda: mock_api,
        )

    def mock_extract_conf_param(
        siemplify: Any,
        provider_name: str,
        **kwargs,
    ) -> Any:
        """
        Mock implementation of extract_configuration_param
        that respects is_mandatory and default_value.
        """
        _ = siemplify
        _ = provider_name
        param_name = kwargs.get("param_name")
        default_value = kwargs.get("default_value")

        val = CONFIG.get(param_name)
        if val is None and default_value is not None:
            return default_value
        return val

    def mock_extract_action_param(
        siemplify: Any,
        param_name: str,
        **kwargs,
    ) -> Any:
        _ = siemplify
        default_value = kwargs.get("default_value")
        if hasattr(mock_api, "action_params"):
            val = mock_api.action_params.get(param_name)
            if val is not None:
                return val

        return default_value

    monkeypatch.setattr(
        "url_scan_io.actions."
        "SearchForScans.extract_configuration_param",
        mock_extract_conf_param
    )

    monkeypatch.setattr(
        "url_scan_io.actions."
        "SearchForScans.extract_action_param",
        mock_extract_action_param
    )

    yield mock_api  # pylint: disable=W0101


@pytest.fixture
def mock_data() -> dict[str, Any]:
    """
    Loads mock API response data from the JSON file.
    """
    mock_data_path = pathlib.Path(
        __file__
    ).parent / "mock_data.json"
    return json.loads(mock_data_path.read_text(encoding="utf-8"))


@pytest.fixture
def url_scan_product() -> Generator[UrlScanIo, Any, None]:
    """
    Provides an instance of the mock UrlScanIo product (our mock database).
    """
    yield UrlScanIo()


@pytest.fixture(autouse=True)
def script_session(  # pylint: disable=redefined-outer-name
    monkeypatch: pytest.MonkeyPatch,
    url_scan_product: UrlScanIo,
    mock_data: dict[str, Any],
) -> None:
    """
    (autouse=True)
    The core fixture that patches the requests.Session used by UrlScanManager.
    """
    session = UrlScanIoSession(url_scan_product, mock_data)

    monkeypatch.setattr(
        "url_scan_io.core.UrlScanManager.requests.Session",
        lambda: session,
    )
