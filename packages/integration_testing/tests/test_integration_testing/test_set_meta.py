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

import json
import pathlib
from typing import TYPE_CHECKING

from soar_sdk.OverflowManager import OverflowManager
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo, ConnectorContext
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.data_models import DatabaseContextType

from integration_testing.common import DEFAULT_OVERFLOW_SETTINGS, create_entity
from integration_testing.platform.external_context import (
    ExternalContextRow,
    MockExternalContext,
)
from integration_testing.set_meta import set_metadata

from .test_scripts.test_action.mock_action import MockAction
from .test_scripts.test_connector.mock_connector import MockConnector
from .test_scripts.test_job.mock_job import MockJob

if TYPE_CHECKING:
    from TIPCommon.types import Entity, SingleJson

BASE_DIR: pathlib.Path = pathlib.Path(__file__).parent
CONFIG_FILE: pathlib.Path = BASE_DIR / "mock.json"
JOB_DEF: pathlib.Path = BASE_DIR / "mock_job_def.jobdef"
CONNECTOR_DEF: pathlib.Path = BASE_DIR / "mock_connector_def.connectordef"


class TestsGeneral:
    def test_external_context_is_passed_to_param(self) -> None:
        og_external_context: MockExternalContext = MockExternalContext()

        @set_metadata(
            integration_config_file_path=CONFIG_FILE,
            external_context=og_external_context,
        )
        def do_test(external_context: MockExternalContext) -> None:
            assert id(og_external_context) == id(external_context)

        do_test()  # pylint: disable=no-value-for-parameter


