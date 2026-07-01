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

import pathlib
import copy

import pytest
from ..core.api_manager import ApiManager
from ..core.datamodels import (
    ClientActivation,
    ClientList,
    ClientListItem,
    ClientListItemDetails,
    NetworkActivation,
    NetworkItemList,
    NetworkListActivation,
    RemoveItemsFromNetworkList,
)
from ..tests import common
from ..tests.core.session import Akamai, AkamaiSession


class TestAkamaiManager:
    """Unit tests for Akamai Integration's AkamaiManager methods."""

    def test_test_connectivity_success(
        self,
        manager: ApiManager,
        script_session: AkamaiSession,
    ) -> None:
        """Args:
        api_manager (ApiManager): ApiManager object.
        akamai_product (Akamai):
            Akamai product object.
        script_session (CAkamaiSession):
            AkamaiSession object.

        """
        manager.test_connectivity()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200

    def test_test_connectivity_failure(
        self,
        manager: ApiManager,
        script_session: AkamaiSession,
    ) -> None:
        """Args:
        api_manager (ApiManager): ApiManager object.
        akamai_product (Akamai):
            Akamai product object.
        script_session (AkamaiSession):
            AkamaiSession object.

        """
        manager.api_root = "https://api.eu.invalid.com"

        with pytest.raises(Exception, match="An error occurred.") as e:
            manager.test_connectivity()

        actual_error_message = str(e.value)

        assert len(script_session.request_history) == 1
        assert "401 Client Error" in actual_error_message
        assert "An error occurred:" in str(e.value)
        assert type(e.value).__name__ == "AkamaiManagerError"

    def test_get_client_lists_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_list_1: ClientList = copy.deepcopy(common.CLIENT_LIST)
        client_list_2: ClientList = copy.deepcopy(common.CLIENT_LIST)

        client_list_1.raw_data["name"] = "Testing_Geo"
        client_list_1.raw_data["listId"] = "238746_TESTINGGEO"
        client_list_1.raw_data["type"] = "GEO"
        client_list_1.raw_data["items"][0]["value"] = "CH"
        client_list_1.raw_data["items"][1]["value"] = "CN"

        client_list_2.raw_data["name"] = "Testing_Ip"
        client_list_2.raw_data["listId"] = "238789_TESTINGIP"
        client_list_2.raw_data["type"] = "IP"
        client_list_2.raw_data["items"][0]["value"] = "1.1.1.1"
        client_list_2.raw_data["items"][1]["value"] = "2.2.2.2"

        akamai.add_client_lists(client_list_1)
        akamai.add_client_lists(client_list_2)

        results = manager.get_client_lists(include_items=True)

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert len(results) == 2
        assert results[0].name == "Testing_Geo"
        assert results[0].list_id == "238746_TESTINGGEO"
        assert len(results[0].item_values) == 2
        assert results[1].name == "Testing_Ip"
        assert results[1].list_id == "238789_TESTINGIP"
        assert len(results[1].item_values) == 2

    def test_add_items_to_client_lists_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_list_item_1: ClientListItem = copy.deepcopy(common.ADD_CLIENT_LIST_ITEM)
        client_list_item_2: ClientListItem = copy.deepcopy(common.ADD_CLIENT_LIST_ITEM)

        client_list_item_1.raw_data["value"] = "11.11.11.11"
        client_list_item_1.raw_data["description"] = "Test_Description"
        client_list_item_1.raw_data["tags"] = ["tag1", "tag2"]
        client_list_item_1.raw_data["expirationDate"] = "2025-01-01T00:00:00Z"

        client_list_item_2.raw_data["value"] = "12.12.12.12"
        client_list_item_2.raw_data["description"] = "Test_Description"
        client_list_item_2.raw_data["tags"] = ["tag1", "tag2"]
        client_list_item_2.raw_data["expirationDate"] = "2025-01-01T00:00:00Z"

        akamai.add_client_list_items(client_list_item_1)
        akamai.add_client_list_items(client_list_item_2)

        item_payload: ClientListItemDetails = ClientListItemDetails(
            values=["11.11.11.11", "12.12.12.12"],
            tags=["tag1", "tag2"],
            description="Test_Description",
            expiration_date="2025-01-01T00:00:00Z",
        )

        results = manager.add_items_to_client_list(
            list_id="238746_TESTINGIP", item_details=item_payload,
        )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert len(results) == 2
        assert results[0].raw_data["value"] == "11.11.11.11"
        assert results[0].raw_data["description"] == "Test_Description"
        assert results[0].raw_data["tags"] == ["tag1", "tag2"]
        assert results[0].raw_data["expirationDate"] == "2025-01-01T00:00:00Z"
        assert results[1].raw_data["value"] == "12.12.12.12"
        assert results[1].raw_data["description"] == "Test_Description"
        assert results[1].raw_data["tags"] == ["tag1", "tag2"]
        assert results[1].raw_data["expirationDate"] == "2025-01-01T00:00:00Z"

    def test_add_items_to_client_lists_failed(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_list_item_1: ClientListItem = copy.deepcopy(common.ADD_CLIENT_LIST_ITEM)
        client_list_item_1.raw_data["value"] = "1.1.1.1"
        client_list_item_1.raw_data["description"] = "Test_Description"
        client_list_item_1.raw_data["tags"] = ["tag1", "tag2"]
        client_list_item_1.raw_data["expirationDate"] = "2025-01-01T00:00:00Z"

        akamai.add_client_list_items(client_list_item_1)

        item_payload: ClientListItemDetails = ClientListItemDetails(
            values=["1.1.1.1"],
            tags=["tag1", "tag2"],
            description="Test_Description",
            expiration_date="2025-01-01T00:00:00Z",
        )

        with pytest.raises(Exception) as e:
            manager.add_items_to_client_list(
                list_id="238746_TESTINGIP", item_details=item_payload,
            )

        assert len(script_session.request_history) == 1
        assert "Cannot add item 1.1.1.1. Already exists" in str(e.value)

    def test_remove_items_from_client_lists_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_list_item_1: ClientListItem = copy.deepcopy(
            common.REMOVE_CLIENT_LIST_ITEM,
        )
        client_list_item_2: ClientListItem = copy.deepcopy(
            common.REMOVE_CLIENT_LIST_ITEM,
        )

        client_list_item_1.raw_data["value"] = "11.11.11.11"
        client_list_item_2.raw_data["value"] = "12.12.12.12"

        akamai.add_client_list_items(client_list_item_1)
        akamai.add_client_list_items(client_list_item_2)

        results = manager.remove_items_from_client_list(
            list_id="238746_TESTINGIP", item_values=["11.11.11.11", "12.12.12.12"],
        )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert len(results) == 2
        assert results[0].raw_data["value"] == "11.11.11.11"
        assert results[1].raw_data["value"] == "12.12.12.12"

    def test_remove_items_from_client_lists_failed(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_list_item_1: ClientListItem = copy.deepcopy(
            common.REMOVE_CLIENT_LIST_ITEM,
        )
        client_list_item_1.raw_data["value"] = "1.1.1.1"
        akamai.add_client_list_items(client_list_item_1)

        with pytest.raises(Exception) as e:
            manager.remove_items_from_client_list(
                list_id="238746_TESTINGIP", item_values=["2.2.2.2"],
            )

        assert len(script_session.request_history) == 1
        assert "Items to delete with values '2.2.2.2' not found." in str(e.value)

    def test_get_network_lists_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_1: ClientList = copy.deepcopy(common.NETWORK_LIST)
        network_list_2: ClientList = copy.deepcopy(common.NETWORK_LIST)

        network_list_1.raw_data["name"] = "Testing_Geo"
        network_list_1.raw_data["listId"] = "238746_TESTINGGEO"
        network_list_1.raw_data["type"] = "GEO"

        network_list_2.raw_data["name"] = "Testing_Ip"
        network_list_2.raw_data["listId"] = "238789_TESTINGIP"
        network_list_2.raw_data["type"] = "IP"

        akamai.add_network_lists(network_list_1)
        akamai.add_network_lists(network_list_2)

        results = manager.get_networks()

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert len(results) == 2
        assert results[0].name == "Testing_Geo"

    def test_get_network_list_activation_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
    ) -> None:
        akamai.add_network_list_activation(common.NETWORK_STAGING_ACTIVATION)
        results: NetworkActivation = manager.get_network_list_activation(
            "229854_TEST", "STAGING",
        )

        assert results.status == common.NETWORK_STAGING_ACTIVATION.status
        assert results.activation_id == common.NETWORK_STAGING_ACTIVATION.activation_id
        assert results.comments == common.NETWORK_STAGING_ACTIVATION.comments
        assert results.unique_id == "229854_TEST"

    def test_get_network_list_activation_failure(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_item_1: NetworkActivation = copy.deepcopy(
            common.NETWORK_STAGING_ACTIVATION,
        )
        network_list_item_1.raw_data["uniqueId"] = "Invalid_ID"
        akamai.add_network_list_activation(network_list_item_1)

        with pytest.raises(Exception) as e:
            manager.get_network_list_activation(
                network_list_item_1.raw_data["uniqueId"], "PRODUCTION",
            )

        assert len(script_session.request_history) == 1
        assert type(e.value).__name__ == "AkamaiManagerError"
        assert "Invalid request." in str(e.value)

    def test_get_network_item_list_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_data: NetworkItemList = common.NETWORK_ITEM_LIST
        akamai.add_network_item_list(network_data)
        results: NetworkItemList = manager.get_network_item_list("229854_TEST")

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0]
        assert request.response.status_code == 200
        assert results is not None
        assert results.raw_data["name"] == network_data.raw_data["name"]
        assert results.raw_data["uniqueId"] == network_data.raw_data["uniqueId"]
        assert (
            results.raw_data["accessControlGroup"]
            == network_data.raw_data["accessControlGroup"]
        )
        assert (
            results.raw_data["networkListType"]
            == network_data.raw_data["networkListType"]
        )
        assert results.raw_data["type"] == network_data.raw_data["type"]
        assert results.raw_data["list"] == network_data.raw_data["list"]
        assert results.raw_data["syncPoint"] == network_data.raw_data["syncPoint"]

    def test_get_network_item_list_failure(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_item: NetworkItemList = copy.deepcopy(common.NETWORK_ITEM_LIST)
        network_list_item.raw_data["uniqueId"] = "Invalid_ID"
        akamai.add_network_list_activation(network_list_item)

        with pytest.raises(Exception) as e:
            manager.get_network_item_list(network_list_item.raw_data["uniqueId"])

        assert len(script_session.request_history) == 0
        assert type(e.value).__name__ == "IndexError"

    def test_add_items_to_network_list_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_data: NetworkItemList = common.ADD_ITEMS_TO_NETWORK_LIST
        akamai.add_network_item_list(network_data)
        results: NetworkItemList = manager.add_items_to_network_list(
            "229854_TEST", "127.0.0.16",
        )
        result_data = results.raw_data["networkLists"]
        network_list_data = network_data.raw_data["networkLists"]

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0]
        assert request.response.status_code == 200
        assert network_data is not None
        assert results.raw_data["links"] == network_data.raw_data["links"]
        assert result_data[0]["uniqueId"] == network_list_data[0]["uniqueId"]
        assert result_data[0]["name"] == network_list_data[0]["name"]
        assert result_data[1]["type"] == network_list_data[1]["type"]
        assert result_data[1]["syncPoint"] == network_list_data[1]["syncPoint"]

    def test_add_items_to_network_list_failure(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_item: NetworkItemList = copy.deepcopy(
            common.ADD_ITEMS_TO_NETWORK_LIST,
        )
        network_list_item.raw_data["uniqueId"] = "Invalid_ID"
        akamai.add_network_item_list(network_list_item)

        with pytest.raises(Exception) as e:
            manager.add_items_to_network_list(
                network_list_item.raw_data["uniqueId"], "PRODUCTION",
            )

        assert len(script_session.request_history) == 1
        assert type(e.value).__name__ == "AkamaiManagerError"
        assert "Invalid request." in str(e.value)

    def test_remove_item_from_network_list_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_data: RemoveItemsFromNetworkList = common.REMOVE_ITEMS_TO_NETWORK_LIST
        akamai.add_network_item_list(network_data)
        results: NetworkItemList = manager.remove_item_from_network_list(
            "229854_TEST", "127.0.0.16",
        )
        result_data = results.raw_data["networkLists"]
        network_list_data = network_data.raw_data["networkLists"]

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0]
        assert request.response.status_code == 200
        assert network_data is not None
        assert results.raw_data["links"] == network_data.raw_data["links"]
        assert result_data[0]["uniqueId"] == network_list_data[0]["uniqueId"]
        assert result_data[0]["name"] == network_list_data[0]["name"]
        assert result_data[1]["type"] == network_list_data[1]["type"]
        assert result_data[1]["syncPoint"] == network_list_data[1]["syncPoint"]

    def test_remove_item_from_network_list_failure(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_item: RemoveItemsFromNetworkList = copy.deepcopy(
            common.REMOVE_ITEMS_TO_NETWORK_LIST,
        )
        network_list_item.raw_data["uniqueId"] = "Invalid_ID"
        akamai.add_network_item_list(network_list_item)

        with pytest.raises(Exception) as e:
            manager.remove_item_from_network_list(
                network_list_item.raw_data["uniqueId"], "1.0.0.0",
            )

        assert len(script_session.request_history) == 0
        assert type(e.value).__name__ == "ValueError"

    def test_activate_network_list_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_data: NetworkListActivation = common.NETWORK_LIST_ACTIVATION
        akamai.add_network_item_list(network_data)
        results: NetworkListActivation = manager.activate_network_list(
            "229854_TEST", "STAGING",
        )

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0]
        assert request.response.status_code == 200
        assert results.raw_data["syncPoint"] == network_data.raw_data["syncPoint"]
        assert results.raw_data["links"] == network_data.raw_data["links"]
        assert (
            results.raw_data["activationComments"]
            == network_data.raw_data["activationComments"]
        )
        assert results.raw_data["uniqueId"] == "238965_TEST3"

    def test_activate_network_list_failure(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        network_list_item: NetworkListActivation = copy.deepcopy(
            common.NETWORK_LIST_ACTIVATION,
        )
        network_list_item.raw_data["uniqueId"] = "Invalid_ID"
        akamai.add_network_item_list(network_list_item)

        with pytest.raises(Exception) as e:
            manager.activate_network_list("Invalid", "PRODUCTION")

        assert len(script_session.request_history) == 0
        assert type(e.value).__name__ == "ValueError"

    def test_activate_client_list_success(
        self,
        manager: ApiManager,
        akamai: Akamai,
        script_session: AkamaiSession,
    ) -> None:
        client_activation: ClientActivation = copy.deepcopy(
            common.ACTIVATE_CLIENT_LIST,
        )
        akamai.add_client_activation(client_activation)

        results = manager.activate_client_list(
            client_list_id="237402_GOOGLESECOPSCLIENTLIST1",
            environment="PRODUCTION",
            comments=None,
            notification_recipients=None,
        )

        assert len(script_session.request_history) == 1
        assert script_session.request_history[0].response.status_code == 200
        assert results.list_id == "237402_GOOGLESECOPSCLIENTLIST1"
        assert results.action == "ACTIVATE"
        assert "PRODUCTION" in results.activations

    def test_activate_client_list_failed(
        self,
        manager: ApiManager,
        script_session: AkamaiSession,
    ) -> None:
        manager.api_root = "https://invalid.url"

        with pytest.raises(Exception) as e:
            manager.activate_client_list(
                client_list_id="237402_GOOGLESECOPSCLIENTLIST1",
                environment="PRODUCTION",
                comments=None,
                notification_recipients=None,
            )

        assert len(script_session.request_history) == 0
        assert "list index out of range" in str(e.value)
