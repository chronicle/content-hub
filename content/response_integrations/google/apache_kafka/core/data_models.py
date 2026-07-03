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

import dataclasses
import datetime
import hashlib
import json
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.transformation import dict_to_flat
from ..core import constants
from ..core import utils

if TYPE_CHECKING:
    from typing import Any, Callable

    from confluent_kafka import Message

    from soar_sdk.SiemplifyConnectorsDataModel import ConnectorInfo

    from TIPCommon.base.interfaces import EnvironmentHandle, ScriptLogger
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class AlertConfig:
    """Dataclass for alert creation and parsing configuration."""

    unique_id_field: str | None
    timestamp_field: str
    timestamp_format: str | None
    case_name_template: str | None
    alert_name_template: str | None
    rule_generator_template: str | None
    severity_mapping_json: SingleJson

    @property
    def default_severity(self) -> int:
        """Retrieves and validates the default severity from the mapping.

        Returns:
            int: The default severity value.

        """
        default_value: str | int | None = self.severity_mapping_json.get("Default")
        if default_value is None:
            raise ValueError(
                'Invalid "Severity Mapping JSON". "Default" value should always be '
                "present."
            )

        return utils.get_default_severity(default_value)

    @property
    def severity_mapping(self) -> dict[str, Callable[[str | None], int | None]]:
        return {
            key: utils.build_severity_transformation(value)
            for key, value in self.severity_mapping_json.items()
            if key != "Default"
        }


@dataclasses.dataclass
class KafkaMessage:
    """Represents a Kafka message ready to be a SOAR alert."""

    raw_message: Message
    alert_config: AlertConfig
    logger: ScriptLogger

    @property
    def message_payload(self) -> SingleJson | None:
        """Safely decodes the message value into a JSON object.

        Args:
            raw_message (Message): The raw message object from Kafka.

        Returns:
            SingleJson | None: A JSON object or None if decoding fails.
        """
        try:
            return json.loads(self.raw_message.value().decode("utf-8"))
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):

            return None

    @property
    def event_json(self) -> SingleJson:
        """Constructs the event JSON from a raw Kafka message.

        Returns:
            SingleJson: A dictionary representing the event.
        """
        kafka_metadata: SingleJson = {
            "topic": self.raw_message.topic(),
            "partition": self.raw_message.partition(),
            "offset": self.raw_message.offset(),
            "timestamp": self.raw_message.timestamp()[1],
            "key": (
                self.raw_message.key().decode("utf-8")
                if self.raw_message.key()
                else None
            ),
            "headers": (
                {
                    key: value.decode("utf-8", "replace")
                    for key, value in self.raw_message.headers()
                }
                if self.raw_message.headers()
                else {}
            ),
        }

        return {
            **kafka_metadata,
            "data": (
                self.message_payload
                if self.message_payload is not None
                else self.raw_message.value().decode("utf-8", errors="replace")
            ),
        }

    @property
    def severity(self) -> int:
        """Get SOAR alert severity.

        Returns:
            (int): An integer representing the alert severity.
        """
        flat_: SingleJson = dict_to_flat(self.event_json)
        for key, transformation in self.alert_config.severity_mapping.items():
            if key in flat_:
                value_ = transformation(flat_[key])
                if value_ is not None:
                    return value_

        return self.alert_config.default_severity

    @property
    def alert_id(self) -> str:
        """A unique ID for the alert.

        Returns:
            str: A unique string identifier for the alert.
        """
        unique_id: Any = utils.get_field_from_payload(
            self.event_json,
            self.alert_config.unique_id_field,
        )

        if not unique_id:
            return hashlib.sha256(self.raw_message.value()).hexdigest()

        return str(unique_id)

    @property
    def timestamp(self) -> int:
        """Extracts the timestamp from a message.

        Args:
            raw_message (Message): The raw message object from Kafka.
            alert_config (data_models.AlertConfig): Config for parsing the message.
            event_json (SingleJson): The event json object.

        Returns:
            int: The event timestamp in milliseconds.
        """
        try:
            timestamp_: Any | None = utils.get_field_from_payload(
                self.event_json,
                self.alert_config.timestamp_field,
            )

            if timestamp_ is None:
                raise ValueError(
                    f"Timestamp field '{self.alert_config.timestamp_field}' not found"
                )

            if isinstance(timestamp_, (int, float)):
                return int(timestamp_)

            if isinstance(timestamp_, str):
                if timestamp_.isnumeric():
                    return int(timestamp_)

            if not self.alert_config.timestamp_format:
                raise ValueError(
                    'Not a valid timestamp and no "Timestamp Format" was provided.'
                )

            return int(
                datetime.datetime.strptime(
                    timestamp_, self.alert_config.timestamp_format
                ).timestamp()
                * NUM_OF_MILLI_IN_SEC
            )

        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(
                f"Unable to resolve field {self.alert_config.timestamp_field}. "
                f"Error is :{e}"
            ) from e

    @property
    def alert_name(self) -> str:
        return utils.format_template(
            self.alert_config.alert_name_template,
            self.event_json,
        )

    @property
    def case_name(self) -> str:
        return utils.format_template(
            self.alert_config.case_name_template,
            self.event_json,
        )

    @property
    def rule_generator(self) -> str:
        return utils.format_template(
            self.alert_config.rule_generator_template,
            self.event_json,
        )

    def to_alert_info(
        self,
        environment_common: EnvironmentHandle,
        connector_info: ConnectorInfo,
        alert_name_template: str,
        rule_generator_template: str,
        source_grouping_identifier: str,
    ) -> AlertInfo:
        """Builds a SOAR AlertInfo object from the Kafka message.

        Args:
            environment_common: The environment common object for environment mapping.
            connector_info: The connector's information object.
            alert_name_template (str): The template for the alert name.
            rule_generator_template (str): The template for the rule generator.
            source_grouping_identifier (str): The identifier for source grouping.

        Returns:
            AlertInfo: A fully populated AlertInfo object.
        """

        alert_info: AlertInfo = AlertInfo()
        flat_event: SingleJson = dict_to_flat(self.event_json)

        alert_info.environment = environment_common.get_environment(flat_event)
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = (
            f"ApacheKafka_{self.alert_id}_{connector_info.identifier}"
        )
        alert_info.device_vendor = constants.VENDOR
        alert_info.device_product = constants.PRODUCT
        alert_info.name = self.alert_name or alert_name_template.format(
            connector_name=connector_info.display_name
        )
        alert_info.rule_generator = (
            self.rule_generator
            or rule_generator_template.format(
                connector_name=connector_info.display_name
            )
        )
        alert_info.priority = self.severity
        alert_info.source_grouping_identifier = source_grouping_identifier
        alert_info.end_time = alert_info.start_time = self.timestamp
        flat_event["custom_case_name"] = self.case_name
        alert_info.events = [flat_event]

        return alert_info
