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

MAX_MESSAGES_TO_FETCH: int = 10
DEFAULT_TIMEOUT: int = 1
SEVERITY_MAPPING_JSON_DEFAULT: str = '{"Default": "Info"}'

TEST_CONSUMER_GROUP_ID: str = "test_group"

TEST_INITIAL_OFFSET_AS_STR: str = "123"
TEST_INITIAL_OFFSET_AS_INT: int = 123
TEST_PARTITIONS: list[int] = [1, 2]

VALIDATE_JSON_FUCTION_NAME: str = "validate_json"

VALIDATE_CSV_FUCTION_NAME: str = "validate_csv"
TEST_PARTITIONS_PARAM_VALUE: str = "1,2,3"
TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR: list[str] = ["1", "2", "3"]
TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_INT: list[int] = [1, 2, 3]

TEST_PARTITIONS_PARAM_VALUE_INVALID: str = "1,a,3"
TEST_PARTITIONS_PARAM_VALUE_AS_LIST_IN_STR_INVALID: list[str] = ["1", "a", "3"]

OFFSET_PARAM_NAME: str = "offset"
OFFSET_PARAM_POSSIBLE_VALUES: list[str] = ["123", "earliest", "latest"]
VALIDATE_NON_NEGATIVE_FUCTION_NAME: str = "validate_non_negative"
INITIAL_OFFSET_PARAM_INVALID_VALUE: str = "invalid"
INITIAL_OFFSET_EARLIEST: str = "earliest"

TEST_KAFKA_BROKERS: str = "server"
TEST_KAFKA_USERNAME: str = "user"
TEST_KAFKA_PASSWORD: str = "pass"
TEST_KAFKA_CA: str = "ca"
TEST_KAFKA_CLIENT_CERT: str = "cert"
TEST_KAFKA_CLIENT_CERT_KEY: str = "key"
TEST_KAFKA_CLIENT_CERT_KEY_PASSWORD: str = "keypass"

TEST_BOOTSTRAP_SERVERS: str = "localhost:9092"

TEST_CA_CERT_CONTENT_BYTES: bytes = b"ca_cert"
TEST_CLIENT_CERT_CONTENT_BYTES: bytes = b"client_cert"
TEST_CLIENT_KEY_CONTENT_BYTES: bytes = b"client_key"

TEST_CA_PATH: str = "/tmp/ca.pem"
TEST_CLIENT_CERT_PATH: str = "/tmp/client.pem"
TEST_CLIENT_KEY_PATH: str = "/tmp/client.key"
TEST_TEMP_FILE_PATH: str = "/tmp/temp_file.pem"

TEST_TOPIC_NON_EXISTENT: str = "non_existent_topic"

TEST_INITIAL_OFFSETS: dict[int, int] = {0: 10, 1: 20}

TEST_KAFKA_MESSAGES: list[str] = ["fake_message"]
TEST_KAFKA_OFFSETS: dict[int, int] = {1: 123, 2: 456}

TEST_UNIQUE_ID_FIELD: str = "id"
TEST_TIMESTAMP_FIELD: str = "time"
TEST_TIMESTAMP_FORMAT: str = "format"
TEST_CASE_NAME_TEMPLATE: str = "case"
TEST_ALERT_NAME_TEMPLATE: str = "alert"
TEST_SEVERITY_MAPPING_DEFAULT_DICT: dict[str, str] = {"Default": "Info"}
TEST_RULE_GENERATOR_TEMPLATE: str = "rule"
TEST_TOPIC: str = "test_topic"

PREPARE_INITIAL_OFFSET_METHOD_NAME: str = "_prepare_initial_offsets"
GET_ALERTS_METHOD_NAME: str = "get_alerts"
INIT_MANAGERS_METHOD_NAME: str = "init_managers"

FIRST_MESSAGE_INDEX: int = 0

TEST_LAST_RUN_DATA: dict[str, dict[int, int] | str] = {
    "topic_name": TEST_TOPIC,
    "offsets": TEST_KAFKA_OFFSETS,
}
