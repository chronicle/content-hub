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

import base64
import binascii
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ..core import (
    constants,
    data_models,
)
from ..tests.test_constants import (
    INITIAL_OFFSET_EARLIEST,
    TEST_BOOTSTRAP_SERVERS,
    TEST_CA_CERT_CONTENT_BYTES,
    TEST_CA_PATH,
    TEST_CLIENT_CERT_CONTENT_BYTES,
    TEST_CLIENT_KEY_CONTENT_BYTES,
    TEST_CLIENT_CERT_PATH,
    TEST_CLIENT_KEY_PATH,
    TEST_CONSUMER_GROUP_ID,
    TEST_INITIAL_OFFSETS,
    TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD,
    TEST_KAFKA_PASSWORD,
    TEST_KAFKA_USERNAME,
    TEST_TEMP_FILE_PATH,
    TEST_TOPIC,
    TEST_TOPIC_NON_EXISTENT,
)

if TYPE_CHECKING:
    from typing import Any

    from pytest_mock import MockerFixture

    from TIPCommon.types import SingleJosn

    from ..core.config_models import (
        KafkaConfigurationParameters,
    )
    from ..core.kafka_manager import (
        KafkaClient,
        KafkaConsumeResult,
    )


class TestKafkaClient:
    def test_build_kafka_config_plaintext(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test building Kafka config with plaintext (no security) settings."""
        mock_kafka_config.use_ssl = False
        mock_kafka_config.use_sasl_ssl = False
        mock_kafka_config.sasl_username = None
        mock_kafka_config.sasl_password = None

        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        build_config_spy(constants.SecurityProtocol.PLAINTEXT)
        conf = build_config_spy.spy_return
        assert conf == {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "security.protocol": "PLAINTEXT",
        }

    def test_build_kafka_config_sasl_plaintext(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test building Kafka config with SASL_PLAINTEXT security."""
        mock_kafka_config.sasl_username = TEST_KAFKA_USERNAME
        mock_kafka_config.sasl_password = TEST_KAFKA_PASSWORD

        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        build_config_spy(constants.SecurityProtocol.SASL_PLAINTEXT)
        conf = build_config_spy.spy_return

        assert conf == {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "PLAIN",
            "sasl.username": TEST_KAFKA_USERNAME,
            "sasl.password": TEST_KAFKA_PASSWORD,
        }

    def test_build_kafka_config_sasl_plaintext_missing_credentials(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test building Kafka config with SASL_PLAINTEXT and missing credentials."""
        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        with pytest.raises(
            ValueError,
            match="SASL username and password must be provided for SASL connections.",
        ):
            build_config_spy(constants.SecurityProtocol.SASL_PLAINTEXT)

    def test_build_kafka_config_ssl(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test building Kafka config with SSL security."""
        ca_path: Path = Path(TEST_CA_PATH)
        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        build_config_spy(constants.SecurityProtocol.SSL, ca_path=ca_path)
        conf = build_config_spy.spy_return
        assert conf == {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "security.protocol": "SSL",
            "ssl.ca.location": str(ca_path),
        }

    def test_build_kafka_config_ssl_missing_ca(
        self, mocker: MockerFixture, kafka_client: KafkaClient
    ) -> None:
        """Test building Kafka config with SSL security but missing CA certificate."""
        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        with pytest.raises(
            ValueError,
            match=(
                "CA certificate must be provided for connections using SSL or SASL_SSL."
            ),
        ):
            build_config_spy(constants.SecurityProtocol.SSL)

    def test_build_kafka_config_ssl_with_client_certs(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test building Kafka config with SSL and client certificates."""
        ca_path: Path = Path(TEST_CA_PATH)
        client_cert_path: Path = Path(TEST_CLIENT_CERT_PATH)
        client_key_path: Path = Path(TEST_CLIENT_KEY_PATH)
        mock_kafka_config.client_certificate_key_password = (
            TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD
        )

        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        build_config_spy(
            constants.SecurityProtocol.SSL,
            ca_path=ca_path,
            client_cert_path=client_cert_path,
            client_key_path=client_key_path,
        )
        conf = build_config_spy.spy_return
        assert conf == {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "security.protocol": "SSL",
            "ssl.ca.location": str(ca_path),
            "ssl.certificate.location": str(client_cert_path),
            "ssl.key.location": str(client_key_path),
            "ssl.key.password": TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD,
        }

    def test_build_kafka_config_sasl_ssl(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test building Kafka config with SASL_SSL security."""
        mock_kafka_config.sasl_username = TEST_KAFKA_USERNAME
        mock_kafka_config.sasl_password = TEST_KAFKA_PASSWORD
        ca_path: Path = Path(TEST_CA_PATH)

        build_config_spy = mocker.spy(kafka_client, "_build_kafka_config")
        build_config_spy(constants.SecurityProtocol.SASL_SSL, ca_path=ca_path)
        conf = build_config_spy.spy_return

        assert conf == {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "PLAIN",
            "sasl.username": TEST_KAFKA_USERNAME,
            "sasl.password": TEST_KAFKA_PASSWORD,
            "ssl.ca.location": str(ca_path),
        }

    def test_connectivity_creates_temp_files(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test that test_connectivity creates temporary certificate files."""
        mock_kafka_config.use_ssl = True
        mock_kafka_config.ca_certificate = base64.b64encode(
            TEST_CA_CERT_CONTENT_BYTES
        ).decode()
        mock_kafka_config.client_certificate = base64.b64encode(
            TEST_CLIENT_CERT_CONTENT_BYTES
        ).decode()
        mock_kafka_config.client_certificate_key = base64.b64encode(
            TEST_CLIENT_KEY_CONTENT_BYTES
        ).decode()

        create_temp_file_mock = mocker.patch(
            "apache_kafka.core.kafka_manager."
            "create_and_write_to_tempfile"
        )
        create_temp_file_mock.side_effect = [
            Path(TEST_CA_PATH),
            Path(TEST_CLIENT_CERT_PATH),
            Path(TEST_CLIENT_KEY_PATH),
        ]
        mocker.patch("apache_kafka.core.kafka_manager.AdminClient")
        cleanup_mock = mocker.patch.object(kafka_client, "_cleanup_temp_files")

        kafka_client.test_connectivity()

        create_temp_file_mock.assert_any_call(TEST_CA_CERT_CONTENT_BYTES)
        create_temp_file_mock.assert_any_call(TEST_CLIENT_CERT_CONTENT_BYTES)
        create_temp_file_mock.assert_any_call(TEST_CLIENT_KEY_CONTENT_BYTES)
        cleanup_mock.assert_called_once()

    def test_connectivity_cleans_up_temp_files(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_logger: Any,
    ) -> None:
        """Test that test_connectivity cleans up temporary files."""
        mock_file1: Any = mocker.MagicMock(spec=Path)
        mock_file1.exists.return_value = True
        mock_file2: Any = mocker.MagicMock(spec=Path)
        mock_file2.exists.return_value = True
        temp_files = [mock_file1, mock_file2, None]

        mocker.patch.object(
            kafka_client,
            "_get_connection_config",
            return_value=(
                {},
                temp_files,
            ),
        )
        mocker.patch("apache_kafka.core.kafka_manager.AdminClient")

        kafka_client.test_connectivity()

        mock_file1.unlink.assert_called_once()
        mock_file2.unlink.assert_called_once()
        mock_logger.info.assert_any_call(f"Removed temporary file: {mock_file1}")
        mock_logger.info.assert_any_call(f"Removed temporary file: {mock_file2}")

    def test_connectivity_cleanup_handles_os_error(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_logger: Any,
    ) -> None:
        """Test that test_connectivity cleanup handles an OSError."""
        mock_file: Any = mocker.MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.unlink.side_effect = OSError("Permission denied")
        temp_files = [mock_file]

        mocker.patch.object(
            kafka_client,
            "_get_connection_config",
            return_value=(
                {},
                temp_files,
            ),
        )
        mocker.patch("apache_kafka.core.kafka_manager.AdminClient")

        kafka_client.test_connectivity()

        mock_file.unlink.assert_called_once()
        mock_logger.error.assert_called_once_with(
            f"Failed to remove temporary file {mock_file}: Permission denied"
        )

    @pytest.mark.parametrize(
        "config_updates, expected_protocol",
        [
            ({"use_sasl_ssl": True}, constants.SecurityProtocol.SASL_SSL),
            ({"use_ssl": True}, constants.SecurityProtocol.SSL),
            (
                {
                    "sasl_username": TEST_KAFKA_USERNAME,
                    "sasl_password": TEST_KAFKA_PASSWORD,
                },
                constants.SecurityProtocol.SASL_PLAINTEXT,
            ),
            ({}, constants.SecurityProtocol.PLAINTEXT),
        ],
    )
    def test_determine_security_protocol(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
        config_updates: SingleJosn,
        expected_protocol: constants.SecurityProtocol,
    ) -> None:
        """Test that the correct security protocol is determined based on config."""
        for key, value in config_updates.items():
            setattr(mock_kafka_config, key, value)

        determine_protocol_spy = mocker.spy(
            kafka_client,
            "_determine_security_protocol",
        )

        mocker.patch.object(
            kafka_client,
            "_create_temp_cert_files",
            return_value=([], {}),
        )
        mocker.patch.object(kafka_client, "_build_kafka_config", return_value={})
        mocker.patch("apache_kafka.core.kafka_manager.AdminClient")
        mocker.patch.object(kafka_client, "_cleanup_temp_files")

        kafka_client.test_connectivity()

        determine_protocol_spy.assert_called_once()
        assert determine_protocol_spy.spy_return.value == expected_protocol.value

        mock_kafka_config.use_sasl_ssl = False
        mock_kafka_config.use_ssl = False
        mock_kafka_config.sasl_username = None
        mock_kafka_config.sasl_password = None

    def test_connectivity_with_ssl_success(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test that connectivity works with SSL and calls config methods correctly."""
        create_temp_files_spy = mocker.spy(
            kafka_client,
            "_create_temp_cert_files",
        )
        determine_protocol_mock = mocker.patch.object(
            kafka_client,
            "_determine_security_protocol",
        )
        build_config_mock = mocker.patch.object(
            kafka_client,
            "_build_kafka_config",
        )
        mocker.patch("apache_kafka.core.kafka_manager.AdminClient")

        mock_kafka_config.use_ssl = True
        determine_protocol_mock.return_value = constants.SecurityProtocol.SSL
        create_temp_files_spy.return_value = (
            [Path(TEST_CA_PATH)],
            {"ca_path": Path(TEST_CA_PATH)},
        )

        kafka_client.test_connectivity()

        create_temp_files_spy.assert_called_once()
        determine_protocol_mock.assert_called_once()

        call_args, call_kwargs = build_config_mock.call_args
        assert call_args[0] == constants.SecurityProtocol.SSL
        assert "ca_path" in call_kwargs
        assert call_kwargs["ca_path"] == create_temp_files_spy.spy_return[1]["ca_path"]

    def test_get_connection_config_invalid_certificate_content(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test connectivity raises error for invalid base64 certificate content."""
        mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient",
        )
        mock_cleanup_temp_files: Any = mocker.patch.object(
            kafka_client,
            "_cleanup_temp_files",
        )

        mocker.patch.object(
            kafka_client,
            "_create_temp_cert_files",
        ).side_effect = binascii.Error("Invalid base64")

        kafka_client.kafka_config.use_ssl = True

        with pytest.raises(
            Exception,
            match=(
                "Invalid certificate content. Please ensure the certificate "
                "values are valid base64 encoded strings."
            ),
        ):
            kafka_client.test_connectivity()

        mock_cleanup_temp_files.assert_called()

    def test_connectivity_value_error_in_config(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test connectivity raises error when a ValueError is raised in config."""
        mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient",
        )
        mock_create_temp_cert_files: Any = mocker.patch.object(
            kafka_client,
            "_create_temp_cert_files",
        )
        mock_determine_security_protocol: Any = mocker.patch.object(
            kafka_client,
            "_determine_security_protocol",
        )
        mock_build_kafka_config: Any = mocker.patch.object(
            kafka_client,
            "_build_kafka_config",
        )
        mock_cleanup_temp_files: Any = mocker.patch.object(
            kafka_client,
            "_cleanup_temp_files",
        )

        mock_kafka_config.use_ssl = True
        mock_create_temp_cert_files.return_value = (
            [Path(TEST_CA_PATH)],
            {"ca_path": Path(TEST_CA_PATH)},
        )
        mock_determine_security_protocol.return_value = constants.SecurityProtocol.SSL
        mock_build_kafka_config.side_effect = ValueError("Missing config")

        with pytest.raises(
            Exception,
            match="Missing required configuration for the selected security protocol.",
        ):
            kafka_client.test_connectivity()

        mock_cleanup_temp_files.assert_called()

    def test_connectivity_os_error_on_temp_file(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_kafka_config: KafkaConfigurationParameters,
    ) -> None:
        """Test connectivity raises error when an OSError is raised creating
        temp files."""
        mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient",
        )
        mock_create_temp_cert_files: Any = mocker.patch.object(
            kafka_client,
            "_create_temp_cert_files",
        )
        cleanup_mock = mocker.patch.object(
            kafka_client,
            "_cleanup_temp_files",
        )

        mock_kafka_config.use_ssl = True
        mock_create_temp_cert_files.side_effect = OSError("Disk full")

        with pytest.raises(
            Exception,
            match="Failed to create temporary certificate files",
        ):
            kafka_client.test_connectivity()

        cleanup_mock.assert_called()

    def test_test_connectivity_success(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_logger: Any,
    ) -> None:
        """Test successful connectivity to Kafka."""
        mock_get_connection_config: Any = mocker.patch.object(
            kafka_client,
            "_get_connection_config",
        )
        mock_admin_client: Any = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        )

        mock_get_connection_config.return_value = ({}, [])
        mock_admin_client_instance: Any = mock_admin_client.return_value
        mock_list_topics_result: Any = mocker.MagicMock()
        mock_list_topics_result.brokers = {1: mocker.MagicMock()}
        mock_admin_client_instance.list_topics.return_value = mock_list_topics_result

        kafka_client.test_connectivity()

        mock_get_connection_config.assert_called_once()
        mock_admin_client.assert_called_once_with({})
        mock_admin_client_instance.list_topics.assert_called_once_with(
            timeout=constants.DEFAULT_TIMEOUT
        )
        mock_logger.info.assert_called_once()

    def test_test_connectivity_kafka_exception(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test connectivity failure due to a KafkaException."""
        mock_get_connection_config: Any = mocker.patch.object(
            kafka_client,
            "_get_connection_config",
        )
        mock_admin_client: Any = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        )

        mock_get_connection_config.return_value = ({}, [])
        mock_admin_client_instance: Any = mock_admin_client.return_value
        mock_admin_client_instance.list_topics.side_effect = Exception(
            "Unable to establish a connection. Please verify the broker list, "
            "network connectivity, credentials, and SSL/TLS configurations. "
        )

        with pytest.raises(
            Exception,
            match=(
                "Unable to establish a connection. Please verify the broker list, "
                "network connectivity, credentials, and SSL/TLS configurations. "
            ),
        ):
            kafka_client.test_connectivity()

    def test_test_connectivity_cleanup_called(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test temporary file cleanup is always called during connectivity test."""
        mock_cleanup_temp_files: Any = mocker.patch.object(
            kafka_client,
            "_cleanup_temp_files",
        )
        mock_get_connection_config: Any = mocker.patch.object(
            kafka_client,
            "_get_connection_config",
        )
        mock_admin_client: Any = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        )

        temp_files: list[Path] = [Path(TEST_TEMP_FILE_PATH)]
        mock_get_connection_config.return_value = ({}, temp_files)
        mock_admin_client_instance: Any = mock_admin_client.return_value
        mock_list_topics_result: Any = mocker.MagicMock()
        mock_list_topics_result.brokers = {1: mocker.MagicMock()}
        mock_admin_client_instance.list_topics.return_value = mock_list_topics_result

        kafka_client.test_connectivity()
        mock_cleanup_temp_files.assert_called_once_with(temp_files)

    def test_consume_messages_uses_partitions_from_initial_offsets(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages uses partitions from initial_offsets."""
        mocker.patch.object(
            kafka_client, "_get_connection_config", return_value=({}, [])
        )
        mock_consumer = mocker.patch(
            "apache_kafka.core.kafka_manager.Consumer"
        ).return_value
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mock_admin_client = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        ).return_value

        mock_topic_metadata = mocker.MagicMock()
        mock_topic_metadata.error = None
        mock_admin_client.list_topics.return_value.topics = {
            TEST_TOPIC: mock_topic_metadata
        }

        initial_offsets: dict[int, int] = TEST_INITIAL_OFFSETS

        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets=initial_offsets,
        )

        assign_call_args = mock_consumer.assign.call_args[0][0]
        assigned_partitions = {tp.partition for tp in assign_call_args}

        assert assigned_partitions == set(initial_offsets.keys())

    def test_consume_messages_fetches_partitions_when_not_provided(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages fetches partitions if not in initial_offsets."""
        mocker.patch.object(
            kafka_client,
            "_get_connection_config",
            return_value=({}, []),
        )
        mock_consumer = mocker.patch(
            "apache_kafka.core.kafka_manager.Consumer"
        ).return_value
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mock_admin_client_class = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        )
        mock_admin_client = mock_admin_client_class.return_value

        mock_list_topics_result: Any = mocker.MagicMock()
        mock_topic_metadata: Any = mocker.MagicMock()
        mock_topic_metadata.partitions = {0: mocker.MagicMock(), 1: mocker.MagicMock()}
        mock_topic_metadata.error = None
        mock_list_topics_result.topics = {TEST_TOPIC: mock_topic_metadata}
        mock_admin_client.list_topics.return_value = mock_list_topics_result

        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets={},
        )

        mock_admin_client.list_topics.assert_any_call(
            TEST_TOPIC,
            timeout=constants.DEFAULT_TIMEOUT,
        )
        assign_call_args = mock_consumer.assign.call_args[0][0]
        assigned_partitions = {tp.partition for tp in assign_call_args}

        assert assigned_partitions == {0, 1}

    def test_consume_messages_raises_error_for_nonexistent_topic(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test consume_messages raises an error if the topic is not found when
        fetching partitions."""
        mocker.patch.object(
            kafka_client,
            "_get_connection_config",
            return_value=({}, []),
        )
        mocker.patch("apache_kafka.core.kafka_manager.Consumer")
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mock_admin_client = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        ).return_value

        mock_list_topics_result: Any = mocker.MagicMock()
        mock_list_topics_result.topics = {}
        mock_admin_client.list_topics.return_value = mock_list_topics_result

        with pytest.raises(
            Exception, match=f"Topic '{TEST_TOPIC_NON_EXISTENT}' not found."
        ):
            kafka_client.consume_messages(
                topic=TEST_TOPIC_NON_EXISTENT,
                alert_config=mocker.MagicMock(),
                max_alerts_to_fetch=1,
                initial_offsets={},
            )

    def test_consume_messages_assigns_manual_partitions(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages correctly assigns manual partitions."""
        mocker.patch.object(
            kafka_client,
            "_get_connection_config",
            return_value=({}, []),
        )
        mock_consumer = mocker.patch(
            "apache_kafka.core.kafka_manager.Consumer"
        ).return_value
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mocker.patch.object(
            kafka_client,
            "_get_partitions_to_process",
            return_value={0, 1, 2},
        )
        mock_admin_client = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        ).return_value

        mock_topic_metadata = mocker.MagicMock()
        mock_topic_metadata.error = None
        mock_admin_client.list_topics.return_value.topics = {
            TEST_TOPIC: mock_topic_metadata
        }

        initial_offsets: dict[int, int | None] = {0: 10, 1: None, 2: 20}

        result = kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets=initial_offsets,
        )

        assign_call_args = mock_consumer.assign.call_args[0][0]
        assigned_partitions = {tp.partition for tp in assign_call_args}
        assert assigned_partitions == {0, 1, 2}
        assert result.next_offsets == {0: 10, 2: 20}

    def test_consume_messages_polls_and_updates_offsets(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test consume_messages polls for messages and updates offsets correctly."""
        mock_kafka_consumer_session = mocker.patch.object(
            kafka_client,
            "_kafka_consumer_session",
        )
        mock_consumer = mocker.MagicMock()
        mock_kafka_consumer_session.return_value.__enter__.return_value = (
            mock_consumer,
            {0: 0},
        )

        mock_alert_config: Any = mocker.MagicMock(spec=data_models.AlertConfig)
        mocker.patch(
            "apache_kafka.core.data_models.KafkaMessage",
            side_effect=[mocker.MagicMock(), mocker.MagicMock()],
        )

        raw_msg1 = mocker.MagicMock()
        raw_msg1.error.return_value = None
        raw_msg1.partition.return_value = 0
        raw_msg1.offset.return_value = 0

        raw_msg2 = mocker.MagicMock()
        raw_msg2.error.return_value = None
        raw_msg2.partition.return_value = 0
        raw_msg2.offset.return_value = 1

        mock_consumer.consume.return_value = [raw_msg1, raw_msg2]

        result = kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mock_alert_config,
            max_alerts_to_fetch=2,
            initial_offsets={},
        )

        assert len(result.messages) == 2
        assert result.next_offsets[0] == 2

    def test_consume_messages_handles_poll_error(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
        mock_logger: Any,
    ) -> None:
        """Test that consume_messages handles a message with an error during polling."""
        mock_kafka_consumer_session = mocker.patch.object(
            kafka_client,
            "_kafka_consumer_session",
        )
        mock_consumer = mocker.MagicMock()
        mock_kafka_consumer_session.return_value.__enter__.return_value = (
            mock_consumer,
            {},
        )
        mock_alert_config: Any = mocker.MagicMock(spec=data_models.AlertConfig)
        mock_kafka_message_class = mocker.patch(
            "apache_kafka.core.data_models.KafkaMessage"
        )

        mock_raw_message_error: Any = mocker.MagicMock()
        mock_raw_message_error.error.return_value = "Some Kafka Error"

        mock_consumer.consume.return_value = [mock_raw_message_error]

        result = kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mock_alert_config,
            max_alerts_to_fetch=1,
            initial_offsets={},
        )

        assert len(result.messages) == 0
        mock_logger.error.assert_called_once_with(
            "Kafka Consumer error: Some Kafka Error"
        )
        mock_kafka_message_class.assert_not_called()

    def test_consume_messages_creates_group_consumer(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages creates a consumer for group-based consumption."""
        mocker.patch.object(kafka_client, "_get_connection_config").return_value = (
            {"bootstrap.servers": TEST_BOOTSTRAP_SERVERS},
            [],
        )
        mock_consumer_class = mocker.patch(
            "apache_kafka.core.kafka_manager.Consumer"
        )
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mock_admin_client = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        ).return_value
        mock_topic_metadata = mocker.MagicMock()
        mock_topic_metadata.error = None
        mock_admin_client.list_topics.return_value.topics = {
            TEST_TOPIC: mock_topic_metadata
        }

        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets={},
            group_id=TEST_CONSUMER_GROUP_ID,
            offset_reset_policy=INITIAL_OFFSET_EARLIEST,
        )

        expected_conf = {
            "bootstrap.servers": TEST_BOOTSTRAP_SERVERS,
            "group.id": TEST_CONSUMER_GROUP_ID,
            "auto.offset.reset": INITIAL_OFFSET_EARLIEST,
            "enable.auto.commit": True,
        }
        mock_consumer_class.assert_called_once_with(expected_conf)
        mock_consumer_class.return_value.subscribe.assert_called_once_with([TEST_TOPIC])

    def test_consume_messages_creates_manual_consumer(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages creates a consumer for manual assignment."""
        mocker.patch.object(kafka_client, "_get_connection_config").return_value = (
            {"bootstrap.servers": TEST_BOOTSTRAP_SERVERS},
            [],
        )
        mock_consumer_class = mocker.patch(
            "apache_kafka.core.kafka_manager.Consumer"
        )
        mocker.patch.object(kafka_client, "_poll_messages", return_value=[])
        mocker.patch.object(
            kafka_client,
            "_assign_manual_partitions",
            return_value=([mocker.MagicMock()], {0: 10}),
        )
        mock_admin_client = mocker.patch(
            "apache_kafka.core.kafka_manager.AdminClient"
        ).return_value
        mock_topic_metadata = mocker.MagicMock()
        mock_topic_metadata.error = None
        mock_admin_client.list_topics.return_value.topics = {
            TEST_TOPIC: mock_topic_metadata
        }

        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets={0: 10},
        )

        call_args = mock_consumer_class.call_args[0][0]
        assert call_args["bootstrap.servers"] == TEST_BOOTSTRAP_SERVERS
        assert call_args["enable.auto.commit"] is False
        assert "group.id" in call_args

        mock_consumer_class.return_value.assign.assert_called_once()

    def test_consume_messages_with_group_id_creates_group_consumer(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test that consume_messages with a group_id creates a group consumer."""
        mock_get_connection_config = mocker.patch.object(
            kafka_client,
            "_get_connection_config",
        )
        mock_create_group_consumer = mocker.patch.object(
            kafka_client,
            "_create_group_consumer",
        )
        mock_poll_messages = mocker.patch.object(kafka_client, "_poll_messages")

        mock_get_connection_config.return_value = ({}, [])
        mock_consumer = mocker.MagicMock()
        mock_create_group_consumer.return_value = (mock_consumer, {})
        mock_poll_messages.return_value = []

        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets={},
            group_id=TEST_CONSUMER_GROUP_ID,
            offset_reset_policy=INITIAL_OFFSET_EARLIEST,
        )

        mock_create_group_consumer.assert_called_once_with(
            {},
            TEST_TOPIC,
            TEST_CONSUMER_GROUP_ID,
            INITIAL_OFFSET_EARLIEST,
        )
        mock_poll_messages.assert_called_once_with(
            consumer=mock_consumer,
            alert_config=mocker.ANY,
            max_alerts_to_fetch=1,
            next_offsets={},
            is_manual_offset=False,
            poll_timeout=mocker.ANY,
        )

    def test_consume_messages_with_manual_assignment(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test consume_messages with manual assignment creates a manual consumer."""
        mock_get_connection_config = mocker.patch.object(
            kafka_client,
            "_get_connection_config",
        )
        mock_create_manual_consumer = mocker.patch.object(
            kafka_client,
            "_create_manual_consumer",
        )
        mock_seek_to_initial_positions = mocker.patch.object(
            kafka_client,
            "_seek_to_initial_positions",
        )
        mock_poll_messages = mocker.patch.object(kafka_client, "_poll_messages")

        mock_get_connection_config.return_value = ({}, [])
        mock_consumer = mocker.MagicMock()
        mock_partitions_to_assign = [mocker.MagicMock()]
        mock_create_manual_consumer.return_value = (
            mock_consumer,
            mock_partitions_to_assign,
            {0: 10},
        )
        mock_poll_messages.return_value = []

        initial_offsets = {0: 10}
        kafka_client.consume_messages(
            topic=TEST_TOPIC,
            alert_config=mocker.MagicMock(),
            max_alerts_to_fetch=1,
            initial_offsets=initial_offsets,
            group_id=None,
            offset_reset_policy=INITIAL_OFFSET_EARLIEST,
        )

        mock_create_manual_consumer.assert_called_once_with(
            {},
            TEST_TOPIC,
            initial_offsets,
        )
        mock_consumer.assign.assert_called_once_with(mock_partitions_to_assign)
        mock_seek_to_initial_positions.assert_called_once_with(
            mock_consumer,
            INITIAL_OFFSET_EARLIEST,
            {0: 10},
        )

    def test_consume_messages_success(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test the successful consumption of messages."""
        mock_kafka_consumer_session: Any = mocker.patch.object(
            kafka_client,
            "_kafka_consumer_session",
        )
        mock_poll_messages: Any = mocker.patch.object(kafka_client, "_poll_messages")

        topic: str = TEST_TOPIC
        alert_config: Any = mocker.MagicMock(spec=data_models.AlertConfig)
        max_alerts_to_fetch: int = 10
        initial_offsets: dict[int, int] = {}
        poll_timeout: int = 1000
        group_id: str = TEST_CONSUMER_GROUP_ID
        offset_reset_policy: str = INITIAL_OFFSET_EARLIEST

        mock_consumer: Any = mocker.MagicMock()
        mock_next_offsets: dict[int, int] = {0: 5}
        mock_kafka_consumer_session.return_value.__enter__.return_value = (
            mock_consumer,
            mock_next_offsets,
        )

        mock_messages: list[Any] = [mocker.MagicMock(spec=data_models.KafkaMessage)]
        mock_poll_messages.return_value = mock_messages

        result: KafkaConsumeResult = kafka_client.consume_messages(
            topic,
            alert_config,
            max_alerts_to_fetch,
            initial_offsets,
            poll_timeout,
            group_id,
            offset_reset_policy,
        )

        mock_kafka_consumer_session.assert_called_once_with(
            topic,
            group_id,
            initial_offsets,
            offset_reset_policy,
        )
        mock_poll_messages.assert_called_once_with(
            consumer=mock_consumer,
            alert_config=alert_config,
            max_alerts_to_fetch=max_alerts_to_fetch,
            next_offsets=mock_next_offsets,
            is_manual_offset=False,
            poll_timeout=poll_timeout,
        )
        assert result.messages == mock_messages
        assert result.next_offsets == mock_next_offsets

    def test_consume_messages_kafka_exception(
        self,
        mocker: MockerFixture,
        kafka_client: KafkaClient,
    ) -> None:
        """Test message consumption when a KafkaException is raised."""
        mock_kafka_consumer_session: Any = mocker.patch.object(
            kafka_client,
            "_kafka_consumer_session",
        )

        topic: str = TEST_TOPIC
        alert_config: Any = mocker.MagicMock(spec=data_models.AlertConfig)
        max_alerts_to_fetch: int = 10
        initial_offsets: dict[int, int] = {}

        mock_kafka_consumer_session.side_effect = Exception(
            "Unable to establish a connection."
        )

        with pytest.raises(Exception, match="Unable to establish a connection."):
            kafka_client.consume_messages(
                topic,
                alert_config,
                max_alerts_to_fetch,
                initial_offsets,
            )
