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

import asyncio
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from TIPCommon.base.job import Job
from TIPCommon.data_models import (
    ConnectorCard,
    InstalledIntegrationInstance,
)
from TIPCommon.rest.async_soar_platform_clients.soar_api_client import (
    AsyncMarketplaceApi,
)
from TIPCommon.rest.async_soar_platform_clients.secops_soar import AsyncChronicleSOAR

from ..core.constants import (
    LIST_ALL_RESULTS_VALUE,
    CONNECTORS_KEY,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    SYNC_CREDENTIAL_JOB_SCRIPT_NAME,
    NameIdentifierMap,
    TIMEOUT_THRESHOLD_MS,
    ASYNC_SEMAPHORE_LIMIT,
    SUCCESS_EXIT_CODE,
    PATH_TO_CLIPASSWORDSDK_JOB_PARAM,
    USERNAME_JOB_PARAM,
    PASSWORD_JOB_PARAM,
)
from ..core.credential_provider_manager import CommandResult, CredentialProviderManager
from ..core.datamodels import ConfigurationParameters
from ..core import exceptions
from ..core.utils import (
    validate_ip_address,
    build_instance_name_lookup,
    build_connector_name_lookup,
    build_job_name_lookup,
    build_param_index,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class SyncIntegrationCredentialJob(Job):
    """Syncs credentials from CyberArk Credential Provider to SOAR.

    Reads a credential mapping JSON from job parameters, fetches
    the corresponding secrets from CyberArk Credential Provider, and
    uses the SOAR SDK to set configuration properties on
    integration instances, connectors, and jobs.
    """

    def __init__(self) -> None:
        super().__init__(SYNC_CREDENTIAL_JOB_SCRIPT_NAME)
        self.credential_mapping: SingleJson = {}
        self.environment_name: str = ""
        self.instance_name_to_identifier: NameIdentifierMap = {}
        self.connector_name_to_identifier: NameIdentifierMap = {}
        self.job_start_time: int = int(time.time() * 1000)
        self._secret_cache: dict[str, str] = {}
        self.execution_errors: list[str] = []
        self.configuration_parameters: ConfigurationParameters | None = None

    def _get_configuration_parameters(self) -> ConfigurationParameters:
        """Resolve and cache configuration parameters directly from Job configuration.

        Returns:
            ConfigurationParameters object.
        """
        if self.configuration_parameters is None:
            sdk_path_str = (
                getattr(self.params, PATH_TO_CLIPASSWORDSDK_JOB_PARAM, None)
                or getattr(self.params, "path_to_clipasswordsdk", None)
            )
            username = (
                getattr(self.params, USERNAME_JOB_PARAM, None)
                or getattr(self.params, "username_for_credential_provider_for_linux", None)
            )
            password = (
                getattr(self.params, PASSWORD_JOB_PARAM, None)
                or getattr(self.params, "password_for_credential_provider_for_linux", None)
            )
            ssh_private_key_path_str = getattr(self.params, "ssh_private_key_path", None)
            ssh_private_key_path = (
                Path(ssh_private_key_path_str)
                if ssh_private_key_path_str
                else None
            )

            self.configuration_parameters = ConfigurationParameters(
                sdk_path=Path(sdk_path_str) if sdk_path_str else Path(""),
                username=username or "",
                docker_gateway_ip=getattr(self.params, "docker_gateway_ip_address", ""),
                host_public_key_data=getattr(self.params, "host_public_key", ""),
                ssh_private_key_path=ssh_private_key_path,
                password=password,
            )

        return self.configuration_parameters

    def _init_api_clients(self) -> CredentialProviderManager:
        """Initialize the CyberArk Credential Provider client.

        Returns:
            CredentialProviderManager client instance.
        """
        params = self._get_configuration_parameters()
        return CredentialProviderManager(
            configuration_parameters=params,
        )

    def _validate_params(self) -> None:
        """Validate job parameters before execution."""
        credential_mapping_str = getattr(self.params, "credential_mapping", None)
        try:
            self.credential_mapping = (
                json.loads(credential_mapping_str)
                if credential_mapping_str
                else {}
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid Credential Mapping JSON: {e}") from e

        params = self._get_configuration_parameters()
        validate_ip_address(params.docker_gateway_ip)

    def _perform_job(self) -> None:
        """Fetch secrets and sync to SOAR platform."""
        self.logger.info(f"Starting {SYNC_CREDENTIAL_JOB_SCRIPT_NAME} Job.")
        asyncio.run(self._async_main())
        self.logger.info(f"{SYNC_CREDENTIAL_JOB_SCRIPT_NAME} Job completed.")

    async def _async_main(self) -> None:
        """Main async execution."""
        self.environment_name = getattr(self.params, "environment_name", "")
        self.logger.info(
            f"Starting credential sync for environment: {self.environment_name}"
        )

        async_soar = AsyncChronicleSOAR(self.soar_job)
        try:
            api = AsyncMarketplaceApi(async_soar)
            semaphore = asyncio.Semaphore(ASYNC_SEMAPHORE_LIMIT)

            await self._prefetch_all_secrets(semaphore)

            if self._is_approaching_timeout():
                return

            await self._sync_integration_instances(api, semaphore)

            if self._is_approaching_timeout():
                return

            await self._sync_connectors(api, semaphore)

            if self._is_approaching_timeout():
                return

            await self._sync_jobs(api, semaphore)
        finally:
            await async_soar.close()

        if self.execution_errors:
            error_summary = "\n".join(f"- {err}" for err in self.execution_errors)
            raise exceptions.CyberArkCredentialProviderSyncError(
                f"Sync completed with errors:\n{error_summary}"
            )

    async def _prefetch_all_secrets(
        self,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Extract all unique secret locations from credential_mapping and pre-fetch them concurrently.

        Args:
            semaphore: Semaphore for concurrent requests.
        """
        locations: set[str] = set()

        for section in (INTEGRATION_INSTANCES_KEY, CONNECTORS_KEY, JOBS_KEY):
            mapping = self.credential_mapping.get(section, {})
            if isinstance(mapping, dict):
                for _, param_mapping in mapping.items():
                    if isinstance(param_mapping, dict):
                        locations.update(param_mapping.values())

        uncached_locations = [loc for loc in locations if loc not in self._secret_cache]

        if not uncached_locations:
            return

        async def fetch_one(secret_loc: str) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._get_secret_from_cyberark_async(secret_loc)
                except Exception:
                    # Secret fetch failures during pre-fetch are handled & logged in context
                    # during the parameter update phase.
                    pass

        tasks = [fetch_one(loc) for loc in uncached_locations]
        await asyncio.gather(*tasks)

    def _is_approaching_timeout(self) -> bool:
        """Check if the job is approaching its timeout.

        Returns:
            True if job execution time exceeds timeout threshold, False otherwise.
        """
        if int(time.time() * 1000) - self.job_start_time > TIMEOUT_THRESHOLD_MS:
            self.logger.info("Timeout approaching. Stopping execution gracefully.")
            return True
        return False

    async def _get_secret_from_cyberark_async(self, secret_location: str) -> str:
        """Fetch a secret from CyberArk asynchronously (via thread pool).

        Args:
            secret_location: A string in the format
            "AppDescs.AppID=<...>;Safe=<...>;Object=<...>[;Folder=<...>]"

        Returns:
            The secret content.

        Raises:
            CyberArkCredentialProviderValidationError: if the location string is invalid
            CyberArkCredentialProviderSDKCommandError: if the secret cannot be fetched.
        """
        if secret_location in self._secret_cache:
            return self._secret_cache[secret_location]

        result: CommandResult = await asyncio.to_thread(
            self.api_client.get_password_from_location,
            secret_location=secret_location,
        )

        if result.exit_code != SUCCESS_EXIT_CODE:
            raise exceptions.CyberArkCredentialProviderSDKCommandError(
                f"Failed to retrieve secret from location '{secret_location}'. "
                f"Error: {result.error}"
            )

        secret_value: str = result.output.strip()
        self._secret_cache[secret_location] = secret_value

        return secret_value

    async def _sync_integration_instances(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for integration instances concurrently.

        Args:
            api: The async API client.
            semaphore: Semaphore for concurrent requests.
        """
        instances: SingleJson = self.credential_mapping.get(
            INTEGRATION_INSTANCES_KEY,
            {},
        )

        if not instances:
            self.logger.info(
                "No integration instances in credential mapping. Skipping."
            )
            return None

        instances_list: list[
            InstalledIntegrationInstance
        ] = await self._fetch_integration_instances(api)
        if not instances_list:
            msg = (
                f"Either the environment name '{self.environment_name}' is invalid "
                f"or no integration instances are configured in that environment."
            )
            self.logger.error(msg)
            self.execution_errors.append(msg)
            return None

        self.instance_name_to_identifier = build_instance_name_lookup(instances_list)

        self.logger.info(
            f"Found {len(self.instance_name_to_identifier)} integration instance(s) "
            f"in environment '{self.environment_name}'."
        )

        async def update_task(name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._update_single_integration_instance(
                        api,
                        name,
                        param_mapping,
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    msg = f"Failed to update instance '{name}': {e}"
                    self.logger.error(msg)
                    self.execution_errors.append(msg)

        tasks = [update_task(name, pm) for name, pm in instances.items()]
        await asyncio.gather(*tasks)

    async def _fetch_integration_instances(
        self,
        api: AsyncMarketplaceApi,
    ) -> list[InstalledIntegrationInstance]:
        """Fetch all integration instances for the configured environment.

        Args:
            api: The async API client.

        Returns:
            List of InstalledIntegrationInstance objects.
        """
        self.logger.info(
            f"Fetching integration instances for environment: {self.environment_name}"
        )

        instances = await api.get_installed_integrations_of_environment(
            environment=self.environment_name,
            integration_identifier=LIST_ALL_RESULTS_VALUE,
        )
        if isinstance(instances, dict):
            instances = (
                instances.get("integrationInstances", [])
                or instances.get("instances", [])
            )

        return [
            InstalledIntegrationInstance.from_json(instance) for instance in instances
        ]

    async def _update_single_integration_instance(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single integration instance.

        Args:
            api: The async API client.
            name: The display name of the instance.
            param_mapping: Map of parameter name -> secret location.
        """
        self.logger.info(f"Processing integration instance: {name}")

        identifier: str | None = self._resolve_instance_identifier(name)
        if identifier is None:
            self.logger.error(
                f"Skipping instance '{name}' — could not resolve identifier."
            )
            return None

        await self._set_integration_params(api, name, identifier, param_mapping)

    def _resolve_instance_identifier(
        self,
        instance_name: str,
    ) -> str | None:
        """Resolve an instance name to its identifier.

        Args:
            instance_name: The display name of the instance.

        Returns:
            The identifier string, or None if not found.
        """
        identifier: str | None = self.instance_name_to_identifier.get(instance_name)

        if identifier is None:
            msg = (
                f"Integration instance '{instance_name}' not found in environment '{self.environment_name}'."
            )
            self.logger.error(msg)
            self.execution_errors.append(msg)

        return identifier

    async def _update_parameter(
        self,
        target_type: str,
        target_name: str,
        target_id: str,
        param_name: str,
        secret_id: str,
        update_callback: Callable[[str], Any],
    ) -> None:
        """Helper to fetch a secret from CyberArk and execute the update callback.

        Args:
            target_type: "instance", "connector", or "job".
            target_name: Display name of the target.
            target_id: Resolved identifier of the target.
            param_name: Name of the parameter to update.
            secret_id: CyberArk secret location string.
            update_callback: Callback function to perform the actual update.
        """
        # 1. Fetch secret value from CyberArk (uses in-memory per-run cache)
        secret_value = await self._get_secret_from_cyberark_async(
            secret_location=secret_id
        )

        # 2. Perform the update via the callback
        if asyncio.iscoroutinefunction(update_callback):
            await update_callback(secret_value)
        else:
            update_callback(secret_value)

        self.logger.info(
            f"Updated '{param_name}' on {target_type} '{target_name}' (id: {target_id}) "
            f"from secret location '{secret_id}'."
        )

    async def _set_integration_params(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        identifier: str,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on an integration instance.

        Args:
            api: The async API client.
            name: Display name of the instance.
            identifier: Resolved instance identifier.
            param_mapping: Param names to secret IDs.
        """
        async def update_single_param(param_name: str, secret_id: str) -> None:
            try:

                async def update_property(value: str) -> None:
                    await api.set_configuration_property(
                        integration_instance_identifier=identifier,
                        property_name=param_name,
                        property_value=value,
                    )

                await self._update_parameter(
                    target_type="instance",
                    target_name=name,
                    target_id=identifier,
                    param_name=param_name,
                    secret_id=secret_id,
                    update_callback=update_property,
                )
            except Exception as e:
                msg = (
                    f"Failed to update '{param_name}' on instance '{name}' "
                    f"(id: {identifier}) from secret location '{secret_id}': {e}"
                )
                self.logger.error(msg)
                self.execution_errors.append(msg)

        tasks = [
            update_single_param(p_name, s_id) for p_name, s_id in param_mapping.items()
        ]
        await asyncio.gather(*tasks)

    async def _sync_connectors(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for connectors.

        Args:
            api: The async API client.
            semaphore: Semaphore for concurrent requests.
        """
        connectors: SingleJson = self.credential_mapping.get(CONNECTORS_KEY, {})

        if not connectors:
            self.logger.info("No connectors in credential mapping. Skipping.")
            return None

        cards: list[ConnectorCard] = await self._fetch_connector_cards(api)
        if not cards:
            self.logger.warn("No connectors found in the platform.")
            return None

        self.connector_name_to_identifier = build_connector_name_lookup(cards)

        self.logger.info(
            f"Found {len(self.connector_name_to_identifier)} connector(s)."
        )

        async def update_task(name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._update_single_connector(api, name, param_mapping)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    msg = f"Failed to update connector '{name}': {e}"
                    self.logger.error(msg)
                    self.execution_errors.append(msg)

        tasks = [update_task(name, pm) for name, pm in connectors.items()]
        await asyncio.gather(*tasks)

    async def _fetch_connector_cards(
        self,
        api: AsyncMarketplaceApi,
    ) -> list[ConnectorCard]:
        """Fetch connector cards for all connectors.

        Args:
            api: The async API client.

        Returns:
            List of ConnectorCard objects.
        """
        response = await api.get_connector_cards(
            integration_name=LIST_ALL_RESULTS_VALUE,
        )
        cards = response.get("connectorInstances", []) or response.get("items", [])

        return [ConnectorCard.from_json(card) for card in cards]

    async def _update_single_connector(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single connector.

        Args:
            api: The async API client.
            name: The display name of the connector.
            param_mapping: Map of parameter name -> secret location.
        """
        self.logger.info(f"Processing connector: {name}")

        identifier: str | None = self._resolve_connector_identifier(name)
        if identifier is None:
            self.logger.error(
                f"Skipping connector '{name}' — could not resolve identifier."
            )
            return None

        await self._set_connector_params(api, name, identifier, param_mapping)

    def _resolve_connector_identifier(
        self,
        connector_name: str,
    ) -> str | None:
        """Resolve a connector display name to its identifier.

        Args:
            connector_name: The display name of the connector.

        Returns:
            The identifier string, or None if not found.
        """
        identifier: str | None = self.connector_name_to_identifier.get(connector_name)

        if identifier is None:
            msg = f"Connector '{connector_name}' not found."
            self.logger.error(msg)
            self.execution_errors.append(msg)

        return identifier

    async def _set_connector_params(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        identifier: str,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on a connector instance.

        Args:
            api: The async API client.
            name: Display name of the connector.
            identifier: Resolved connector identifier.
            param_mapping: Param names to secret IDs.
        """
        async def update_single_param(param_name: str, secret_id: str) -> None:
            try:

                async def update_param(value: str) -> None:
                    await api.set_connector_parameter(
                        connector_instance_identifier=identifier,
                        parameter_name=param_name,
                        parameter_value=value,
                    )

                await self._update_parameter(
                    target_type="connector",
                    target_name=name,
                    target_id=identifier,
                    param_name=param_name,
                    secret_id=secret_id,
                    update_callback=update_param,
                )
            except Exception as e:
                msg = (
                    f"Failed to update '{param_name}' on connector '{name}' "
                    f"(id: {identifier}) from secret location '{secret_id}': {e}"
                )
                self.logger.error(msg)
                self.execution_errors.append(msg)

        tasks = [
            update_single_param(p_name, s_id) for p_name, s_id in param_mapping.items()
        ]
        await asyncio.gather(*tasks)

    async def _sync_jobs(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for jobs.

        Args:
            api: The async API client.
            semaphore: Semaphore for concurrent requests.
        """
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})

        if not jobs:
            self.logger.info("No jobs in credential mapping. Skipping.")
            return None

        job_instances: list[SingleJson] | None = await self._fetch_job_instances(api)
        if job_instances is None:
            return None

        name_to_job: dict[str, SingleJson] = build_job_name_lookup(job_instances)

        self.logger.info(f"Found {len(name_to_job)} job(s).")

        async def update_task(job_name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    self.logger.info(f"Processing job: {job_name}")
                    await self._update_single_job(
                        api, job_name, param_mapping, name_to_job
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    msg = f"Failed to update job '{job_name}': {e}"
                    self.logger.error(msg)
                    self.execution_errors.append(msg)

        tasks = [update_task(name, pm) for name, pm in jobs.items()]
        await asyncio.gather(*tasks)

    async def _fetch_job_instances(
        self,
        api: AsyncMarketplaceApi,
    ) -> list[SingleJson] | None:
        """Fetch and normalise the list of installed jobs.

        Args:
            api: The async API client.

        Returns:
            List of job dicts, or None if error or no jobs found.
        """
        installed_jobs_response: SingleJson = await api.get_installed_jobs()

        if (
            isinstance(installed_jobs_response, dict)
            and "job_instances" in installed_jobs_response
        ):
            job_instances: list[SingleJson] = installed_jobs_response["job_instances"]
        elif isinstance(installed_jobs_response, list):
            job_instances = installed_jobs_response
        else:
            self.logger.error(
                f"Unexpected response format from get_installed_jobs: "
                f"expected dict or list, got {type(installed_jobs_response).__name__}."
            )
            return None

        if not job_instances:
            self.logger.warn("No installed jobs found.")
            return None

        return job_instances

    async def _update_single_job(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        param_mapping: SingleJson,
        name_to_job: dict[str, SingleJson],
    ) -> None:
        """Update parameters for a single job.

        Args:
            api: The async API client.
            job_name: The display name of the job.
            param_mapping: Map of param name -> secret ID.
            name_to_job: Lookup of display name -> job dict.
        """
        resolved: (
            tuple[SingleJson, list[SingleJson]] | None
        ) = await self._resolve_job_data(api, job_name, name_to_job)
        if resolved is None:
            return None

        job_data: SingleJson
        parameters: list[SingleJson]
        job_data, parameters = resolved

        param_index: dict[str, int] = build_param_index(parameters)

        updated_count: int = await self._apply_secrets_to_params(
            job_name,
            param_mapping,
            parameters,
            param_index,
        )

        if updated_count == 0:
            self.logger.warn(
                f"No parameters updated for job '{job_name}' — skipping save."
            )
            return None

        job_data["parameters"] = parameters
        await self._persist_job(api, job_name, job_data, updated_count)

    async def _resolve_job_data(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        name_to_job: dict[str, SingleJson],
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters are available for update.

        If the list response omitted parameters, fetches the full job details.

        Args:
            api: The async API client.
            job_name: The display name of the job.
            name_to_job: Lookup of display name -> job dict.

        Returns:
            A ``(job_data, parameters)`` tuple, or ``None`` if the job cannot be
            resolved.
        """
        job_data: SingleJson | None = name_to_job.get(job_name)
        if job_data is None:
            msg = f"Job '{job_name}' not found."
            self.logger.error(msg)
            self.execution_errors.append(msg)
            return None

        job_data = dict(job_data)

        parameters: list[SingleJson] | None = job_data.get("parameters")
        if parameters is None:
            job_data, parameters = await self._fetch_full_job_details(
                api,
                job_name,
                job_data,
            ) or (
                None,
                None,
            )
            if job_data is None:
                return None

        if not isinstance(parameters, list):
            self.logger.error(
                f"Unexpected parameters format for job '{job_name}': "
                f"expected list, got {type(parameters).__name__}."
            )
            return None

        if not parameters:
            self.logger.warn(
                f"Job '{job_name}' has an empty parameters list — nothing to update."
            )
            return None

        return job_data, parameters

    async def _fetch_full_job_details(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        job_data: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Fetch full job details when the list response omits parameters.

        Args:
            api: The async API client.
            job_name: The display name of the job.
            job_data: The partial job dict from the list response.

        Returns:
            A ``(job_data, parameters)`` tuple or ``None`` on failure.
        """
        job_instance_id = job_data.get("id")
        if job_instance_id is None:
            self.logger.error(
                f"Job '{job_name}' has no id and no parameters — cannot update."
            )
            return None

        try:
            full_job: SingleJson = await api.get_installed_jobs(
                job_instance_id=job_instance_id,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to fetch full details for job '{job_name}' "
                f"(id: {job_instance_id}): {e}"
            )
            return None

        if not isinstance(full_job, dict):
            self.logger.error(
                f"Unexpected response format when fetching job details for "
                f"'{job_name}': expected dict, got "
                f"{type(full_job).__name__}."
            )
            return None

        return full_job, full_job.get("parameters", [])

    async def _apply_secrets_to_params(
        self,
        job_name: str,
        param_mapping: SingleJson,
        parameters: list[SingleJson],
        param_index: dict[str, int],
    ) -> int:
        """Fetch secrets and swap values into the parameters list.

        Args:
            job_name: The display name of the job.
            param_mapping: Map of param name -> secret ID.
            parameters: The mutable parameter list.
            param_index: Name -> index lookup.

        Returns:
            The number of parameters successfully updated.
        """
        async def update_single_param(param_name: str, secret_id: str) -> bool:
            if param_name not in param_index:
                msg = f"Parameter '{param_name}' not found on job '{job_name}'."
                self.logger.error(msg)
                self.execution_errors.append(msg)
                return False

            try:
                idx: int = param_index[param_name]

                def update_job_param(value: str) -> None:
                    parameters[idx]["value"] = value

                await self._update_parameter(
                    target_type="job",
                    target_name=job_name,
                    target_id=job_name,
                    param_name=param_name,
                    secret_id=secret_id,
                    update_callback=update_job_param,
                )
                return True
            except Exception as e:
                msg = (
                    f"Failed to fetch secret from location '{secret_id}' for param "
                    f"'{param_name}' on job '{job_name}': {e}"
                )
                self.logger.error(msg)
                self.execution_errors.append(msg)
                return False

        tasks = [
            update_single_param(p_name, s_id) for p_name, s_id in param_mapping.items()
        ]
        results = await asyncio.gather(*tasks)
        return sum(1 for success in results if success)

    async def _persist_job(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        job_data: SingleJson,
        updated_count: int,
    ) -> None:
        """Save the modified job back to the platform.

        Args:
            api: The async API client.
            job_name: The display name of the job.
            job_data: The full job dict with updated parameters.
            updated_count: Number of params changed.
        """
        try:
            await api.save_or_update_job(
                job_data=job_data,
            )
            self.logger.info(
                f"Saved job '{job_name}' with {updated_count} updated parameter(s)."
            )
        except Exception as e:
            self.logger.error(f"Failed to save job '{job_name}': {e}")


def main() -> None:
    SyncIntegrationCredentialJob().start()


if __name__ == "__main__":
    main()
