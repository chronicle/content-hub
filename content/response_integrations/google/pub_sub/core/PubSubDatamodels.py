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

import copy
import datetime
import json
import hashlib
from typing import Any, Callable, Optional
import dataclasses

from TIPCommon.adapters.pubsub.data_models import ReceivedMessage
from TIPCommon.base.utils import NewLineLogger
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson

from ..core.PubSubExceptions import PubSubInvalidJsonException
from ..core.PubSubUtils import (
    get_default_severity,
    build_severity_transformation,
    transform_template_string,
)


@dataclasses.dataclass(frozen=True)
class AlertConfig:
    unique_id_field: str | None
    timestamp_field: str
    timestamp_format: str | None
    case_name_template: str | None
    alert_name_template: str | None
    rule_generator_template: str | None
    severity_mapping_json: SingleJson

    @property
    def default_severity(self) -> int:
        return get_default_severity(self.severity_mapping_json["Default"])

    @property
    def severity_mapping(self) -> dict[str, Callable[[Optional[str]], int | None]]:
        return {
            key: build_severity_transformation(value)
            for key, value in self.severity_mapping_json.items()
            if key != "Default"
        }

@dataclasses.dataclass
class PubSubMessage:
    message: ReceivedMessage
    alert_config: AlertConfig
    logger: NewLineLogger

    _json_payload: SingleJson | None = None
    _flat: SingleJson | None = None

    @property
    def json_payload(self) -> SingleJson:
        """Return JSON payload of the message."""
        if self._json_payload is not None:
            return self._json_payload

        try:
            self._json_payload = json.loads(self.message.message.data)
            return self._json_payload
        except json.JSONDecodeError as e:
            raise PubSubInvalidJsonException(
                "Unable to unmarshall received message, error is {e}"
            ) from e

    def json(self) -> SingleJson:
        """Return JSON payload of the message."""
        json_ = copy.deepcopy(self.message.json())
        json_["message"]["data"] = self.message.message.data

        try:
            json_["message"]["json"] = self.json_payload
        except PubSubInvalidJsonException as e:
            self.logger.error(f"Can't assign Json payload, error is: {e}")

        return json_

    def flat(self) -> SingleJson:
        """Build flat JSON from message payload."""
        if self._flat is None:
            self._flat = dict_to_flat(self.json())
        return self._flat

    def get_severity(self) -> int | float:
        """Get SOAR alert severity."""
        flat_ = self.flat()
        for key, transformation in self.alert_config.severity_mapping.items():
            if key in flat_:
                value_ = transformation(flat_[key])
                if value_ is not None:
                    return value_

        return self.alert_config.default_severity

    @property
    def timestamp(self) -> int:
        """Retrieve timestamp from message payload."""
        try:
            timestamp_ = self.get_field_from_payload(
                self.alert_config.timestamp_field
            )
            if timestamp_.isnumeric():
                return int(timestamp_)

            if not self.alert_config.timestamp_format:
                raise ValueError(
                    "data is not a valid timestamp and no \"Timestamp Format\" "
                    "was provided."
                )

            return int(
                datetime.datetime.strptime(
                    timestamp_,
                    self.alert_config.timestamp_format
                ).timestamp()
                * NUM_OF_MILLI_IN_SEC
            )

        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(
                f"Unable to resolve field {self.alert_config.timestamp_field}."
                f" Error is {e}"
            ) from e

    def get_field_from_payload(self, field_name: str) -> Any:
        return self.flat().get(field_name)

    @property
    def alert_id(self) -> str:
        return (
            self.get_field_from_payload(self.alert_config.unique_id_field)
            or (
                hashlib.sha256(self.message.message.data.encode("utf-8"))
                .hexdigest()
            )
        )

    @property
    def alert_name(self) -> str:
        return transform_template_string(
            self.alert_config.alert_name_template,
            self.flat()
        )

    @property
    def case_name(self) -> str:
        return transform_template_string(
            self.alert_config.case_name_template,
            self.flat()
        )

    @property
    def rule_generator(self) -> str:
        return transform_template_string(
            self.alert_config.rule_generator_template,
            self.flat()
        )
