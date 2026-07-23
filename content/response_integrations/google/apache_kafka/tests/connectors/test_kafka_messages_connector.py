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

from typing import TYPE_CHECKING

import pytest

from TIPCommon.exceptions import ConnectorSetupError, ParameterValidationError

from ...tests.test_constants import (
    MAX_MESSAGES_TO_FETCH,
    DEFAULT_TIMEOUT,
    SEVERITY_MAPPING_JSON_DEFAULT,
    TEST_CONSUMER_GROUP_ID,
    TEST_INITIAL_OFFSET_AS_STR,
    TEST_PARTITIONS,
    VALIDATE_JSON_FUCTION_NAME,
    VALIDATE_CSV_FUCTION_NAME,
    TEST_PARTITIONS_PARAM_VALUE,
    TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_INT,
    TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR,
    TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR_INVALID,
    TEST_PARTITIONS_PARAM_VALUE_INVALID,
    OFFSET_PARAM_NAME,
    OFFSET_PARAM_POSSIBLE_VALUES,
    VALIDATE_NON_NEGATIVE_FUCTION_NAME,
    INITIAL_OFFSET_PARAM_INVALID_VALUE,
    TEST_KAFKA_BROKERS,
    TEST_KAFKA_USERNAME,
    TEST_KAFKA_PASSWORD,
    TEST_KAFKA_CA,
    TEST_KAFKA_CLIENT_CERT,
    TEST_KAFKA_CLIENT_CERT_KEY,
    TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD,
    TEST_KAFKA_MESSAGES,
    TEST_KAFKA_OFFSETS,
    TEST_UNIQUE_ID_FIELD,
    TEST_TIMESTAMP_FIELD,
    TEST_TIMESTAMP_FORMAT,
    TEST_CASE_NAME_TEMPLATE,
    TEST_ALERT_NAME_TEMPLATE,
    TEST_SEVERITY_MAPPING_DEFAULT_DICT,
    TEST_RULE_GENERATOR_TEMPLATE,
    TEST_TOPIC,
    PREPARE_INITIAL_OFFSET_METHOD_NAME,
    FIRST_MESSAGE_INDEX,
    TEST_LAST_RUN_DATA,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ...connectors.kafka_messages_connector import (
        KafkaMessagesConnector,
    )


class TestKafkaMessagesConnector:
    """Tests for the KafkaMessagesConnector"""

    def test_init(self, connector: KafkaMessagesConnector) -> None:
        """Test the __init__ method."""
        assert connector.next_offsets == {}

    def test_validate_params_general(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test the general parameter validation within validate_params."""
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.severity_mapping_json = SEVERITY_MAPPING_JSON_DEFAULT
        mocker.patch.object(
            connector.param_validator,
            "validate_json",
            return_value={"Default": "Info"},
        )
        mocker.patch.object(
            connector.param_validator,
            "validate_positive",
            side_effect=lambda _, value, **kwargs: value,
        )

        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")
        mocker.patch.object(connector, "_validate_initial_offset")
        connector.validate_params()

        connector.param_validator.validate_positive.assert_any_call(
            "Max Messages To Fetch",
            MAX_MESSAGES_TO_FETCH,
        )
        connector.param_validator.validate_positive.assert_any_call(
            "Poll Timeout (Seconds)",
            DEFAULT_TIMEOUT,
        )
        connector.param_validator.validate_json.assert_called_once_with(
            "Severity Mapping JSON",
            SEVERITY_MAPPING_JSON_DEFAULT,
        )

    def test_validate_params_invalid_severity_mapping(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test validate_params with invalid severity mapping."""
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.severity_mapping_json = "{}"
        mocker.patch.object(
            connector.param_validator, VALIDATE_JSON_FUCTION_NAME, return_value={}
        )
        mocker.patch.object(
            connector.param_validator,
            "validate_positive",
            side_effect=lambda _, value, **kwargs: value,
        )
        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")
        mocker.patch.object(connector, "_validate_initial_offset")

        with pytest.raises(ConnectorSetupError):
            connector.validate_params()

    def test_validate_params_offset_management_error(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test validate_params for offset management when it should raise an error."""
        connector.params.consumer_group_id = TEST_CONSUMER_GROUP_ID
        connector.params.initial_offset = TEST_INITIAL_OFFSET_AS_STR
        connector.params.partitions = TEST_PARTITIONS
        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")
        mocker.patch.object(connector, "_validate_initial_offset")

        with pytest.raises(ConnectorSetupError):
            connector.validate_params()

    def test_validate_params_offset_management_pass(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test validate_params for offset management when it should pass."""
        connector.params.consumer_group_id = None
        connector.params.initial_offset = TEST_INITIAL_OFFSET_AS_STR
        connector.params.partitions = TEST_PARTITIONS

        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")
        mocker.patch.object(connector, "_validate_initial_offset")

        connector.validate_params()

    def test_validate_params_parse_partitions_success(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test the _validate_and_parse_partitions method for successful parsing."""
        mocker.patch.object(
            connector.param_validator,
            VALIDATE_CSV_FUCTION_NAME,
            return_value=TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR,
        )
        connector.params.partitions = TEST_PARTITIONS_PARAM_VALUE

        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_initial_offset")
        connector.validate_params()

        assert connector.params.partitions == TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_INT

    def test_validate_params_parse_partitions_error(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test validate_params for partition parsing error."""
        mocker.patch.object(
            connector.param_validator,
            VALIDATE_CSV_FUCTION_NAME,
            return_value=TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR_INVALID,
        )
        connector.params.partitions = TEST_PARTITIONS_PARAM_VALUE_INVALID

        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_initial_offset")

        with pytest.raises(ConnectorSetupError):
            connector.validate_params()

    @pytest.mark.parametrize(OFFSET_PARAM_NAME, OFFSET_PARAM_POSSIBLE_VALUES)
    def test_validate_params_initial_offset_pass(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
        offset: str,
    ) -> None:
        """Test the _validate_initial_offset method when it should pass."""
        mocker.patch.object(
            connector.param_validator,
            VALIDATE_NON_NEGATIVE_FUCTION_NAME,
        )
        connector.params.initial_offset = offset

        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")

        connector.validate_params()

    def test_validate_params_initial_offset_error(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test validate_params for initial offset when it should raise an error."""
        mocker.patch.object(
            connector.param_validator,
            VALIDATE_NON_NEGATIVE_FUCTION_NAME,
            side_effect=ParameterValidationError("param", "value", "message"),
        )
        connector.params.initial_offset = INITIAL_OFFSET_PARAM_INVALID_VALUE

        mocker.patch.object(connector, "_validate_general_params")
        mocker.patch.object(connector, "_validate_offset_management_params")
        mocker.patch.object(connector, "_validate_and_parse_partitions")

        with pytest.raises(ConnectorSetupError):
            connector.validate_params()

    def test_init_managers(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test the init_managers method."""
        kafka_client_mock = mocker.patch(
            "apache_kafka.connectors."
            "kafka_messages_connector.KafkaClient"
        )
        connector.params.kafka_brokers = TEST_KAFKA_BROKERS
        connector.params.use_tls_for_connection = False
        connector.params.use_saslplain_with_tls_for_connection = False
        connector.params.saslplain_username = TEST_KAFKA_USERNAME
        connector.params.saslplain_password = TEST_KAFKA_PASSWORD
        connector.params.ca_certificate_of_kafka_server = TEST_KAFKA_CA
        connector.params.client_certificate = TEST_KAFKA_CLIENT_CERT
        connector.params.client_certificate_key = TEST_KAFKA_CLIENT_CERT_KEY
        connector.params.client_certificate_key_password = (
            TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD
        )

        connector.init_managers()

        kafka_client_mock.assert_called_once()
        assert connector.manager == kafka_client_mock.return_value

    def test_get_alerts(
        self,
        connector: KafkaMessagesConnector,
        mocker: MockerFixture,
    ) -> None:
        """Test the get_alerts method."""
        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = (
            TEST_KAFKA_MESSAGES,
            TEST_KAFKA_OFFSETS,
        )
        prepare_initial_offsets_mock = mocker.patch.object(
            connector,
            PREPARE_INITIAL_OFFSET_METHOD_NAME,
        )
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.topic = TEST_TOPIC
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.consumer_group_id = None
        connector.params.initial_offset = None

        alerts = connector.get_alerts()

        prepare_initial_offsets_mock.assert_called_once()
        connector.manager.consume_messages.assert_called_once()
        assert alerts == (
            connector.manager.consume_messages.return_value[FIRST_MESSAGE_INDEX]
        )

    def test_get_alerts_with_group_id_prepares_empty_offsets(
        self,
        mocker: MockerFixture,
        connector: KafkaMessagesConnector,
    ) -> None:
        """Test the _prepare_initial_offsets method when consumer_group_id
        is provided."""
        connector.params.consumer_group_id = TEST_CONSUMER_GROUP_ID
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.initial_offset = None
        connector.params.topic = TEST_TOPIC

        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = ([], {})

        prepare_initial_offsets_spy = mocker.spy(connector, "_prepare_initial_offsets")
        connector.get_alerts()

        assert prepare_initial_offsets_spy.spy_return == {}

    def test_get_alerts_with_last_run_data_prepares_correct_offsets(
        self,
        mocker: MockerFixture,
        connector: KafkaMessagesConnector,
    ) -> None:
        """Test the _prepare_initial_offsets method when last_run_data is available."""
        connector.params.consumer_group_id = None
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.initial_offset = None
        connector.params.partitions = None
        connector.params.topic = TEST_TOPIC

        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = ([], {})
        connector.context.last_run_data = TEST_LAST_RUN_DATA

        prepare_initial_offsets_spy = mocker.spy(connector, "_prepare_initial_offsets")
        connector.get_alerts()

        assert prepare_initial_offsets_spy.spy_return == TEST_KAFKA_OFFSETS

    def test_get_alerts_with_initial_offset_and_partitions_prepares_correct_offsets(
        self,
        mocker: MockerFixture,
        connector: KafkaMessagesConnector,
    ) -> None:
        """Test the _prepare_initial_offsets method with initial_offset
        and partitions."""
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.consumer_group_id = None
        connector.params.initial_offset = "100"
        connector.params.partitions = [1, 2, 3]
        connector.params.topic = TEST_TOPIC
        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = ([], {})
        connector.context.last_run_data = {}

        prepare_initial_offsets_spy = mocker.spy(connector, "_prepare_initial_offsets")
        connector.get_alerts()

        assert prepare_initial_offsets_spy.spy_return == {1: None, 2: None, 3: None}

    def test_get_alerts_with_partitions_only_prepares_correct_offsets(
        self,
        mocker: MockerFixture,
        connector: KafkaMessagesConnector,
    ) -> None:
        """Test the _prepare_initial_offsets method with partitions only."""
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.consumer_group_id = None
        connector.params.initial_offset = None
        connector.params.partitions = [1, 2]
        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = ([], {})
        connector.params.topic = TEST_TOPIC
        connector.context.last_run_data = {}

        prepare_initial_offsets_spy = mocker.spy(connector, "_prepare_initial_offsets")
        connector.get_alerts()

        assert prepare_initial_offsets_spy.spy_return == {1: None, 2: None}

    def test_get_alerts_with_no_offset_params_prepares_empty_offsets(
        self,
        mocker: MockerFixture,
        connector: KafkaMessagesConnector,
    ) -> None:
        """Test the _prepare_initial_offsets method with no specific offset params."""
        connector.params.unique_id_field = TEST_UNIQUE_ID_FIELD
        connector.params.timestamp_field = TEST_TIMESTAMP_FIELD
        connector.params.timestamp_format = TEST_TIMESTAMP_FORMAT
        connector.params.case_name_template = TEST_CASE_NAME_TEMPLATE
        connector.params.alert_name_template = TEST_ALERT_NAME_TEMPLATE
        connector.params.rule_generator_template = TEST_RULE_GENERATOR_TEMPLATE
        connector.params.severity_mapping_json = TEST_SEVERITY_MAPPING_DEFAULT_DICT
        connector.params.max_messages_to_fetch = MAX_MESSAGES_TO_FETCH
        connector.params.poll_timeout = DEFAULT_TIMEOUT
        connector.params.topic = TEST_TOPIC
        connector.params.consumer_group_id = None
        connector.params.initial_offset = None
        connector.params.partitions = None
        connector.manager = mocker.MagicMock()
        connector.manager.consume_messages.return_value = ([], {})
        connector.params.topic = TEST_TOPIC
        connector.context.last_run_data = {}

        prepare_initial_offsets_spy = mocker.spy(connector, "_prepare_initial_offsets")
        connector.get_alerts()

        assert prepare_initial_offsets_spy.spy_return == {}
