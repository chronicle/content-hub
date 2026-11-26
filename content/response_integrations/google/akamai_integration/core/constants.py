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

from collections.abc import Mapping, Sequence

INTEGRATION_NAME: str = "Akamai"
PING_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Ping"
ACTIVATE_NETWORK_LIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Activate Network List"
ACTIVATE_CLIENT_LIST_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Activate Client List"
ADD_ITEMS_TO_CLIENT_LISTS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Items To Client Lists"
)
ADD_ITEMS_TO_NETWORK_LISTS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Add Items To Network List"
)
GET_CLIENT_LISTS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Client Lists"
GET_NETWORK_LISTS_SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Get Network Lists"
REMOVE_ITEMS_FROM_CLIENT_LISTS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Remove Items From Client Lists"
)
REMOVE_ITEMS_FROM_NETWORK_LISTS_SCRIPT_NAME: str = (
    f"{INTEGRATION_NAME} - Remove Items From Network List"
)

COULD_NOT_BE_FOUND_ERR_LIST: Sequence[str] = [
    "could not be found",
    "should be of the format",
]

ITEM_NOT_FOUND: str = "is not part of this list"

ENDPOINTS: Mapping[str, str] = {
    "get_contracts": "/network-list/v2/network-lists?limit=1",
    "get_networks": "/network-list/v2/network-lists",
    "get_network_list_activation": (
        "/network-list/v2/network-lists/{network_list_id}/"
        "environments/{environment}/status"
    ),
    "item_list": "/network-list/v2/network-lists/{network_list_id}",
    "add_items_to_network_list": (
        "/network-list/v2/network-lists/{network_list_id}/append"
    ),
    "remove_item_from_network_list": (
        "/network-list/v2/network-lists/{network_list_id}/elements?element={item}"
    ),
    "get_client_lists": "/client-list/v1/lists?includeItems={include_items}",
    "update_items_in_client_list": "/client-list/v1/lists/{list_id}/items",
    "activate_network_list": (
        "/network-list/v2/network-lists/{network_list_id}/"
        "environments/{environment}/activate"
    ),
    "activate_client_list": "/client-list/v2/lists/{list_id}/activations",
}

NOT_FOUND_ERROR_MSG: str = "wasn't found"
INVALID_TOKEN_ERROR: str = "invalid token."
FAILED_TO_TAKE_REQUEST_DOWN_ERR: str = "failed to take action `request_takedown`"
DEFAULT_RESULTS_TO_RETURN: int = 100
CERTIFICATE_VERIFY_FAILED: str = (
    "certificate verify failed: unable to get local issuer certificate"
)

ENV_LIST: Sequence[str] = ["Both", "Production", "Staging"]

LIST_TYPE_FOR_ALL: str = "Select One"
LIST_ITEMS: str = "items"
NETWORK_LIST_NOT_FOUND: str = "network list wasn't found in Akamai."
CLIENT_LIST_NOT_FOUND: str = "client list wasn't found in Akamai."

CLIENT_LIST_TYPE_MAPPING: Mapping[str, str] = {
    "Select One": "Select One",
    "IP": "IP",
    "GEO": "GEO",
    "ASN": "ASN",
    "TLS Fingerprint": "TLS_FINGERPRINT",
    "File Hash": "FILE_HASH",
}

MINIMUM_POSITIVE_INTEGER: int = 1

ERROR_LIST: Sequence[str] = [
    "certificate_verify_failed",
    "invalid authorization",
]

CLIENT_LIST_NOT_FOUND: str = "client list wasn't found in Akamai."
ACTIVATION_ENVIRONMENTS: Sequence[str] = ["Production", "Staging"]
API_ENVIRONMENTS: Mapping[str, str] = {"Production": "PRODUCTION", "Staging": "STAGING"}
STAGE_ACTIVATION: Sequence[str] = ["Both", "Staging"]
PROD_ACTIVATION: Sequence[str] = ["Both", "Production"]
