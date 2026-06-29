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
from typing import TYPE_CHECKING

from TIPCommon.base.interfaces import ScriptLogger

if TYPE_CHECKING:
    from typing import Self

    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_token: str
    client_secret: str
    access_token: str
    verify_ssl: bool
    siemplify_logger: ScriptLogger


@dataclasses.dataclass(slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return self.raw_data


@dataclasses.dataclass(slots=True)
class NetworkList(BaseModel):
    name: str
    unique_id: str
    read_only: bool
    shared: bool
    network_type: str
    network_list_type: str
    access_control_group: str
    activation_production: SingleJson | None = None
    activation_staging: SingleJson | None = None

    @classmethod
    def from_json(cls, network_json: SingleJson) -> NetworkList:
        return cls(
            raw_data=network_json,
            name=network_json["name"],
            unique_id=network_json["uniqueId"],
            read_only=network_json["readOnly"],
            shared=network_json["shared"],
            network_type=network_json["type"],
            network_list_type=network_json["networkListType"],
            access_control_group=network_json.get("accessControlGroup"),
        )

    def to_dict(self) -> SingleJson:
        """Converts the NetworkList object to a dictionary representation.

        Returns:
            dict: A dictionary containing the attributes of the NetworkList object.

        """
        data = self.raw_data.copy()
        if self.activation_production:
            data["Activation_PRODUCTION"] = self.activation_production
        if self.activation_staging:
            data["Activation_STAGING"] = self.activation_staging

        return data


@dataclasses.dataclass(slots=True)
class NetworkActivation(BaseModel):
    activation_id: int
    comments: str
    status: str
    unique_id: str

    @classmethod
    def from_json(cls, activation_json: SingleJson) -> NetworkActivation:
        return cls(
            raw_data=activation_json,
            activation_id=activation_json.get("activationId"),
            comments=activation_json.get("activationComments"),
            status=activation_json.get("activationStatus"),
            unique_id=activation_json["uniqueId"],
        )


@dataclasses.dataclass(slots=True)
class ClientActivation(BaseModel):
    action: str
    activations: dict
    create_date: str
    created_by: str
    list_id: str
    version: int

    @classmethod
    def from_json(cls, activation_json: SingleJson) -> Self:
        return cls(
            raw_data=activation_json,
            action=activation_json.get("action"),
            activations=activation_json.get("activations", {}),
            create_date=activation_json.get("createDate"),
            created_by=activation_json.get("createdBy"),
            list_id=activation_json.get("listId"),
            version=activation_json.get("version"),
        )


@dataclasses.dataclass(slots=True)
class NetworkItemList(BaseModel):
    @classmethod
    def from_json(cls, item_list_json: SingleJson) -> NetworkItemList:
        return cls(
            raw_data=item_list_json,
        )


@dataclasses.dataclass(slots=True)
class AddItemsToNetworkList(BaseModel):
    @classmethod
    def from_json(cls, add_items_json: SingleJson) -> AddItemsToNetworkList:
        return cls(
            raw_data=add_items_json,
        )


@dataclasses.dataclass(slots=True)
class RemoveItemsFromNetworkList(BaseModel):
    @classmethod
    def from_json(cls, remove_items_json: SingleJson) -> RemoveItemsFromNetworkList:
        return cls(
            raw_data=remove_items_json,
        )


@dataclasses.dataclass(slots=True)
class ClientListItemDetails:
    """Represents the details of items to be added to a client list."""

    values: list[str]
    tags: list[str]
    description: str | None = None
    expiration_date: str | None = None


@dataclasses.dataclass(slots=True)
class ClientList(BaseModel):
    """Represents an Akamai client list."""

    name: str | None
    list_id: str | None
    item_values: list[str]

    @classmethod
    def from_json(cls, client_list_json: SingleJson) -> ClientList:
        return cls(
            raw_data=client_list_json,
            name=client_list_json["name"],
            list_id=client_list_json["listId"],
            item_values=[item["value"] for item in client_list_json.get("items", [])],
        )


@dataclasses.dataclass(slots=True)
class ClientListItem(BaseModel):
    """Represents an item within an Akamai client list."""

    @classmethod
    def from_json(cls, client_list_item_json: SingleJson) -> ClientListItem:
        return cls(
            raw_data=client_list_item_json,
        )


@dataclasses.dataclass(slots=True)
class NetworkListActivation(BaseModel):
    @classmethod
    def from_json(cls, network_activation_json: SingleJson) -> NetworkListActivation:
        return cls(
            raw_data=network_activation_json,
        )
