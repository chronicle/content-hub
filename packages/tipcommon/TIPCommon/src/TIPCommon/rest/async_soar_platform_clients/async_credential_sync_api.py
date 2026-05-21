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

"""Async API client for credential sync operations on Chronicle SOAR."""

from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.rest.async_soar_platform_clients.base_soar_api import BaseAsyncSoarApi
from TIPCommon.rest.async_soar_platform_clients.constants import (
    STATUS_CODE_NO_CONTENT,
)
from TIPCommon.utils import escape_odata_literal

if TYPE_CHECKING:
    import httpx

    from TIPCommon.types import SingleJson


class AsyncCredentialSyncApi(BaseAsyncSoarApi):
    """Async API client for credential sync operations.

    Provides async methods for fetching integration instances,
    connectors, and jobs, as well as updating their configuration
    properties and parameters.
    """

    async def get_installed_integrations_of_environment(
        self,
        integration_identifier: str,
        environment: str,
    ) -> SingleJson:
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
        endpoint: str = (
            f"/integrations/{integration_identifier}/integrationInstances"
        )
        env_literal: str = escape_odata_literal(
            "*" if environment == "Shared Instances" else environment,
        )
        params: SingleJson = {
            "$filter": f"environment eq '{env_literal}'",
        }
        response: httpx.Response = await self.get(endpoint, params=params)
        if response.status_code == STATUS_CODE_NO_CONTENT:
            return {"integrationInstances": []}

        return response.json()

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
        endpoint: str = (
            f"/integrations/{integration_name}/connectors/-/connectorInstances"
        )
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
            return {"jobInstances": []}

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
            ValueError: If ``job_data`` is missing required fields.

        """
        resource_path: str | None = job_data.get("name")
        if resource_path is None:
            raise ValueError(
                "Job data must include a 'name' field with the resource path."
            )

        parameters = job_data.get("parameters")
        if parameters is None:
            raise ValueError(
                "Job data is missing 'parameters' field. Nothing to update."
            )

        segment_pos: int = resource_path.find("integrations/")
        if segment_pos == -1:
            raise ValueError(
                f"Cannot parse resource path: '{resource_path}'. "
                "Expected path to contain 'integrations/'."
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
