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

from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.base.action import ExecutionState

from ...core.ServiceDeskPlusManagerV3 import ServiceDeskPlusV3Exception
from ...actions.CreateAlertRequest import (
    main as create_alert_request_main,
)
from ...actions.CreateAlertRequest import (
    ExecutionScope,
)
from ...tests.common import CONFIG_PATH, REQUEST
from ...tests.core.product import ServiceDeskPlusV3
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

OUTPUT_MESSAGE: str = "Successfully created ServiceDesk Plus request"
FAILED_OUTPUT_MESSAGE: str = "Failed to create ServiceDesk Plus requests."
CASE_OUTPUT_MESSAGE: str = (
    "Successfully created ServiceDesk Plus requests for all alerts."
)


class AlertMock:
    def __init__(
        self,
        external_id: str,
        identifier: str,
        name: str = "mock_alert_name",
    ) -> None:
        self.external_id: str = external_id
        self.identifier: str = identifier
        self.name: str = name


@set_metadata(
    parameters={
        "Subject": "Test Subject",
        "Requester": "Test Requester",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_create_alert_request_success(
    action_output: MockActionOutput,
    product: ServiceDeskPlusV3,
    monkeypatch,
) -> None:
    class MockCase:
        environment: str = "mock_env"

    class MockAlert:
        name: str = "mock_alert_name"
        external_id: str = "mock_external_id"
        identifier: str = "mock_identifier"

    monkeypatch.setattr(SiemplifyAction, "case", property(lambda self: MockCase()))
    monkeypatch.setattr(
        SiemplifyAction, "current_alert", property(lambda self: MockAlert())
    )
    monkeypatch.setattr(
        SiemplifyAction,
        "get_configuration",
        lambda self, provider_name: {"Api Root": "/api/v3", "Api Key": "mock_key"},
    )

    product.add_request(REQUEST)
    create_alert_request_main()

    assert action_output.results.output_message == OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Subject": "FailSubject",
        "Requester": "Test Requester",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_create_alert_request_failed(
    action_output: MockActionOutput,
) -> None:
    create_alert_request_main()
    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE


@set_metadata(
    parameters={
        "Subject": "Test Subject",
        "Requester": "Test Requester",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_create_alert_request_case_scope_success(
    action_output: MockActionOutput,
    product: ServiceDeskPlusV3,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SiemplifyAction,
        "execution_scope",
        property(lambda self: ExecutionScope.Case, lambda self, v: None),
        raising=False,
    )

    class MockCase:
        def __init__(self):
            self.alerts: list[AlertMock] = [
                AlertMock("ext_id_1", "ident_1"),
                AlertMock("ext_id_2", "ident_2"),
            ]

    monkeypatch.setattr(
        SiemplifyAction, "case", property(lambda self: MockCase()), raising=False
    )

    monkeypatch.setattr(
        SiemplifyAction,
        "get_configuration",
        lambda self, provider_name: {"Api Root": "/api/v3", "Api Key": "mock_key"},
    )

    product.add_request(REQUEST)

    create_alert_request_main()

    assert action_output.results.output_message == CASE_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
