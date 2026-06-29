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
import json
import pathlib

from TIPCommon.types import SingleJson

from akamai_integration.core.datamodels import (
    AddItemsToNetworkList,
    ClientActivation,
    ClientList,
    ClientListItem,
    NetworkActivation,
    NetworkItemList,
    NetworkList,
    NetworkListActivation,
    RemoveItemsFromNetworkList,
)
from akamai_integration.core import data_parser
from integration_testing.common import get_def_file_content


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)
MOCK_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA: SingleJson = get_def_file_content(MOCK_PATH)
PING_RESPONSE: SingleJson = MOCK_DATA["ping"]
NETWORK_LIST_RESPONSE: SingleJson = MOCK_DATA["get_network_list"]
STAGING_NETWORK_RESPONSE: SingleJson = MOCK_DATA["env_staging_response"]
PRODUCTION_NETWORK_RESPONSE: SingleJson = MOCK_DATA["env_production_response"]
GET_ITEMS_RESPONSE: SingleJson = MOCK_DATA["get_items_response"]
GET_ACTIVATION_RESPONSE: SingleJson = MOCK_DATA["network_activation_response"]

NETWORK_LIST: NetworkList = NetworkList.from_json(
    NETWORK_LIST_RESPONSE["networkLists"][0],
)

NETWORK_STAGING_ACTIVATION: NetworkActivation = data_parser.build_network_activation(
    STAGING_NETWORK_RESPONSE,
)

NETWORK_PRODUCTION_ACTIVATION: NetworkActivation = NetworkActivation.from_json(
    PRODUCTION_NETWORK_RESPONSE,
)

NETWORK_ITEM_LIST: NetworkItemList = data_parser.build_network_item_list(
    GET_ITEMS_RESPONSE,
)

ADD_ITEMS_TO_NETWORK_LIST: AddItemsToNetworkList = AddItemsToNetworkList.from_json(
    NETWORK_LIST_RESPONSE,
)

REMOVE_ITEMS_TO_NETWORK_LIST: RemoveItemsFromNetworkList = (
    RemoveItemsFromNetworkList.from_json(NETWORK_LIST_RESPONSE)
)

NETWORK_ACTIVATION_LIST: NetworkItemList = NetworkItemList.from_json(
    GET_ACTIVATION_RESPONSE,
)

NETWORK_LIST_ACTIVATION: NetworkListActivation = NetworkListActivation.from_json(
    GET_ACTIVATION_RESPONSE,
)

GET_CLIENT_LISTS_SUCCESS_MOCK_DATA: SingleJson = MOCK_DATA.get(
    "get_client_lists_success",
)
ADD_ITEMS_TO_CLIENT_LIST_SUCCESS_MOCK_DATA: SingleJson = MOCK_DATA.get(
    "add_items_to_client_list_success",
)
REMOVE_ITEMS_FROM_CLIENT_LIST_SUCCESS_MOCK_DATA: SingleJson = MOCK_DATA.get(
    "remove_items_from_client_list_success",
)
ACTIVATE_CLIENT_LIST_MOCK_DATA: SingleJson = MOCK_DATA.get("activate_client_list")
ACTIVATE_CLIENT_LIST: ClientActivation = data_parser.build_client_activation(
    ACTIVATE_CLIENT_LIST_MOCK_DATA
)

CLIENT_LIST: ClientList = data_parser.build_client_list(
    GET_CLIENT_LISTS_SUCCESS_MOCK_DATA.get("content")[0],
)
ADD_CLIENT_LIST_ITEM: ClientListItem = (
    data_parser.build_client_list_items_update_result(
        ADD_ITEMS_TO_CLIENT_LIST_SUCCESS_MOCK_DATA.get("appended")[0],
    )
)
REMOVE_CLIENT_LIST_ITEM: ClientListItem = (
    data_parser.build_client_list_items_update_result(
        REMOVE_ITEMS_FROM_CLIENT_LIST_SUCCESS_MOCK_DATA.get("deleted")[0],
    )
)
INTEGRATION_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent
