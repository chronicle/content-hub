from __future__ import annotations

import pytest

from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.base.action import ExecutionState

from service_desk_plus.core.ServiceDeskPlusManager import ServiceDeskPlusManagerError
from service_desk_plus.actions.CreateAlertRequest import (
    main as create_alert_request_main,
    ExecutionScope,
)
from service_desk_plus.tests.common import CONFIG_PATH, REQUEST
from service_desk_plus.tests.core.product import ServiceDeskPlus
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

OUTPUT_MESSAGE: str = "ServiceDesk Plus request - 12345 was created."
FAILED_OUTPUT_MESSAGE: str = "Failed to create ServiceDesk Plus requests."
CASE_OUTPUT_MESSAGE: str = "Successfully created requests for alerts: 12345, 12345."


class AlertMock:
    def __init__(self, external_id, identifier):
        self.external_id: str = external_id
        self.identifier: str = identifier


@set_metadata(
    parameters={
        "Subject": "Test Subject",
        "Requester": "Test Requester",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_create_alert_request_success(
    action_output: MockActionOutput,
    product: ServiceDeskPlus,
) -> None:
    product.add_request(REQUEST)
    create_alert_request_main()

    assert action_output.results.output_message == OUTPUT_MESSAGE
    assert action_output.results.result_value == "12345"
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
    assert action_output.results.result_value is False
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
    product: ServiceDeskPlus,
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

    product.add_request(REQUEST)

    create_alert_request_main()

    assert action_output.results.output_message == CASE_OUTPUT_MESSAGE
    assert action_output.results.result_value == "12345,12345"
