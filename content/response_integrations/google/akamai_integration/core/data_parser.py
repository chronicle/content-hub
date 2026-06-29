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

from collections.abc import Iterable
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


def build_network_lists(raw_data: SingleJson) -> Iterable[NetworkList]:
    return [
        build_network_list(raw_data=network_json)
        for network_json in raw_data["networkLists"]
    ]


def build_network_list(raw_data: SingleJson) -> NetworkList:
    return NetworkList.from_json(network_json=raw_data)


def build_network_activation(raw_data: SingleJson) -> NetworkActivation:
    return NetworkActivation.from_json(activation_json=raw_data)


def build_client_activation(raw_data: SingleJson) -> ClientActivation:
    return ClientActivation.from_json(activation_json=raw_data)


def build_network_item_list(raw_data: SingleJson) -> NetworkItemList:
    return NetworkItemList.from_json(item_list_json=raw_data)


def build_add_items_to_network_list(raw_data: SingleJson) -> AddItemsToNetworkList:
    return AddItemsToNetworkList.from_json(add_items_json=raw_data)


def build_remove_items_from_network_list(
    raw_data: SingleJson,
) -> RemoveItemsFromNetworkList:
    return RemoveItemsFromNetworkList.from_json(remove_items_json=raw_data)


def build_client_lists(raw_data: SingleJson) -> Iterable[ClientList]:
    return [
        build_client_list(raw_data=client_list_json)
        for client_list_json in raw_data.get("content", [])
    ]


def build_client_list(raw_data: SingleJson) -> ClientList:
    return ClientList.from_json(client_list_json=raw_data)


def build_client_list_items_append_result_list(
    raw_data: SingleJson,
) -> Iterable[ClientListItem]:
    return [
        build_client_list_items_update_result(raw_data=client_list_item)
        for client_list_item in raw_data.get("appended", [])
    ]


def build_client_list_items_delete_result_list(
    raw_data: SingleJson,
) -> Iterable[ClientListItem]:
    return [
        build_client_list_items_update_result(raw_data=client_list_item)
        for client_list_item in raw_data.get("deleted", [])
    ]


def build_client_list_items_update_result(raw_data: SingleJson) -> ClientListItem:
    return ClientListItem.from_json(client_list_item_json=raw_data)


def build_network_list_activation_object(raw_data: SingleJson) -> NetworkListActivation:
    return NetworkListActivation.from_json(network_activation_json=raw_data)
