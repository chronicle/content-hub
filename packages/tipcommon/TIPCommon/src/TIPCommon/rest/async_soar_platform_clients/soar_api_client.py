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

import httpx

from TIPCommon.rest.async_soar_platform_clients.base_soar_api import BaseAsyncSoarApi
from TIPCommon.rest.async_soar_platform_clients.constants import (
    CONNECTOR_INSTANCE_UPDATE_FIELDS,
    DEFAULT_PAGE_SIZE,
    STATUS_CODE_NO_CONTENT,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class AsyncMarketplaceApi(BaseAsyncSoarApi):
    """
    Async Marketplace Integrations API client.
    """

    async def get_list_of_integrations_available_for_upgrade(self) -> SingleJson:
        """Get a list of integrations available for upgrade.

        Returns:
            SingleJson: A list of integrations available for upgrade.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        params: SingleJson = {
            "orderBy": "identifier asc",
            "pageSize": DEFAULT_PAGE_SIZE,
            "filter": "updateAvailable = true",
        }
        response: httpx.Response = await self.get(
            "marketplaceIntegrations",
            params=params,
        )

        return response.json()

    async def upgrade_integration(
        self,
        integration_id: str,
        override_mapping: bool = False,
        staging: bool = False,
    ) -> SingleJson:
        """Upgrade an integration to the latest version.

        Args:
            integration_id (str): The ID of the integration to upgrade.
            override_mapping (bool): Whether to override the mapping. Defaults to False.
            staging (bool): Whether to use staging. Defaults to False.

        Returns:
            SingleJson: The response from the upgrade request.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = f"/marketplaceIntegrations/{integration_id}:install"
        payload: SingleJson = {"overrideMapping": override_mapping, "staging": staging}
        response: httpx.Response = await self.post(endpoint, payload=payload)

        return response.json()

    async def get_connector_instances(self) -> SingleJson:
        """Get a list of connector instances.

        Returns:
            SingleJson: A list of connector instances.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = "/integrations/-/connectors/-/connectorInstances"
        params: SingleJson = {"pageSize": DEFAULT_PAGE_SIZE}
        response: httpx.Response = await self.get(endpoint, params=params)
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {"connector_instances": []}

        return response.json()

    async def get_connector_instance_details(
        self,
        integration_id: str,
        connector_id: str,
        connector_instance_id: str,
    ) -> SingleJson:
        """Get details of a specific connector instance.

        Args:
            integration_id (str): The ID of the integration.
            connector_id (str): The ID of the connector.
            connector_instance_id (str): The ID of the connector instance.

        Returns:
            SingleJson: Details of the connector instance.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = (
            f"/integrations/{integration_id}/connectors/{connector_id}/"
            f"connectorInstances/{connector_instance_id}"
        )
        response: httpx.Response = await self.get(endpoint)

        return response.json()

    async def fetch_latest_connector_def(
        self,
        integration_id: str,
        connector_id: str,
        connector_instance_id: str,
    ) -> SingleJson:
        """Fetch the latest connector definition for a specific connector instance.

        Args:
            integration_id (str): The ID of the integration.
            connector_id (str): The ID of the connector.
            connector_instance_id (str): The ID of the connector instance.

        Returns:
            SingleJson: The latest connector definition.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = (
            f"/integrations/{integration_id}/connectors/{connector_id}/"
            f"connectorInstances/{connector_instance_id}:fetchLatestDefinition"
        )
        response: httpx.Response = await self.get(endpoint)

        return response.json()

    async def get_integration_details(self, integration_id: str) -> SingleJson:
        """Get details of a specific integration.

        Args:
            integration_id (str): The ID of the integration.

        Returns:
            SingleJson: Details of the integration.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = f"/integrations/{integration_id}"
        response: httpx.Response = await self.get(endpoint)

        return response.json()

    async def upgrade_connector_instance(
        self,
        integration_name: str,
        connector_id: str,
        connector_instance_id: str,
        payload: SingleJson,
    ) -> SingleJson:
        """Upgrade a connector instance to the latest definition.

        Args:
            integration_name (str): The name of the integration.
            connector_id (str): The ID of the connector.
            connector_instance_id (str): The ID of the connector instance.
            payload (SingleJson): The payload for upgrading the connector instance.

        Returns:
            SingleJson: The response from the upgrade request.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
        """
        endpoint: str = (
            f"/integrations/{integration_name}/connectors/{connector_id}/"
            f"connectorInstances/{connector_instance_id}"
        )
        params: SingleJson = {"updateMask": ",".join(CONNECTOR_INSTANCE_UPDATE_FIELDS)}
        response: httpx.Response = await self.patch(
            endpoint,
            payload=payload,
            params=params,
        )

        return response.json()
