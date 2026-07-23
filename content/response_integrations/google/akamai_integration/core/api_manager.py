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
from collections.abc import Iterable
from typing import TYPE_CHECKING

from TIPCommon.base.interfaces import ScriptLogger
from ..core import data_parser
from ..core import api_utils
from ..core import constants
from ..core import datamodels
import requests

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class ApiParameters:
    api_root: str


class ApiManager:

    def __init__(
        self,
        session: requests.Session,
        api_parameters: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        self.session: requests.Session = session
        self.api_root: str = api_parameters.api_root
        self.logger: ScriptLogger = logger

    def test_connectivity(self) -> None:
        """Test the connectivity to the Akamai API."""
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_contracts",
        )

        try:
            response: requests.Response = self.session.get(url=url)
            api_utils.validate_response(response=response)

        except UnicodeEncodeError as e:
            raise requests.exceptions.RequestException("Invalid credentials") from e

    def get_networks(self) -> Iterable[datamodels.NetworkList]:
        """Get the list of networks.

        Returns:
            Iterable[datamodels.NetworkList]: The list of networks.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_networks",
        )

        response: requests.Response = self.session.get(url)
        api_utils.validate_response(response=response)

        return data_parser.build_network_lists(raw_data=response.json())

    def get_network_list_activation(
        self,
        network_list_id: str,
        environment: str,
    ) -> datamodels.NetworkActivation:
        """Get the activation status of a network list.

        Args:
            network_list_id (str): The ID of the network list.
            environment (str): The environment to check.

        Returns:
            SingleJson: The activation status of the network list.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_network_list_activation",
            network_list_id=network_list_id,
            environment=environment,
        )
        response: requests.Response = self.session.get(url=url)
        api_utils.validate_response(response=response)

        return data_parser.build_network_activation(raw_data=response.json())

    def get_network_item_list(self, network_list_id: str) -> datamodels.NetworkItemList:
        """Retrieves the item list for a given network list ID.

        Args:
            network_list_id: The unique identifier of the network list.

        Returns:
            A NetworkItemList object containing the list of items in the network list.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root, url_id="item_list", network_list_id=network_list_id,
        )
        response: requests.Response = self.session.get(url)
        api_utils.validate_response(response=response)
        return data_parser.build_network_item_list(raw_data=response.json())

    def add_items_to_network_list(
        self,
        network_list_id: str,
        items: Iterable[str],
    ) -> datamodels.AddItemsToNetworkList:
        """Add items to a network list.

        Args:
            network_list_id (str): The ID of the network list.
            items (list[str]): The items to add to the network list.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="add_items_to_network_list",
            network_list_id=network_list_id,
        )
        payload: dict[str, list[str]] = {"list": items}
        response: requests.Response = self.session.post(url=url, json=payload)
        api_utils.validate_response(response=response)

        return data_parser.build_add_items_to_network_list(raw_data=response.json())

    def remove_item_from_network_list(
        self,
        network_list_id: str,
        item: str,
    ) -> datamodels.RemoveItemsFromNetworkList:
        """Remove an item from a network list.

        Args:
            network_list_id (str): The ID of the network list.
            item (str): The item to remove.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="remove_item_from_network_list",
            network_list_id=network_list_id,
            item=item,
        )
        response: requests.Response = self.session.delete(url=url)
        api_utils.validate_response(response=response)

        return data_parser.build_remove_items_from_network_list(
            raw_data=response.json(),
        )

    def get_client_lists(
        self,
        client_list_type: str = constants.LIST_TYPE_FOR_ALL,
        *,
        include_items: bool = False,
    ) -> list[datamodels.ClientList]:
        """Get a list of client lists.

        Args:
            client_list_type (str): The type of client list to retrieve.
            include_items (bool): Whether to include items in the response.

        Returns:
            list[datamodels.ClientList]: A list of ClientList objects.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="get_client_lists",
            include_items=include_items,
        )

        if client_list_type != constants.LIST_TYPE_FOR_ALL:
            url = f"{url}&type={constants.CLIENT_LIST_TYPE_MAPPING[client_list_type]}"

        response: requests.Response = self.session.get(url=url)
        api_utils.validate_response(response=response)

        return data_parser.build_client_lists(response.json())

    def add_items_to_client_list(
        self,
        list_id: str,
        item_details: datamodels.ClientListItemDetails,
    ) -> Iterable[datamodels.ClientListItem]:
        """Add items to a specified client list in Akamai.

        Args:
            list_id (str): The ID of the client list to which items will be added.
            item_details (datamodels.ClientListItemDetails): An object containing
                the details of the items to be added (values, tags, description,
                expiration date).

        Returns:
            Iterable[datamodels.ClientListItem]: A list of ClientListItem object that
                encapsulates the API response from Akamai, including details of
                appended, deleted, or updated items.

        """
        description: str = (
            item_details.description if item_details.description is not None else ""
        )
        expiration_date: str = (
            item_details.expiration_date
            if item_details.expiration_date is not None
            else ""
        )

        body: SingleJson = {"append": []}

        for value in item_details.values:
            body["append"].append(
                {
                    "description": description,
                    "expirationDate": expiration_date,
                    "tags": item_details.tags,
                    "value": value,
                },
            )

        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="update_items_in_client_list",
            list_id=list_id,
        )

        response: requests.Response = self.session.post(url=url, json=body)
        api_utils.validate_response(response=response)

        return data_parser.build_client_list_items_append_result_list(response.json())

    def remove_items_from_client_list(
        self,
        list_id: str,
        item_values: list[str],
    ) -> Iterable[datamodels.ClientListItem]:
        """Remove items from a specified client list in Akamai.

        Args:
            list_id (str): The ID of the client list from which items will be removed.
            item_values (list[str]): A list of values for the items to be removed.

        Returns:
            Iterable[datamodels.ClientListItem]: A list of ClientListItem object that
                encapsulates the API response from Akamai, including details of
                appended, deleted, or updated items.

        """
        body: SingleJson = {"delete": []}

        for value in item_values:
            body["delete"].append({"value": value})

        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="update_items_in_client_list",
            list_id=list_id,
        )

        response: requests.Response = self.session.post(url=url, json=body)
        api_utils.validate_response(response=response)

        return data_parser.build_client_list_items_delete_result_list(response.json())

    def activate_network_list(
        self,
        network_list_id: str,
        environment: str,
        comments: SingleJson | None = None,
        notification_recipients: SingleJson | None = None,
    ) -> datamodels.NetworkListActivation:
        """Activates a network list in the specified environment.

        Args:
            network_list_id: The ID of the network list.
            environment: The environment to activate in. The method will handle
                converting to uppercase for the API.
            comments: Optional comments for the activation.
            notification_recipients: Optional list of email addresses for notifications.

        Returns:
            A NetworkListActivation object representing the result of the activation.

        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="activate_network_list",
            network_list_id=network_list_id,
            environment=environment.upper(),
        )

        payload: SingleJson = {}
        if comments:
            payload["comments"] = comments
        if notification_recipients:
            payload["notificationRecipients"] = notification_recipients

        response: requests.Response = self.session.post(url=url, json=payload)
        api_utils.validate_response(response=response)

        return data_parser.build_network_list_activation_object(
            raw_data=response.json(),
        )

    def activate_client_list(
        self,
        client_list_id: str,
        environment: str,
        comments: str | None,
        notification_recipients: list[str] | None,
    ) -> datamodels.ClientActivation:
        """Activates a specific client list on the Akamai network.

        Args:
            client_list_id (str): The unique identifier for the client list.
            environment (str): The environment to activate in (e.g., "PRODUCTION"
                or "STAGING").
            comments (str | None): Optional comments for the activation.
            notification_recipients (list[str] | None): Optional list of email
                addresses for notifications.

        Returns:
            datamodels.ClientActivation: A ClientActivation object representing
                the result of the activation.
        """
        url: str = api_utils.get_full_url(
            api_root=self.api_root,
            url_id="activate_client_list",
            list_id=client_list_id,
        )

        payload: SingleJson = {
            "action": "ACTIVATE",
            "network": environment.upper(),
        }

        if comments is not None:
            payload["comments"] = comments
        if notification_recipients is not None:
            payload["notificationRecipients"] = notification_recipients

        response: requests.Response = self.session.post(url, json=payload)
        api_utils.validate_response(response)

        return data_parser.build_client_activation(raw_data=response.json())
