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
from typing import TYPE_CHECKING

from TIPCommon.base.connector import Connector
from TIPCommon.consts import STORED_IDS_LIMIT
from TIPCommon.exceptions import ConnectorSetupError, ParameterValidationError
from TIPCommon.filters import filter_old_alerts
from TIPCommon.smp_io import read_content, write_content
from TIPCommon.utils import is_test_run
from ..core import constants
from ..core.config_models import KafkaConfigurationParameters
from ..core import data_models
from ..core.kafka_manager import KafkaClient

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, MutableMapping, Sequence

    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

    from TIPCommon.types import SingleJson


class KafkaMessagesConnector(Connector):
    def __init__(self, test_run: bool = False) -> None:
        """Initializes a new KafkaMessagesConnector instance."""
        super().__init__(constants.KAFKA_CONNECTOR_SCRIPT_NAME, is_test_run=test_run)
        self.manager: KafkaClient | None = None
        self.next_offsets: MutableMapping[int, int | None] = {}

    def _validate_general_params(self) -> None:
        """Validate general connector parameters."""
        self.params.max_messages_to_fetch = self.param_validator.validate_positive(
            "Max Messages To Fetch",
            self.params.max_messages_to_fetch,
        )
        self.params.poll_timeout = self.param_validator.validate_positive(
            "Poll Timeout (Seconds)",
            self.params.poll_timeout,
        )
        self.params.severity_mapping_json = self.param_validator.validate_json(
            "Severity Mapping JSON",
            self.params.severity_mapping_json,
        )

        if (
            constants.SEVERITY_MAPPING_DEFAULT_KEY
            not in self.params.severity_mapping_json
        ):
            raise ConnectorSetupError(
                'Invalid parameter "Severity Mapping JSON". '
                '"Default" value must be specified.'
            )

    def _validate_offset_management_params(self) -> None:
        """Validate parameters related to offset management."""
        if self.params.consumer_group_id and (
            self.params.initial_offset or self.params.partitions
        ):
            raise ConnectorSetupError(
                "When 'Consumer Group ID' is provided, offset management is handled by "
                "Kafka. The parameters 'Initial Offset' and 'Partitions' "
                "should not be set."
            )

    def _validate_and_parse_partitions(self) -> None:
        """Validate and parse the 'Partitions' parameter."""
        if self.params.partitions:
            partitions_list: Sequence[str] = self.param_validator.validate_csv(
                "Partitions",
                self.params.partitions,
            )
            parsed_partitions: list[int] = []
            invalid_partitions: list[str] = []

            for p in partitions_list:
                try:
                    partition_num: int = self.param_validator.validate_non_negative(
                        "Partition",
                        p,
                    )
                    parsed_partitions.append(partition_num)

                except ParameterValidationError:
                    invalid_partitions.append(p)

            if invalid_partitions:
                raise ConnectorSetupError(
                    "Invalid format for 'Partitions To Consume'. "
                    "The following partition numbers are invalid (must be non-negative "
                    f"integers): {', '.join(invalid_partitions)}"
                )
            self.params.partitions = parsed_partitions

    def _validate_initial_offset(self) -> None:
        """Validate the 'Initial Offset' parameter."""
        if self.params.initial_offset:
            try:
                self.param_validator.validate_non_negative(
                    "Initial Offset",
                    self.params.initial_offset,
                )
            except ParameterValidationError as e:
                if self.params.initial_offset.lower() not in [
                    constants.EARLIEST_OFFSET_STR,
                    constants.LATEST_OFFSET_STR,
                ]:
                    raise ConnectorSetupError(
                        "Invalid value for 'Initial Offset'. "
                        "It must be a non-negative integer, 'earliest', or 'latest'."
                    ) from e

    def validate_params(self) -> None:
        """Validate connector parameters."""
        self._validate_general_params()
        self._validate_offset_management_params()
        self._validate_and_parse_partitions()
        self._validate_initial_offset()

    def init_managers(self) -> None:
        """Initialize the KafkaClient."""
        kafka_config: KafkaConfigurationParameters = KafkaConfigurationParameters(
            bootstrap_servers=self.params.kafka_brokers,
            use_ssl=self.params.use_tls_for_connection,
            use_sasl_ssl=self.params.use_saslplain_with_tls_for_connection,
            sasl_username=self.params.saslplain_username,
            sasl_password=self.params.saslplain_password,
            ca_certificate=self.params.ca_certificate_of_kafka_server,
            client_certificate=self.params.client_certificate,
            client_certificate_key=self.params.client_certificate_key,
            client_certificate_key_password=(
                f"{self.params.client_certificate_key_password}"
            ),
        )

        self.manager = KafkaClient(kafka_config=kafka_config, logger=self.logger)

    def _get_offsets_from_initial_offset_param(self) -> dict[int, int | None]:
        """Builds an offset mapping based on the 'Initial Offset' and 'Partitions'
        parameters. Assumes that both parameters have been validated to exist.

        Returns:
            dict[int, int | None]: A dict of partition numbers to offsets.
        """
        initial_offsets: MutableMapping[int, int | None] = {}

        try:
            start_offset: int = int(self.params.initial_offset)
            for p in self.params.partitions:
                initial_offsets[p] = start_offset

        except ValueError:
            for p in self.params.partitions:
                initial_offsets[p] = None

        return initial_offsets

    def _get_offsets_for_user_partitions(self) -> dict[int, int | None]:
        """Handle the logic when user-specified partitions are provided.

        Returns:
            dict[int, int | None]: A dict of partition numbers to offsets.
                An empty dict is returned if no partitions are provided.
        """
        self.logger.info(
            f"User specified partitions {self.params.partitions}. No initial "
            "offset provided. Will use saved offsets if available."
        )
        saved_offsets: Mapping[int, int | None] = self.context.last_run_data.get(
            "offsets",
            {},
        )

        if saved_offsets and all(
            isinstance(k, str) and k.isdigit() for k in saved_offsets
        ):
            saved_offsets: dict[int, int | None] = {
                int(k): v for k, v in saved_offsets.items()
            }

        return {p: saved_offsets.get(p) for p in self.params.partitions}

    def _get_offsets_from_last_run(self) -> dict[int, int | None] | None:
        """Handle resuming from previously saved offsets.

        Returns:
            dict[int, int | None] | None: A dict of partition numbers to offsets.
                None is returned if the topic has changed, or if no saved offsets
                are found for the current topic.
        """
        if self.context.last_run_data.get("topic_name") != self.params.topic:
            return None

        saved_offsets: Mapping[int, int | None] = self.context.last_run_data.get(
            "offsets",
            {},
        )

        if saved_offsets and all(
            isinstance(k, str) and k.isdigit() for k in saved_offsets
        ):
            return {int(k): v for k, v in saved_offsets.items()}

        if saved_offsets:
            return saved_offsets

        return None

    def _prepare_initial_offsets(self) -> dict[int, int | None]:
        """Prepares the initial offsets for manual partition assignment.

        Returns:
            dict[int, int | None]: A dictionary mapping partition numbers to specific
            starting offsets. An empty dictionary is returned when using consumer group
            management or when the consumer should subscribe to all partitions and use
            the global offset reset policy.
        """
        if self.params.consumer_group_id:
            return {}

        if self.params.partitions:
            offsets: Mapping[int, int | None] = self._get_offsets_for_user_partitions()
            if offsets is not None:
                return offsets

        offsets: Mapping[int, int | None] = self._get_offsets_from_last_run()
        if offsets is not None:
            return offsets

        if self.params.initial_offset and self.params.partitions:
            self.logger.info(
                f"First run or topic changed. Using user-provided 'Initial Offset' "
                f"('{self.params.initial_offset}') for specified partitions "
                f"{self.params.partitions}."
            )
            return self._get_offsets_from_initial_offset_param()

        if self.params.initial_offset:
            self.logger.info(
                f"First run or topic changed. Using user-provided 'Initial Offset' "
                f"('{self.params.initial_offset}') for all partitions, as no "
                "specific partitions were provided."
            )
            return {}

        offset_policy: str = self.params.initial_offset or constants.EARLIEST_OFFSET_STR
        self.logger.info(
            "No saved offsets found and no specific partitions provided. "
            "The consumer will subscribe to all partitions and start based on the "
            f"effective offset policy: '{offset_policy}'."
        )

        return {}

    def get_alerts(self) -> list[data_models.KafkaMessage]:
        """Fetch new messages from the Kafka topic.

        Returns:
            messages (list[data_models.KafkaMessage]): An list of KafkaMessage
                objects.
        """
        alert_config = data_models.AlertConfig(
            unique_id_field=self.params.unique_id_field,
            timestamp_field=self.params.timestamp_field,
            timestamp_format=self.params.timestamp_format,
            case_name_template=self.params.case_name_template,
            alert_name_template=self.params.alert_name_template,
            rule_generator_template=self.params.rule_generator_template,
            severity_mapping_json=self.params.severity_mapping_json,
        )

        initial_offsets: Mapping[int, int | None] = self._prepare_initial_offsets()

        messages, self.next_offsets = self.manager.consume_messages(
            topic=self.params.topic,
            alert_config=alert_config,
            max_alerts_to_fetch=self.params.max_messages_to_fetch,
            poll_timeout=self.params.poll_timeout,
            group_id=self.params.consumer_group_id,
            initial_offsets=initial_offsets,
            offset_reset_policy=self.params.initial_offset
            or constants.EARLIEST_OFFSET_STR,
        )

        return messages

    def filter_alerts(
        self,
        fetched_alerts: Iterable[data_models.KafkaMessage],
    ) -> list[data_models.KafkaMessage]:
        """Filters out alerts that have already been processed."""
        return filter_old_alerts(
            self.siemplify,
            fetched_alerts,
            self.context.existing_ids,
            "alert_id",
        )

    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if the alert is an overflow alert."""
        return not self.params.disable_overflow and super().is_overflow_alert(
            alert_info
        )

    def read_context_data(self) -> None:
        """Read context data like last run offsets and existing alert IDs."""
        self.logger.info("Reading context data (offsets and existing IDs)...")
        context_data: SingleJson = read_content(
            self.siemplify,
            file_name=constants.CONTEXT_FILENAME,
            db_key=constants.CONTEXT_DB_KEY,
            default_value_to_return={},
        )
        self.context.existing_ids = context_data.get("ids", [])
        self.context.last_run_data = context_data.get("last_run_data", {})

    def write_context_data(self, alerts: list[data_models.KafkaMessage]) -> None:
        """Write context data, including next offsets and processed alert IDs.

        Args:
            alerts(list[data_models.KafkaMessage]): List of KafkaMessage objects
                that were processed in the current run.
        """
        self.context.existing_ids = self.context.existing_ids[-STORED_IDS_LIMIT:]

        context_to_save: SingleJson = {
            "ids": self.context.existing_ids,
            "last_run_data": {},
        }

        if self.next_offsets:
            self.logger.info("Updating offsets for manual offset management.")
            last_run_offsets: MutableMapping[int, int] = self.context.last_run_data.get(
                "offsets",
                {},
            )

            if last_run_offsets and all(
                isinstance(k, str) and k.isdigit() for k in last_run_offsets
            ):
                last_run_offsets = {int(k): v for k, v in last_run_offsets.items()}

            last_run_offsets.update(self.next_offsets)

            context_to_save["last_run_data"]["topic_name"] = self.params.topic
            context_to_save["last_run_data"]["offsets"] = last_run_offsets

        if alerts or self.next_offsets or self.context.last_run_data:
            self.logger.info("Saving context data (offsets and/or IDs).")
            write_content(
                self.siemplify,
                context_to_save,
                file_name=constants.CONTEXT_FILENAME,
                db_key=constants.CONTEXT_DB_KEY,
            )

    def store_alert_in_cache(self, alert: data_models.KafkaMessage) -> None:
        """Store a processed alert's ID in the cache to prevent duplicates."""
        self.context.existing_ids.append(alert.alert_id)

    def create_alert_info(self, alert: data_models.KafkaMessage) -> AlertInfo:
        """Create a SOAR AlertInfo object from a Kafka message.

        Args:
            alert(data_models.KafkaMessage): The KafkaMessage object to convert.

        Returns:
            A Siemplify AlertInfo object.
        """
        return alert.to_alert_info(
            environment_common=self.env_common,
            connector_info=self.siemplify.context.connector_info,
            alert_name_template=constants.ALERT_NAME,
            rule_generator_template=constants.RULE_GENERATOR,
            source_grouping_identifier=self.params.topic,
        )


if __name__ == "__main__":
    is_test: bool = is_test_run(sys.argv)
    connector: KafkaMessagesConnector = KafkaMessagesConnector(test_run=is_test)
    connector.start()
