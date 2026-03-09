# Copyright 2025 Google LLC
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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def build_upgrade_connector_instance_payload(
    connector_instance: SingleJson,
    latest_definition: SingleJson,
    integration_details: SingleJson,
) -> SingleJson:
    """Build payload for upgrading a connector instance.

    Args:
        connector_instance(SingleJson): Current connector instance details.
        latest_definition(SingleJson): Latest connector definition details.
        integration_details(SingleJson): Integration details.

    Returns:
        SingleJson: Payload dictionary for upgrading the connector instance.
    """
    parameters: list[SingleJson] = [
        {
            "displayName": param["displayName"],
            "value": param.get("value", ""),
        }
        for param in latest_definition.get("parameters", [])
    ]

    payload: SingleJson = {
        "name": connector_instance["name"],
        "id": str(connector_instance["id"]),
        "enabled": latest_definition.get("enabled", connector_instance.get("enabled")),
        "environment": latest_definition.get(
            "environment", connector_instance.get("environment")
        ),
        "displayName": connector_instance["displayName"],
        "description": connector_instance.get("description", ""),
        "intervalSeconds": latest_definition.get(
            "intervalSeconds",
            connector_instance.get("intervalSeconds"),
        ),
        "allowList": latest_definition.get("allowList", []),
        "productFieldName": connector_instance.get("productFieldName"),
        "eventFieldName": connector_instance.get("eventFieldName"),
        "timeoutSeconds": str(connector_instance.get("timeoutSeconds", 0)),
        "integrationVersion": integration_details["version"],
        "parameters": parameters,
    }

    return payload
