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

import base64
import binascii
import contextlib
from pathlib import Path
from typing import NamedTuple, TYPE_CHECKING
import uuid

from confluent_kafka import Consumer, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient, BrokerMetadata, TopicMetadata

from TIPCommon.utils import create_and_write_to_tempfile
from ..core import config_models
from ..core import constants
from ..core import data_models
from ..core import exceptions

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping, MutableMapping

    from confluent_kafka import Message

    from TIPCommon.base.interfaces import ScriptLogger


class KafkaConsumeResult(NamedTuple):
    """Represents the result of consuming messages from Kafka.

    Attributes:
        messages (list[data_models.KafkaMessage]): A list of consumed and parsed
            Kafka messages.
        next_offsets (MutableMapping[int, int]): A dictionary mapping partition IDs to
            the next offset to consume.
    """

    messages: list[data_models.KafkaMessage]
    next_offsets: MutableMapping[int, int]


class KafkaClient:
    """Manages interactions with a Kafka server, including connectivity testing"""

    def __init__(
        self,
        kafka_config: config_models.KafkaConfigurationParameters,
        logger: ScriptLogger,
    ) -> None:
        """Initializes a KafkaClient instance.

        Args:
            kafka_config (config_models.KafkaConfigurationParameters): The Kafka
                configuration parameters.
            logger (ScriptLogger): The logger instance.
        """
        self.kafka_config: config_models.KafkaConfigurationParameters = kafka_config
        self.logger: ScriptLogger = logger

    def _build_kafka_config(
        self,
        security_protocol: constants.SecurityProtocol,
        ca_path: Path | None = None,
        client_cert_path: Path | None = None,
        client_key_path: Path | None = None,
    ) -> dict[str, str]:
        """Builds the configuration dictionary for the Kafka client.

        Args:
            security_protocol (constants.SecurityProtocol): The security protocol to use
            ca_path (Path | None): Path to the CA certificate file.
            client_cert_path (Path | None): Path to the client certificate file.
            client_key_path (Path | None): Path to the client certificate key file.

        Returns:
            dict[str, str]: The configuration dictionary.

        Raises:
            ValueError: If required parameters for the specified security protocol
                are missing.
        """
        conf: dict[str, str] = {
            "bootstrap.servers": self.kafka_config.bootstrap_servers,
            "security.protocol": security_protocol.value,
        }

        if security_protocol.value.startswith(constants.SASL_PROTOCOL_PREFIX):
            if not (
                self.kafka_config.sasl_username and self.kafka_config.sasl_password
            ):
                raise ValueError(
                    "SASL username and password must be provided for SASL connections."
                )

            conf["sasl.mechanism"] = constants.PLAINTEXT_PROTOCOL
            conf["sasl.username"] = self.kafka_config.sasl_username
            conf["sasl.password"] = self.kafka_config.sasl_password

        if security_protocol.value in (
            constants.SecurityProtocol.SSL.value,
            constants.SecurityProtocol.SASL_SSL.value,
        ):
            if not ca_path:
                raise ValueError(
                    "CA certificate must be provided for connections using "
                    "SSL or SASL_SSL."
                )

            conf["ssl.ca.location"] = str(ca_path)

            if client_cert_path and client_key_path:
                conf["ssl.certificate.location"] = str(client_cert_path)
                conf["ssl.key.location"] = str(client_key_path)

                if self.kafka_config.client_certificate_key_password:
                    conf["ssl.key.password"] = (
                        self.kafka_config.client_certificate_key_password
                    )

        return conf

    def _cleanup_temp_files(self, file_paths: Iterable[Path | None]) -> None:
        """Removes temporary files.

        Args:
            file_paths (Iterable[Path | None]): An iterable of paths to temporary files.
        """
        file_path: Path | None

        for file_path in file_paths:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    self.logger.info(f"Removed temporary file: {file_path}")

                except (OSError, FileNotFoundError) as e:
                    self.logger.error(
                        f"Failed to remove temporary file {file_path}: {e}"
                    )

    def _create_temp_cert_files(self) -> tuple[list[Path], dict[str, Path | None]]:
        """Creates temporary files for certificates and returns their paths.

        Returns:
            tuple[list[Path], dict[str, Path | None]]: A tuple containing a list of all
            temporary file paths and a dictionary mapping certificate types to their
            respective paths.
        """
        temp_files: list[Path] = []
        cert_paths: dict[str, Path | None] = {
            "ca_path": None,
            "client_cert_path": None,
            "client_key_path": None,
        }

        if self.kafka_config.ca_certificate:
            cert_paths["ca_path"] = create_and_write_to_tempfile(
                base64.b64decode(self.kafka_config.ca_certificate)
            )
            temp_files.append(cert_paths["ca_path"])

        if self.kafka_config.client_certificate:
            cert_paths["client_cert_path"] = create_and_write_to_tempfile(
                base64.b64decode(self.kafka_config.client_certificate)
            )
            temp_files.append(cert_paths["client_cert_path"])

        if self.kafka_config.client_certificate_key:
            cert_paths["client_key_path"] = create_and_write_to_tempfile(
                base64.b64decode(self.kafka_config.client_certificate_key)
            )
            temp_files.append(cert_paths["client_key_path"])

        return temp_files, cert_paths

    def _determine_security_protocol(self) -> constants.SecurityProtocol:
        """Determines the security protocol based on the configuration.

        Returns:
            constants.SecurityProtocol: The determined security protocol.
        """
        if self.kafka_config.use_sasl_ssl:
            return constants.SecurityProtocol.SASL_SSL

        if self.kafka_config.use_ssl:
            return constants.SecurityProtocol.SSL

        if self.kafka_config.sasl_username and self.kafka_config.sasl_password:
            return constants.SecurityProtocol.SASL_PLAINTEXT

        return constants.SecurityProtocol.PLAINTEXT

    def _get_connection_config(self) -> tuple[dict[str, str], list[Path]]:
        """Builds Kafka client configuration and handles temporary certificate files.

        Returns:
            tuple[dict[str, str], list[Path]]: A tuple containing the config
            dictionary and a list of temporary file paths.

        Raises:
            exceptions.KafkaClientError: If certificate content is invalid or it fails
                to create temporary files.
        """
        temp_files: list[Path] = []

        try:
            cert_paths: dict[str, Path | None] = {}
            if self.kafka_config.use_ssl or self.kafka_config.use_sasl_ssl:
                temp_files, cert_paths = self._create_temp_cert_files()

            security_protocol: constants.SecurityProtocol = (
                self._determine_security_protocol()
            )
            conf: Mapping[str, str] = self._build_kafka_config(
                security_protocol,
                **cert_paths,
            )

            return conf, temp_files

        except binascii.Error as e:
            self._cleanup_temp_files(temp_files)
            raise exceptions.KafkaClientError(
                "Invalid certificate content. Please ensure the certificate values are "
                "valid base64 encoded strings."
            ) from e

        except ValueError as e:
            self._cleanup_temp_files(temp_files)
            raise exceptions.KafkaClientError(
                "Missing required configuration for the selected security protocol. "
                "Please check your settings (e.g., SASL credentials for SASL, "
                "CA certificate for SSL)."
            ) from e

        except (OSError, IOError, PermissionError) as e:
            self._cleanup_temp_files(temp_files)
            raise exceptions.KafkaClientError(
                f"Failed to create temporary certificate files: {e}"
            ) from e

    def test_connectivity(self) -> None:
        """Tests connectivity to the Kafka.

        Raises:
            KafkaConnectionError: If the connection to Kafka fails.
            KafkaClientError: If an unexpected error occurs.
        """
        conf: Mapping[str, str] = {}
        temp_files: list[Path] = []

        try:
            conf, temp_files = self._get_connection_config()
            admin_client: AdminClient = AdminClient(conf)
            brokers: dict[int, BrokerMetadata] = admin_client.list_topics(
                timeout=constants.DEFAULT_TIMEOUT,
            ).brokers
            self.logger.info(f"Successfully connected to Kafka cluster: {brokers}")

        except KafkaException as e:
            raise exceptions.KafkaConnectionError(
                "Unable to establish a connection. Please verify the broker list, "
                "network connectivity, credentials, and SSL/TLS configurations. "
            ) from e

        finally:
            self._cleanup_temp_files(temp_files)

    def _get_partitions_to_process(
        self,
        topic: str,
        initial_offsets: Mapping[int, int | None],
        conf: Mapping[str, str],
    ) -> set[int]:
        """Determines the set of partitions to be processed.

        Args:
            topic (str): The topic to consume from.
            initial_offsets (Mapping[int, int]): A map of partition to offset.
            conf (Mapping[str, str]): The Kafka client configuration.

        Returns:
            set[int]: A set of partition IDs.
        """
        if initial_offsets:
            return set(initial_offsets.keys())

        admin_client: AdminClient = AdminClient(conf)
        topic_metadata: TopicMetadata | None = admin_client.list_topics(
            topic,
            timeout=constants.DEFAULT_TIMEOUT,
        ).topics.get(topic)

        if not topic_metadata:
            raise exceptions.KafkaClientError(f"Topic '{topic}' not found.")

        return set(topic_metadata.partitions)

    def _calculate_seek_offset(
        self,
        consumer: Consumer,
        tp: TopicPartition,
        offset_reset_policy: str | int,
    ) -> int:
        """Calculates the offset to seek to for a given partition.

        Args:
            consumer (Consumer): The Kafka consumer instance.
            tp (TopicPartition): The topic partition.
            offset_reset_policy (str | int): The policy for starting offsets.

        Returns:
            int: The calculated offset.
        """
        try:
            low, high = consumer.get_watermark_offsets(
                tp,
                timeout=constants.DEFAULT_TIMEOUT,
            )

            try:
                return int(offset_reset_policy)
            except (ValueError, TypeError):
                return high if offset_reset_policy == "latest" else low

        except KafkaException as e:
            self.logger.warn(
                f"Could not get watermarks for partition {tp.partition}: {e}. "
                "It might be empty. Starting from offset 0."
            )

            return constants.EARLIEST_OFFSET_INT

    def _seek_to_initial_positions(
        self,
        consumer: Consumer,
        offset_reset_policy: str | int,
        next_offsets: MutableMapping[int, int],
    ) -> None:
        """Seeks partitions to their initial starting positions.

        Args:
            consumer (Consumer): The Kafka consumer instance.
            offset_reset_policy (str | int): The policy for starting offsets.
            next_offsets (MutableMapping[int, int]): The map of next offsets to update.
        """
        for tp in consumer.assignment():
            seek_to_offset: int | None = next_offsets.get(tp.partition)

            if seek_to_offset is None:
                seek_to_offset: int = self._calculate_seek_offset(
                    consumer,
                    tp,
                    offset_reset_policy,
                )

            try:
                topic_partition: TopicPartition = TopicPartition(
                    tp.topic,
                    tp.partition,
                    seek_to_offset,
                )
                consumer.seek(topic_partition)
                next_offsets[tp.partition] = seek_to_offset

            except KafkaException:
                if seek_to_offset == 0:
                    consumer.seek_to_end(tp)
                    next_offsets[tp.partition] = consumer.position(tp)

    def _assign_manual_partitions(
        self,
        topic: str,
        initial_offsets: Mapping[int, int | None],
        conf: Mapping[str, str],
    ) -> tuple[list[TopicPartition], dict[int, int]]:
        """Assigns consumer to partitions and seeks to the correct offsets.

        Args:
            topic (str): The topic to consume from.
            initial_offsets (dict[int, int]): A map of partition to offset.
            conf (Mapping[str, str]): The Kafka client configuration.

        Returns:
            tuple[list[TopicPartition], dict[int, int]]: A tuple containing the list of
            TopicPartitions to assign and the map of next offsets.
        """
        next_offsets: MutableMapping[int, int] = {
            k: v for k, v in initial_offsets.items() if v is not None
        }
        partitions_to_process: set[int] = self._get_partitions_to_process(
            topic,
            initial_offsets,
            conf,
        )

        partitions_to_assign: list[TopicPartition] = [
            TopicPartition(topic, p_id) for p_id in partitions_to_process
        ]

        return partitions_to_assign, next_offsets

    def _poll_messages(
        self,
        consumer: Consumer,
        alert_config: data_models.AlertConfig,
        max_alerts_to_fetch: int,
        next_offsets: MutableMapping[int, int],
        is_manual_offset: bool,
        poll_timeout: int,
    ) -> list[data_models.KafkaMessage]:
        """Polls for messages and processes them into KafkaMessage objects.

        Args:
            consumer (Consumer): The Kafka consumer instance.
            alert_config (data_models.AlertConfig): Configuration for parsing alerts.
            max_alerts_to_fetch (int): The maximum number of messages to fetch.
            next_offsets (MutableMapping[int, int]): The map of next offsets to update.
            is_manual_offset (bool): Whether manual offsets are being used.

        Returns:
            list[data_models.KafkaMessage]: A list of processed KafkaMessage objects.
        """
        messages: list[data_models.KafkaMessage] = []
        self.logger.info(f"Polling for up to {max_alerts_to_fetch} messages.")
        raw_messages: list[Message] = consumer.consume(
            num_messages=max_alerts_to_fetch,
            timeout=poll_timeout,
        )

        for raw_message in raw_messages:
            if raw_message is None:
                self.logger.info("Consumer timeout reached, no more messages.")
                break

            if raw_message.error():
                self.logger.error(f"Kafka Consumer error: {raw_message.error()}")
                continue

            if is_manual_offset:
                current_partition: int = raw_message.partition()
                current_offset: int = raw_message.offset()
                next_offsets[current_partition] = current_offset + 1

            messages.append(
                data_models.KafkaMessage(
                    raw_message=raw_message,
                    alert_config=alert_config,
                    logger=self.logger,
                )
            )

        return messages

    def _create_group_consumer(
        self,
        conf: Mapping[str, str],
        topic: str,
        group_id: str,
        offset_reset_policy: str | int,
    ) -> tuple[Consumer, dict[int, int]]:
        """Creates a consumer for group-based consumption.

        Args:
            conf (Mapping[str, str]): Base Kafka configuration.
            topic (str): Topic to consume from.
            group_id (str): Consumer group ID.
            offset_reset_policy (str | int): Policy for starting offsets.

        Returns:
            tuple[Consumer, dict[int, int]]: Consumer and empty offsets dict.
        """
        conf: dict = dict(conf)
        conf.update(
            {
                "group.id": group_id,
                "auto.offset.reset": offset_reset_policy,
                "enable.auto.commit": True,
            }
        )
        consumer: Consumer = Consumer(conf)
        consumer.subscribe([topic])

        admin_client: AdminClient = AdminClient(conf)
        topic_metadata: dict[str, TopicMetadata] = admin_client.list_topics(
            topic,
            timeout=constants.DEFAULT_TIMEOUT,
        ).topics

        if topic not in topic_metadata or topic_metadata.get(topic).error:
            raise exceptions.KafkaClientError(
                f"Topic '{topic}' not found or is invalid.",
            )

        return consumer, {}

    def _create_manual_consumer(
        self,
        conf: Mapping[str, str],
        topic: str,
        initial_offsets: Mapping[int, int | None],
    ) -> tuple[Consumer, list[TopicPartition], dict[int, int]]:
        """Creates a consumer for manual partition assignment.

        Args:
            conf (Mapping[str, str]): Base Kafka configuration.
            topic (str): Topic to consume from.
            initial_offsets (Mapping[int, int | None]): Initial partition offsets.

        Returns:
            tuple[Consumer, list[TopicPartition], dict[int, int]]:
            Consumer, partitions to assign, and next offsets map.
        """
        conf: dict = dict(conf)
        conf.update(
            {
                "group.id": f"manual-consumer-{uuid.uuid4()}",
                "enable.auto.commit": False,
            }
        )

        admin_client: AdminClient = AdminClient(conf)
        topic_metadata: dict[str, TopicMetadata] = admin_client.list_topics(
            topic,
            timeout=constants.DEFAULT_TIMEOUT,
        ).topics

        if topic not in topic_metadata or topic_metadata.get(topic).error:
            raise exceptions.KafkaClientError(
                f"Topic '{topic}' not found or is invalid.",
            )

        consumer: Consumer = Consumer(conf)
        partitions_to_assign, next_offsets = self._assign_manual_partitions(
            topic,
            initial_offsets,
            conf,
        )

        return consumer, partitions_to_assign, next_offsets

    @contextlib.contextmanager
    def _kafka_consumer_session(
        self,
        topic: str,
        group_id: str | None,
        initial_offsets: Mapping[int, int | None],
        offset_reset_policy: str | int,
    ) -> Generator[tuple[Consumer, dict[int, int]], None, None]:
        """A context manager for creating and cleaning up a Kafka consumer.

        Args:
            topic (str): The topic to consume from.
            group_id (str | None): The consumer group ID.
            initial_offsets (Mapping[int, int | None]): A map of partition to offset.
            offset_reset_policy (str | int): The policy for starting offsets.

        Yields:
            tuple[Consumer, dict[int, int]]: Consumer and next offsets map.

        Raises:
            exceptions.KafkaClientError: If there's a configuration error.
        """
        conf, temp_files = self._get_connection_config()
        consumer: Consumer | None = None
        try:
            if group_id:
                consumer, next_offsets = self._create_group_consumer(
                    conf,
                    topic,
                    group_id,
                    offset_reset_policy,
                )
            else:
                consumer, partitions_to_assign, next_offsets = (
                    self._create_manual_consumer(
                        conf,
                        topic,
                        initial_offsets,
                    )
                )
                if partitions_to_assign:
                    consumer.assign(partitions_to_assign)

            consumer.poll(timeout=constants.DEFAULT_TIMEOUT)

            if not group_id:
                self._seek_to_initial_positions(
                    consumer,
                    offset_reset_policy,
                    next_offsets,
                )

            yield consumer, next_offsets

        except ValueError as e:
            self._cleanup_temp_files(temp_files)
            raise exceptions.KafkaClientError(str(e)) from e

        finally:
            if consumer:
                consumer.close()
            self._cleanup_temp_files(temp_files)

    def consume_messages(
        self,
        topic: str,
        alert_config: data_models.AlertConfig,
        max_alerts_to_fetch: int,
        initial_offsets: Mapping[int, int | None],
        poll_timeout: int = constants.DEFAULT_TIMEOUT,
        group_id: str | None = None,
        offset_reset_policy: str | int = constants.EARLIEST_OFFSET_STR,
    ) -> KafkaConsumeResult:
        """Consume messages from a Kafka topic.

        Args:
            topic (str): The topic to consume messages from.
            alert_config (data_models.AlertConfig): Configuration for parsing alerts.
            max_alerts_to_fetch (int): The maximum number of messages to fetch.
            group_id (str | None): The consumer group ID, if any.
            initial_offsets (Mapping[int, int | None]): Manual initial offsets.
            offset_reset_policy (str | int): Policy for starting offsets.

        Returns:
            KafkaConsumeResult: A NamedTuple containing processed messages and the
                next offsets.

        Raises:
            KafkaConnectionError: If there is a connection issue.
            KafkaClientError: If an unexpected error occurs.
        """
        try:
            with self._kafka_consumer_session(
                topic,
                group_id,
                initial_offsets,
                offset_reset_policy,
            ) as (consumer, next_offsets):
                messages: list[data_models.KafkaMessage] = self._poll_messages(
                    consumer=consumer,
                    alert_config=alert_config,
                    max_alerts_to_fetch=max_alerts_to_fetch,
                    next_offsets=next_offsets,
                    is_manual_offset=group_id is None,
                    poll_timeout=poll_timeout,
                )
                return KafkaConsumeResult(messages=messages, next_offsets=next_offsets)

        except KafkaException as e:
            raise exceptions.KafkaConnectionError(
                "Unable to establish a connection. Please verify the broker list, "
                "network connectivity, credentials, and SSL/TLS configurations. "
            ) from e
