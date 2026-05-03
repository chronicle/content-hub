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
import json
import pathlib
from typing import Any, Generator
from unittest.mock import MagicMock
import pytest

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: dict = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


@dataclasses.dataclass
class LegacyActionOutput:
    output_message: str | None = None
    result_value: bool | str | None = None
    status: str | None = None
    is_success: bool = False

    def set_output(
        self,
        output_message: str,
        result_value: bool | str,
        status: str = "COMPLETED",
    ) -> None:
        """Set output values."""
        self.output_message = output_message
        self.result_value = result_value
        self.status = status
        self.is_success = result_value in [True, "true"]


@pytest.fixture
def action_output() -> Generator[LegacyActionOutput, Any, None]:
    yield LegacyActionOutput()


@dataclasses.dataclass
class LegacyJsonResults:
    json_results: list | dict = dataclasses.field(default_factory=list)

    def set_json_results(self, json_data: list | dict) -> None:
        self.json_results = json_data


@pytest.fixture
def json_results() -> Generator[LegacyJsonResults, Any, None]:
    yield LegacyJsonResults()


@pytest.fixture(autouse=True)
def mock_siemplify(
    monkeypatch: pytest.MonkeyPatch,
    action_output: LegacyActionOutput,  # pylint: disable=redefined-outer-name
    json_results: LegacyJsonResults,  # pylint: disable=redefined-outer-name
) -> Generator[MagicMock, Any, None]:
    """Mock Siemplify API."""
    mock_api = MagicMock()
    mock_api.LOGGER = MagicMock()

    mock_api.result = MagicMock()
    mock_api.result.add_result_json.side_effect = json_results.set_json_results
    mock_api.result.add_data_table = MagicMock()
    mock_api.result.add_entity_table = MagicMock()

    mock_api.get_configuration.return_value = CONFIG
    mock_api.target_entities = []
    mock_api.end.side_effect = action_output.set_output

    actions = ["EnrichEntities"]
    for action in actions:
        monkeypatch.setattr(
            f"Integrations.AnomaliThreatStream.ActionsScripts.{action}.SiemplifyAction",
            lambda: mock_api,
        )

        def mock_extract_conf_param(siemplify, provider_name, param_name, **kwargs):
            _ = siemplify
            _ = provider_name
            default_value = kwargs.get("default_value")
            return CONFIG.get(param_name, default_value)

        monkeypatch.setattr(
            f"Integrations.AnomaliThreatStream.ActionsScripts.{action}"
            ".extract_configuration_param",
            mock_extract_conf_param,
        )

        def mock_extract_action_param(siemplify, param_name, **kwargs):
            _ = siemplify
            default_value = kwargs.get("default_value")
            if hasattr(mock_api, "action_params"):
                return mock_api.action_params.get(param_name, default_value)
            return default_value

        monkeypatch.setattr(
            f"Integrations.AnomaliThreatStream.ActionsScripts.{action}"
            ".extract_action_param",
            mock_extract_action_param,
        )

    yield mock_api
