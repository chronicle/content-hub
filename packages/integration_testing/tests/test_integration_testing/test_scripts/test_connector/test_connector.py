# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from integration_testing.common import (
    INGEST_ALERT_AS_OVERFLOW_SETTINGS,
    set_is_test_run_to_true,
)
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.set_meta import set_metadata

from .mock_connector import MockConnector

if TYPE_CHECKING:
    from soar_sdk.OverflowManager import OverflowAlertDetails

    from integration_testing.platform.script_output import MockConnectorOutput


@set_metadata
def test_mock_connector_output(connector_output: MockConnectorOutput) -> None:
    connector: MockConnector = MockConnector()
    expected_alert: AlertInfo = AlertInfo()
    expected_alert.environment = "environment"
    expected_alert.device_product = "product"
    expected_alert.rule_generator = "rule"

    connector.set_alert_to_ingest(expected_alert)
    connector.start()

    assert connector_output.report is not None

    alerts: list[AlertInfo] = connector_output.report.json_output.alerts
    assert len(alerts) == 1

    alert: AlertInfo = alerts[0]
    assert alert.environment == expected_alert.environment
    assert alert.device_product == expected_alert.device_product
    assert alert.rule_generator == expected_alert.rule_generator


@set_metadata(external_context=MockExternalContext([INGEST_ALERT_AS_OVERFLOW_SETTINGS]))
def test_mock_connector_overflow_output(connector_output: MockConnectorOutput) -> None:
    connector: MockConnector = MockConnector()
    alert: AlertInfo = AlertInfo()
    alert.environment = "environment"
    alert.device_product = "product"
    alert.rule_generator = "rule"

    connector.set_alert_to_ingest(alert)
    connector.start()

    assert connector_output.report is not None

    overflow_alerts: list[OverflowAlertDetails] = (
        connector_output.report.json_output.overflow_alerts
    )
    assert len(overflow_alerts) == 1

    overflow_alert: OverflowAlertDetails = overflow_alerts[0]
    assert overflow_alert.environment == alert.environment
    assert overflow_alert.product == alert.device_product
    assert overflow_alert.alert_name == alert.rule_generator


@set_metadata
def test_is_test_run_defaults_to_false() -> None:
    connector: MockConnector = MockConnector()

    assert not connector.is_test_run


@set_metadata
def test_is_test_run_is_set_to_true() -> None:
    set_is_test_run_to_true()
    connector: MockConnector = MockConnector()

    assert connector.is_test_run
