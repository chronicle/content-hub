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
import soar_sdk
from typing import TYPE_CHECKING
import pytest
from apache_kafka.actions.ping import Ping
from apache_kafka.connectors.kafka_messages_connector import (
    KafkaMessagesConnector,
)
from apache_kafka.core.kafka_manager import KafkaClient
from apache_kafka.core import config_models

pytest_plugins = ("integration_testing.conftest",)

sdk_dir = soar_sdk.__path__[0]

if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

if TYPE_CHECKING:
    from typing import Any

    from pytest_mock import MockerFixture

@pytest.fixture()
def ping_action(mocker: MockerFixture) -> Ping:
    """Ping action fixture."""
    mocker.patch(
        "apache_kafka.actions.ping.create_kafka_client",
    )
    mocker.patch("TIPCommon.base.action.base_action.create_soar_action")
    mocker.patch("TIPCommon.base.action.base_action.create_logger")
    mocker.patch("TIPCommon.base.action.base_action.create_params_container")

    return Ping()

@pytest.fixture
def connector(mocker: MockerFixture) -> KafkaMessagesConnector:
    """Connector fixture"""
    mocker.patch(
        "TIPCommon.base.connector.base_connector.create_soar_connector",
    )
    return KafkaMessagesConnector()

@pytest.fixture
def mock_kafka_config(
    mocker: MockerFixture,
) -> config_models.KafkaConfigurationParameters:
    """Create a mock Kafka configuration object."""
    config = mocker.MagicMock(spec=config_models.KafkaConfigurationParameters)
    config.bootstrap_servers = "localhost:9092"
    config.sasl_username = None
    config.sasl_password = None
    config.ca_certificate = None
    config.client_certificate = None
    config.client_certificate_key = None
    config.client_certificate_key_password = None
    config.use_ssl = False
    config.use_sasl_ssl = False
    return config

@pytest.fixture
def mock_logger(mocker: MockerFixture) -> Any:
    """Create a mock logger object."""
    logger = mocker.MagicMock()
    return logger

@pytest.fixture
def kafka_client(
    mock_kafka_config: config_models.KafkaConfigurationParameters, # pylint: disable=redefined-outer-name
    mock_logger: Any,  # pylint: disable=redefined-outer-name
) -> KafkaClient:
    """Create a KafkaClient instance with mock configuration and logger."""
    return KafkaClient(kafka_config=mock_kafka_config, logger=mock_logger)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
