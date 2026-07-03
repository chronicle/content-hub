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

from ...core.action_init import create_kafka_client

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from ...actions.ping import Ping


class TestPingAction:
    """Ping action test cases."""

    def test_init(self, ping_action: Ping) -> None:
        """Test init.

        Args:
            ping_action: ping action fixture
        """
        assert ping_action.output_message == (
            "Successfully connected to the Apache Kafka server with the provided "
            "connection parameters!"
        )
        assert ping_action.error_output_message == (
            "Failed to connect to the Apache Kafka server!"
        )

    def test_perform_action(
        self,
        ping_action: Ping,
        mocker: MockerFixture,
    ) -> None:
        """Test perform action.

        Args:
            ping_action: ping action fixture
            mocker: mocker fixture
        """
        mock_api_client = mocker.MagicMock()
        mocker.patch.object(
            ping_action, "_init_api_clients", return_value=mock_api_client
        )
        ping_action.run()
        mock_api_client.test_connectivity.assert_called_once()


def test_create_kafka_client(mocker: MockerFixture) -> None:
    """Test create kafka client.

    Args:
        mocker: mocker fixture
    """
    soar_action = mocker.MagicMock()
    get_integration_parameters = mocker.patch(
        "apache_kafka.core.action_init.get_integration_parameters",
    )
    kafka_client = mocker.patch(
        "apache_kafka.core.action_init.KafkaClient",
    )
    create_kafka_client(soar_action)
    get_integration_parameters.assert_called_once_with(soar_action)
    kafka_client.assert_called_once_with(
        get_integration_parameters.return_value,
        soar_action.logger,
    )
