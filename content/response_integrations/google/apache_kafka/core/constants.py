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
from enum import Enum


INTEGRATION_NAME: str = "Apache Kafka"
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"

INTEGRATION_IDENTIFIER: str = "ApacheKafka"
KAFKA_CONNECTOR_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Messages Connector"
VENDOR: str = "Apache Kafka"
PRODUCT: str = "Message"
ALERT_NAME: str = "{connector_name} - Alert"
RULE_GENERATOR: str = "{connector_name} - Rule Generator"
CONNECTOR_DISPLAY_ID_TEMPLATE: str = "ApacheKafka_{alert_id}_{connector_identifier}"

CONTEXT_FILENAME: str = "context.json"
CONTEXT_DB_KEY: str = "context"

INVALID_PARTITION: int = -1
INVALID_OFFSET: int = -1001
EARLIEST_OFFSET_INT: int = 0
EARLIEST_OFFSET_STR: str = "earliest"
LATEST_OFFSET_STR: str = "latest"
DEFAULT_TIMEOUT: int = 5

SEVERITY_MAPPING_DEFAULT_KEY: str = "Default"
SASL_PROTOCOL_PREFIX: str = "SASL_"
PLAINTEXT_PROTOCOL: str = "PLAIN"


class SecurityProtocol(Enum):
    PLAINTEXT: str = "PLAINTEXT"
    SASL_PLAINTEXT: str = "SASL_PLAINTEXT"
    SASL_SSL: str = "SASL_SSL"
    SSL: str = "SSL"