class TestAction:
    def test_can_be_called_without_parameters(self) -> None:
        @set_metadata()
        def do_test() -> None:
            action: MockAction = MockAction()

            action.run()

        do_test()

    def test_can_be_called_without_parenthesis(self) -> None:
        @set_metadata
        def do_test() -> None:
            action: MockAction = MockAction()

            action.run()

        do_test()

    def test_script_parameters(self) -> None:
        parameters: dict[str, str] = {"Param": "Value"}

        @set_metadata(parameters=parameters, integration_config_file_path=CONFIG_FILE)
        def do_test() -> None:
            action: MockAction = MockAction()

            action_params: SingleJson = action.get_action_parameters()

            assert action_params == parameters

        do_test()

    def test_input_context(self) -> None:
        expected_input_context: SingleJson = {
            "parameters": {"Param": "Value"},
            "case_id": 31,
            "environment": "env",
        }

        @set_metadata(
            input_context=expected_input_context,
            integration_config_file_path=CONFIG_FILE,
        )
        def do_test() -> None:
            action: MockAction = MockAction()

            input_context: SingleJson = action.get_input_context()

            assert input_context["parameters"] == expected_input_context["parameters"]
            assert input_context["case_id"] == expected_input_context["case_id"]
            assert input_context["environment"] == expected_input_context["environment"]

        do_test()

    def test_set_to_external_context(self) -> None:
        @set_metadata(
            integration_config_file_path=CONFIG_FILE,
            external_context=MockExternalContext(),
        )
        def do_test(external_context: MockExternalContext) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            action: MockAction = MockAction()
            action.set_external_context(context, identifier, key, expected_value)
            value: str = external_context.get_row_value(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_get_from_external_context(self) -> None:
        @set_metadata(
            integration_config_file_path=CONFIG_FILE,
            external_context=MockExternalContext(),
        )
        def do_test(external_context: MockExternalContext) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            external_context.set_row_value(context, identifier, key, expected_value)
            action: MockAction = MockAction()
            value: str = action.get_external_context(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_integration_config(self) -> None:
        @set_metadata(integration_config_file_path=CONFIG_FILE)
        def do_test() -> None:
            expected_config = json.loads(CONFIG_FILE.read_text())
            action: MockAction = MockAction()
            integration_config: SingleJson = action.get_integration_configuration()

            assert expected_config == integration_config

        do_test()

    def test_setting_entities_(self) -> None:
        entity: Entity = create_entity("8.8.8.8", EntityTypesEnum.ADDRESS)

        @set_metadata(entities=[entity])
        def do_test() -> None:
            action: MockAction = MockAction()

            entities: list[Entity] = action.get_entities()

            assert len(entities) == 1
            assert entity in entities

        do_test()


class TestJob:
    def test_can_be_called_without_parameters(self) -> None:
        @set_metadata()
        def do_test() -> None:
            job: MockJob = MockJob()

            job.start()

        do_test()

    def test_can_be_called_without_parenthesis(self) -> None:
        @set_metadata
        def do_test() -> None:
            job: MockJob = MockJob()

            job.start()

        do_test()

    def test_script_parameters(self) -> None:
        parameters: dict[str, str] = {"Param name": "Param value"}

        @set_metadata(parameters=parameters)
        def do_test() -> None:
            job: MockJob = MockJob()

            job_params: SingleJson = job.get_job_parameters()

            assert job_params == parameters

        do_test()

    def test_script_parameters_using_base_class_extraction(self) -> None:
        parameters: dict[str, str] = {"Username": "Hello World", "Password": "123"}

        @set_metadata(parameters=parameters, job_def_file_path=JOB_DEF)
        def do_test() -> None:
            job: MockJob = MockJob()

            job.set_parameters()

            assert parameters["Username"] == job.params.username
            assert parameters["Password"] == job.params.password

        do_test()

    def test_script_params_using_base_class_extraction_without_job_def(self) -> None:
        @set_metadata(parameters={"Username": "Hello World", "Password": "123"})
        def do_test() -> None:
            job: MockJob = MockJob()

            job.set_parameters()

            assert hasattr(job.params, "username")
            assert hasattr(job.params, "password")

        do_test()

    def test_input_context(self) -> None:
        expected_input_context: SingleJson = {
            "parameters": {"Param": "Value"},
            "unique_identifier": "1234",
            "job_api_key": "5678",
        }

        @set_metadata(input_context=expected_input_context)
        def do_test() -> None:
            job: MockJob = MockJob()

            input_context: SingleJson = job.get_input_context()

            assert input_context["parameters"] == expected_input_context["parameters"]
            assert input_context["unique_identifier"] == expected_input_context["unique_identifier"]
            assert input_context["job_api_key"] == expected_input_context["job_api_key"]

        do_test()

    def test_set_to_external_context(self) -> None:
        @set_metadata(external_context=MockExternalContext())
        def do_test(external_context: MockExternalContext[str]) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            job: MockJob = MockJob()
            job.set_external_context(context, identifier, key, expected_value)
            value: str = external_context.get_row_value(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_get_from_external_context(self) -> None:
        @set_metadata(external_context=MockExternalContext())
        def do_test(external_context: MockExternalContext[str]) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            external_context.set_row_value(context, identifier, key, expected_value)
            job: MockJob = MockJob()
            value: str = job.get_external_context(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_integration_config(self) -> None:
        @set_metadata(integration_config_file_path=CONFIG_FILE)
        def do_test() -> None:
            expected_config = json.loads(CONFIG_FILE.read_text())
            job: MockJob = MockJob()

            integration_config: SingleJson = job.get_integration_configuration()

            assert expected_config == integration_config

        do_test()


class TestConnector:
    def test_can_be_called_without_parameters(self) -> None:
        @set_metadata()
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            connector.start()

        do_test()

    def test_can_be_called_without_parenthesis(self) -> None:
        @set_metadata
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            connector.start()

        do_test()

    def test_script_parameters(self) -> None:
        parameters: dict[str, str] = {"Param name": "Param value"}

        @set_metadata(parameters=parameters)
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            connector_params: SingleJson = connector.get_connector_parameters()

            assert connector_params == parameters

        do_test()

    def test_script_parameters_using_base_class_extraction(self) -> None:
        parameters: dict[str, str] = {"Username": "Hello World", "Password": "123"}

        @set_metadata(parameters=parameters, connector_def_file_path=CONNECTOR_DEF)
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            connector.start()

            assert parameters["Username"] == connector.params.username
            assert parameters["Password"] == connector.params.password

        do_test()

    def test_script_params_using_base_class_extraction_without_connector_def(
        self,
    ) -> None:
        @set_metadata(parameters={"Username": "Hello World", "Password": "123"})
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            connector.start()

            assert hasattr(connector.params, "username")
            assert hasattr(connector.params, "password")

        do_test()

    def test_input_context(self) -> None:
        expected_input_context: SingleJson = {
            "connector_context": ConnectorContext(
                vault_settings={"param_name": "Param", "param_value": "Value"},
                connector_info={
                    "description": "1234",
                    "params": {"param_name": "Param", "param_value": "Value"},
                },
            ),
        }
        expected_context: ConnectorContext = expected_input_context["connector_context"]

        @set_metadata(input_context=expected_input_context)
        def do_test() -> None:
            connector: MockConnector = MockConnector()

            input_context: ConnectorContext = connector.get_input_context()

            assert input_context.vault_settings == expected_context.environment_api_key
            assert input_context.connector_info.params == expected_context.connector_info.params
            assert (
                input_context.connector_info.description
                == expected_context.connector_info.description
            )

        do_test()

    def test_set_to_external_context(self) -> None:
        @set_metadata(external_context=MockExternalContext())
        def do_test(external_context: MockExternalContext[str]) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            connector: MockConnector = MockConnector()
            connector.set_external_context(context, identifier, key, expected_value)
            value: str = external_context.get_row_value(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_get_from_external_context(self) -> None:
        @set_metadata(external_context=MockExternalContext())
        def do_test(external_context: MockExternalContext) -> None:
            context = DatabaseContextType.GLOBAL
            identifier = "identifier"
            key = "key"
            expected_value = "Test Value"

            external_context.set_row_value(context, identifier, key, expected_value)
            connector: MockConnector = MockConnector()
            value: str = connector.get_external_context(context, identifier, key)

            assert value == expected_value

        do_test()  # pylint: disable=no-value-for-parameter

    def test_overflow_is_saved_to_external_context(self) -> None:
        @set_metadata(external_context=MockExternalContext([DEFAULT_OVERFLOW_SETTINGS]))
        def do_test(external_context: MockExternalContext) -> None:
            connector: MockConnector = MockConnector()
            overflow_key: str = "|environment|product|rule"
            expected_row: ExternalContextRow[str] = ExternalContextRow(
                context_type=DatabaseContextType.CONNECTOR,
                identifier=None,
                property_key=OverflowManager.OVERFLOW_DATA_KEY,
                property_value=(
                    "{\n"
                    f'    "{overflow_key}": {{\n'
                    '        "digestion_times": [\n'
                    "            1717086290652\n"
                    "        ],\n"
                    '        "last_notification_time": 0\n'
                    "    }\n"
                    "}"
                ),
            )
            alert: AlertInfo = AlertInfo()
            alert.environment = "environment"
            alert.device_product = "product"
            alert.rule_generator = "rule"

            connector.set_alert_to_ingest(alert)
            connector.start()
            overflow_context_value: str = external_context.get_row_value(
                context_type=expected_row.context_type,
                identifier=expected_row.identifier,
                property_key=expected_row.property_key,
            )
            overflow_context_json: SingleJson = json.loads(overflow_context_value)

            assert "digestion_times" in overflow_context_json[overflow_key]
            assert "last_notification_time" in overflow_context_json[overflow_key]
            assert overflow_context_json[overflow_key]["last_notification_time"] == 0

        do_test()  # pylint: disable=no-value-for-parameter
