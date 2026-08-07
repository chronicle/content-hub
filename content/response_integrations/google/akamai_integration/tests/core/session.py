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

from collections.abc import Iterable

from TIPCommon.types import SingleJson

from ...tests.core.product import Akamai
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class AkamaiSession(MockSession[MockRequest, MockResponse, Akamai]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_network_lists,
            self.get_network_list_items_by_id,
            self.add_items_to_network_list,
            self.remove_element_from_network_list,
            self.activate_network_list_in_environment,
            self.get_client_lists,
            self.update_items_in_client_list,
            self.get_network_list_activation_status,
            self.activate_client_list,
        ]

    @router.get(r"/network-list/v2/network-lists")
    def get_network_lists(self, request: MockRequest) -> MockResponse:
        """Handle GET /network-list/v2/network-lists requests."""
        response_data: SingleJson = {
            "networkLists": [
                network_list.to_json()
                for network_list in self._product.get_network_list()
            ],
        }
        if "invalid" in request.url.netloc:
            return MockResponse(
                content=response_data,
                status_code=401,
            )
        return MockResponse(content=response_data, status_code=200)

    @router.get(r"/network-list/v2/network-lists/(?P<network_list_id>[^/]+)$")
    def get_network_list_items_by_id(
        self,
        request: MockRequest,
    ) -> MockResponse:
        """Handle GET /network-list/v2/network-lists/{network_list_id} requests."""
        network_item_jsons: list[SingleJson] = [
            item.to_json() for item in self._product.get_network_item_list()
        ]

        response_content: SingleJson = network_item_jsons[0]

        if "Invalid" in request.url.path:
            return MockResponse(
                content="Test",
                status_code=404,
            )

        return MockResponse(content=response_content, status_code=200)

    @router.post(r"/network-list/v2/network-lists/(?P<network_list_id>[^/]+)/append")
    def add_items_to_network_list(self, request: MockRequest) -> MockResponse:
        """Handle POST /{network_list_id}/append requests."""
        network_item_jsons: list[SingleJson] = [
            item.to_json() for item in self._product.get_network_item_list()
        ]
        if "Invalid" in request.url.path:
            return MockResponse(
                content="Test",
                status_code=404,
            )

        response_content: SingleJson = network_item_jsons[0]
        return MockResponse(content=response_content, status_code=200)

    @router.delete(
        r"/network-list/v2/network-lists/(?P<network_list_id>\d+_[A-Z0-9]+)/elements",
    )
    def remove_element_from_network_list(self, request: MockRequest) -> MockResponse:
        """Handle DELETE /{network_list_id}/elements?element={element_value} requests.
        """
        network_item_jsons: list[SingleJson] = [
            item.to_json() for item in self._product.get_network_item_list()
        ]

        response_content: SingleJson = network_item_jsons[0]

        if "Invalid" in request.url.path:
            return MockResponse(
                content="Test",
                status_code=404,
            )

        return MockResponse(content=response_content, status_code=200)

    @router.post(
        r"/network-list/v2/network-lists/(?P<network_list_id>\d+_[A-Z0-9]+)"
        r"/environments/(?P<environment>(?:STAGING|PRODUCTION))/activate",
    )
    def activate_network_list_in_environment(
        self, request: MockRequest,
    ) -> MockResponse:
        """Handle POST /{network_list_id}/environments/{environment}/activate requests.
        """
        network_item_jsons: list[SingleJson] = [
            item.to_json() for item in self._product.get_network_item_list()
        ]

        response_content: SingleJson = network_item_jsons[0]

        if "Invalid" in request.url.path:
            return MockResponse(
                content="Test",
                status_code=404,
            )

        return MockResponse(content=response_content, status_code=200)

    @router.get(r"/client-list/v1/lists(?:\?includeItems=(?P<include_items>.+))?")
    def get_client_lists(self, _: MockRequest) -> MockResponse:
        """Handle GET /client-list/v1/lists requests."""
        response_data: SingleJson = {
            "content": [
                client_list.to_json()
                for client_list in self._product.get_client_lists()
            ],
        }

        return MockResponse(content=response_data, status_code=200)

    @router.post(r"/client-list/v1/lists/(?P<list_id>[^/]+)/items")
    def update_items_in_client_list(self, request: MockRequest) -> MockResponse:
        """Handle POST /client-list/v1/lists/{list_id}/items requests."""
        payload: SingleJson = request.kwargs["json"]

        if "append" in payload:
            if "1.1.1.1" in request.kwargs["json"]["append"][0]["value"]:
                response_data: SingleJson = {
                    "status": 400,
                    "title": "Invalid Input Error",
                    "detail": "Cannot add item 1.1.1.1. Already exists",
                }
                return MockResponse(content=response_data, status_code=400)

            response_data: SingleJson = {
                "appended": [
                    client_list_item.to_json()
                    for client_list_item in self._product.get_client_list_items()
                ],
            }
            return MockResponse(content=response_data, status_code=200)

        if "2.2.2.2" in request.kwargs["json"]["delete"][0]["value"]:
            response_data: SingleJson = {
                "status": 400,
                "title": "Invalid Input Error",
                "detail": "Items to delete with values '2.2.2.2' not found.",
            }
            return MockResponse(content=response_data, status_code=400)

        response_data: SingleJson = {
            "deleted": [
                client_list_item.to_json()
                for client_list_item in self._product.get_client_list_items()
            ],
        }

        return MockResponse(content=response_data, status_code=200)

    @router.get(
        r"/network-list/v2/network-lists/(?P<network_list_id>[^/]+)"
        r"/environments/(?P<environment>[^/]+)/status",
    )
    def get_network_list_activation_status(self, request: MockRequest) -> MockResponse:
        """Handle GET /{network_list_id}/environments/{environment}/status requests.
        """
        network_item_jsons: list[SingleJson] = [
            item.to_json() for item in self._product.get_network_list_activation()
        ]
        response_content: SingleJson = network_item_jsons[0]

        if "Invalid" in request.url.path:
            return MockResponse(
                content="Test",
                status_code=404,
            )
        return MockResponse(content=response_content, status_code=200)


    @router.post(r"/client-list/v2/lists/(?P<list_id>[^/]+)/activations")
    def activate_client_list(self, _: MockRequest) -> MockResponse:
        """Handle POST /client-list/v2/lists/{list_id}/activations requests."""
        client_activation = self._product.get_client_activation()
        response_content = client_activation.to_json()
        return MockResponse(content=response_content, status_code=200)
