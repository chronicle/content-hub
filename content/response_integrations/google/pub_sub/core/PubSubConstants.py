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
INTEGRATION_IDENTIFIER = "PubSub"
INTEGRATION_DISPLAY_NAME = "Pub/Sub"

PING_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Ping"

PUB_SUB_CONNECTOR_SCRIPT_NAME = f"{INTEGRATION_IDENTIFIER} - Messages Connector"

PUB_SUB_PULL_TIMEOUT = 45
DEFAULT_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform"
]
CONNECTOR_SUB_NAME_FORMAT = "soar_pub_sub_connector_{identifier}_sub"
CONNECTOR_DISPLAY_ID_TEMPLATE = (
    "Pub/Sub_{alert_id}_{connector_identifier}"
)
VENDOR = "Pub/Sub"
PRODUCT = "Message"
ALERT_NAME = "{connector_name} - Alert"
RULE_GENERATOR = "{connector_name} - Rule Generator"
