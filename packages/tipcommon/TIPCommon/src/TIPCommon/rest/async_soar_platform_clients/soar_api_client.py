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

from TIPCommon.exceptions import EmptyMandatoryValues, ParameterValidationError
from TIPCommon.rest.async_soar_platform_clients.base_soar_api import BaseAsyncSoarApi
from TIPCommon.rest.async_soar_platform_clients.constants import (
    CONNECTOR_INSTANCE_UPDATE_FIELDS,
    DEFAULT_PAGE_SIZE,
    STATUS_CODE_NO_CONTENT,
)
from TIPCommon.utils import escape_odata_literal

if TYPE_CHECKING:
    import httpx

    from TIPCommon.types import SingleJson


class AsyncMarketplaceApi(BaseAsyncSoarApi):
    """Async Marketplace Integrations API client."""

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
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {"marketplaceIntegrations": []}

        return response.json()

    async def get_integration_available_for_upgrade_in_staging(self) -> SingleJson:
        """Get the integration available for upgrade in staging environment.

        Returns:
            SingleJson: The integration available for upgrade in staging environment.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        params: SingleJson = {
            "orderBy": "productionIdentifier asc",
            "pageSize": DEFAULT_PAGE_SIZE,
        }
        response: httpx.Response = await self.get("integrations", params=params)
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {"integrations": []}

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
            return {"connectorInstances": []}

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
            f"/integrations/{integration_id}/connectors/{connector_id}/connectorInstances/{connector_instance_id}"
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
            f"/integrations/{integration_name}/connectors/{connector_id}/connectorInstances/{connector_instance_id}"
        )
        params: SingleJson = {"updateMask": ",".join(CONNECTOR_INSTANCE_UPDATE_FIELDS)}
        response: httpx.Response = await self.patch(
            endpoint,
            payload=payload,
            params=params,
        )

        return response.json()

    async def get_installed_integrations_of_environment(
        self,
        integration_identifier: str,
        environment: str,
    ) -> list[SingleJson]:
        """Get integration instances for a given environment.

        Args:
            integration_identifier: The integration identifier
                (use ``"-"`` for all integrations).
            environment: The environment name to filter by.

        Returns:
            The response JSON containing integration instances.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        env_literal: str = escape_odata_literal(
            "*" if environment == "Shared Instances" else environment,
        )
        endpoint: str = f"/integrations/{integration_identifier}/integrationInstances"
        params: SingleJson = {
            "$filter": f"environment eq '{env_literal}'",
            "pageSize": DEFAULT_PAGE_SIZE,
        }
        return await self._paginate_results(
            endpoint,
            "integrationInstances",
            params=params,
        )

    async def get_connector_cards(
        self,
        integration_name: str,
    ) -> SingleJson:
        """Get connector instance cards for the specified integration.

        Args:
            integration_name: The integration name
                (use ``"-"`` for all integrations).

        Returns:
            The response JSON containing connector instances.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        endpoint: str = f"/integrations/{integration_name}/connectors/-/connectorInstances"
        response: httpx.Response = await self.get(endpoint)
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {"connectorInstances": []}

        return response.json()

    async def get_installed_jobs(
        self,
        job_instance_id: str | None = None,
    ) -> SingleJson:
        """Retrieve installed job instances.

        Args:
            job_instance_id: Optional specific job instance ID.
                If ``None``, returns all job instances.

        Returns:
            The response JSON containing job instances.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        endpoint: str = "/integrations/-/jobs/-/jobInstances"
        if job_instance_id:
            endpoint += f"/{job_instance_id}"

        response: httpx.Response = await self.get(endpoint)
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {} if job_instance_id else {"jobInstances": []}

        return response.json()

    async def set_configuration_property(
        self,
        integration_instance_identifier: str,
        property_name: str,
        property_value: str,
    ) -> SingleJson:
        """Set an integration instance configuration property.

        Args:
            integration_instance_identifier: The identifier of the
                integration instance.
            property_name: The name of the property to update.
            property_value: The new value for the property.

        Returns:
            The response JSON with updated property details.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        endpoint: str = "/legacySdk:legacyUpdateConfigurationProperty"
        params: SingleJson = {
            "identifier": integration_instance_identifier,
            "propertyName": property_name,
            "format": "snake",
        }
        payload: SingleJson = {"property_value": property_value}
        response: httpx.Response = await self.put(
            endpoint,
            payload=payload,
            params=params,
        )

        return response.json()

    async def set_connector_parameter(
        self,
        connector_instance_identifier: str,
        parameter_name: str,
        parameter_value: str,
    ) -> SingleJson:
        """Set a connector instance parameter.

        Args:
            connector_instance_identifier: The identifier of the
                connector instance.
            parameter_name: The name of the parameter to update.
            parameter_value: The new value for the parameter.

        Returns:
            The response JSON with updated parameter details.

        Raises:
            httpx.HTTPStatusError: If the API request fails.

        """
        endpoint: str = "/legacySdk:legacyUpdateConnectorParameter"
        params: SingleJson = {
            "identifier": connector_instance_identifier,
            "parameterName": parameter_name,
            "format": "snake",
        }
        payload: SingleJson = {"parameter_value": parameter_value}
        response: httpx.Response = await self.put(
            endpoint,
            payload=payload,
            params=params,
        )

        return response.json()

    async def save_or_update_job(
        self,
        job_data: SingleJson,
    ) -> SingleJson:
        """Save or update a job's parameters.

        The ``job_data`` dict must contain:

        - **name** (``str``): The full GCP resource path of the
          job instance.
        - **parameters** (``list[dict]``): A list of parameter dicts.

        Args:
            job_data: The full job dict with updated parameters.

        Returns:
            The response JSON from the platform.

        Raises:
            httpx.HTTPStatusError: If the API request fails.
            EmptyMandatoryValues: If ``job_data`` is missing required fields.
            ParameterValidationError: If the resource path cannot be parsed.

        """
        resource_path: str | None = job_data.get("name")
        if resource_path is None:
            raise EmptyMandatoryValues(
                "Job data must include a 'name' field with the resource path. "
                "Example (1P resource path): "
                "projects/{project}/locations/{location}/instances/{instance}/"
                "integrations/{integrationId}/jobs/{jobId}/"
                "jobInstances/{instanceId}. "
                "Cannot determine the PATCH endpoint without the resource path."
            )

        parameters: list[SingleJson] | None = job_data.get("parameters")
        if parameters is None:
            raise EmptyMandatoryValues("Job data is missing 'parameters' field, Nothing to update.")

        segment_pos: int = resource_path.find("integrations/")
        if segment_pos == -1:
            raise ParameterValidationError(
                param_name="name",
                value=resource_path,
                message=("Cannot parse resource path. Expected path to contain 'integrations/'"),
            )
        endpoint: str = f"/{resource_path[segment_pos:]}"

        params: SingleJson = {"updateMask": "parameters"}
        payload: SingleJson = {"parameters": parameters}
        response: httpx.Response = await self.patch(
            endpoint,
            payload=payload,
            params=params,
        )
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {}

        return response.json()
