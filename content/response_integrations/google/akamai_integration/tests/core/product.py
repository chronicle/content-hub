from __future__ import annotations
import abc

import dataclasses
from collections.abc import Iterable

from akamai_integration.core.datamodels import (
    AddItemsToNetworkList,
    ClientActivation,
    ClientList,
    ClientListItem,
    NetworkActivation,
    NetworkItemList,
    NetworkList,
)


@dataclasses.dataclass
class Akamai(abc.ABC):
    def __init__(self):
        self._network_lists: list[NetworkList] = []
        self._network_activations: list[NetworkActivation] = []
        self._network_item_lists: list[NetworkItemList] = []
        self._add_items_responses: list[AddItemsToNetworkList] = []
        self._client_lists: list[ClientList] = []
        self._client_list_items: list[ClientListItem] = []
        self.client_activations: list[ClientActivation] = []

    @property
    def client_lists(self) -> list[ClientList]:
        return self._client_lists

    @property
    def client_list_items(self) -> list[ClientListItem]:
        return self._client_list_items

    def get_network_list(self) -> NetworkList | None:
        return self._network_lists

    def add_network_lists(self, network_lists: Iterable[NetworkList]) -> None:
        self._network_lists.append(network_lists)

    def get_network_item_list(self) -> NetworkItemList | None:
        return self._network_item_lists

    def get_client_activation(self) -> ClientActivation:
        return self.client_activations[0]

    def add_client_activation(self, client_activation: ClientActivation) -> None:
        self.client_activations.append(client_activation)

    def add_network_item_list(self, item_list: NetworkItemList) -> None:
        self._network_item_lists.append(item_list)

    def add_network_list_activation(
        self, network_activation: NetworkActivation,
    ) -> None:
        self._network_activations.append(network_activation)

    def get_network_list_activation(self) -> NetworkActivation | None:
        return self._network_activations

    def add_client_lists(self, client_list: ClientList) -> None:
        self._client_lists.append(client_list)

    def get_client_lists(self) -> list[ClientList]:
        return self._client_lists

    def add_client_list_items(self, client_list_item: ClientListItem) -> None:
        self._client_list_items.append(client_list_item)

    def get_client_list_items(self) -> list[ClientListItem]:
        return self._client_list_items
