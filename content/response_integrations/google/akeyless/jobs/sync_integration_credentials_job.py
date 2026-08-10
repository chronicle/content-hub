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
import operator
import re
import time
from itertools import starmap
from typing import TYPE_CHECKING, Any

from TIPCommon.base.job import Job
from TIPCommon.rest.async_soar_platform_clients.secops_soar import AsyncChronicleSOAR
from TIPCommon.rest.async_soar_platform_clients.soar_api_client import (
    AsyncMarketplaceApi,
)

from ..core.authentication import IntegrationParameters, build_auth_params
from ..core.constants import (
    ANY_INTEGRATION_FILTER_VALUE,
    ASYNC_SEMAPHORE_LIMIT,
    CONNECTORS_KEY,
    DEFAULT_SECRET_VERSION,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    SYNC_CREDENTIALS_JOB_SCRIPT_NAME,
    TIMEOUT_THRESHOLD_MS,
    NameIdentifierMap,
    SecretCacheKey,
)
from ..core.exceptions import (
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
    JobSaveError,
    SecretAccessError,
)
from ..core.manager import AkeylessClient, AkeylessClientConfig
from ..core.utils import build_lookup_with_warnings, mask_id

if TYPE_CHECKING:
    from collections.abc import Callable

    from TIPCommon.types import SingleJson

RESOURCE_NAME_PATTERN: re.Pattern = re.compile(r"^(?P<secret>[^:]+)(?::(?P<version>.+))?$")


class SyncIntegrationCredentialsJob(Job):
    """Syncs credentials from Akeyless to SOAR.

    Reads a credential mapping JSON from job parameters, fetches
    the corresponding secrets from Akeyless, and
    uses the SOAR SDK to set configuration properties on
    integration instances, connectors, and jobs.
    """

    def __init__(self) -> None:
        super().__init__(SYNC_CREDENTIALS_JOB_SCRIPT_NAME)
        self.akeyless_client: AkeylessClient | None = None
        self.credential_mapping: SingleJson = {}
        self.environment_name: str = ""
        self.instance_name_to_identifier: NameIdentifierMap = {}
        self.connector_name_to_identifier: NameIdentifierMap = {}
        self.job_start_time: int = int(time.time() * 1000)
        self._secret_cache: dict[SecretCacheKey, str] = {}
        self.execution_errors: list[str] = []

    def _init_api_clients(self) -> None:
        """No-op. Async API clients are initialized inside the async event loop."""

    def _init_akeyless_client(self) -> None:
        """Initialize the Akeyless client."""
        auth_params: IntegrationParameters = build_auth_params(self.soar_job)

        config = AkeylessClientConfig(
            access_id=auth_params.access_id,
            access_key=auth_params.access_key,
            api_gateway_url=auth_params.api_gateway_url,
            verify_ssl=auth_params.verify_ssl,
        )

        self.akeyless_client = AkeylessClient(
            config,
            logger=self.logger,
        )

    def _validate_params(self) -> None:
        """Validate job parameters before execution.

        Parses and validates the Credential Mapping JSON
        string provided via the job configuration UI.

        Raises:
            InvalidConfigurationError: If the JSON string
                is invalid or if the mapped values are in an invalid format.

        """
        try:
            self.credential_mapping = (
                json.loads(self.params.credential_mapping)
                if self.params.credential_mapping
                else {}
            )
        except json.JSONDecodeError as e:
            msg = f"Invalid Credential Mapping JSON syntax: {e}"
            raise InvalidConfigurationError(msg) from e

        if not isinstance(self.credential_mapping, dict):
            msg = "Credential Mapping must be a dictionary."
            raise InvalidConfigurationError(msg)

        valid_keys = {INTEGRATION_INSTANCES_KEY, CONNECTORS_KEY, JOBS_KEY}
        invalid_keys = set(self.credential_mapping.keys()) - valid_keys
        if invalid_keys:
            msg = (
                f"Invalid root keys in Credential Mapping: {list(invalid_keys)}. Allowed keys are: {list(valid_keys)}."
            )
            raise InvalidConfigurationError(msg)

        for category in valid_keys:
            category_mapping = self.credential_mapping.get(category, {})
            if not isinstance(category_mapping, dict):
                msg = f"Category '{category}' must be a dictionary."
                raise InvalidConfigurationError(msg)

            for component_name, param_mapping in category_mapping.items():
                if not isinstance(param_mapping, dict):
                    msg = f"Parameters for '{component_name}' in category '{category}' must be a dictionary."
                    raise InvalidConfigurationError(msg)

                for param_name, mapped_value in param_mapping.items():
                    val = str(mapped_value).strip()
                    if not RESOURCE_NAME_PATTERN.match(val):
                        msg = (
                            f"Invalid format for parameter '{param_name}' of '{component_name}' "
                            f"in category '{category}': '{val}'. "
                            f"Expected format: 'secret_name' or 'secret_name:version'."
                        )
                        raise InvalidConfigurationError(msg)

    def _perform_job(self) -> None:
        """Fetch secrets and sync to SOAR platform."""
        self.logger.info("Starting 'Sync Integration Credentials Job'.")
        asyncio.run(self._async_main())
        self.logger.info("'Sync Integration Credentials Job' completed.")

    async def _async_main(self) -> None:
        """Execute the job asynchronously.

        Raises:
            IntegrationCredentialSyncError: If any errors occur during credential sync.

        """
        self._init_akeyless_client()
        self.environment_name = self.params.environment_name
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
            self.logger.info("Closing async client session.")
            await async_soar.close()

        if self.execution_errors:
            summary = "\n".join(f"- {err}" for err in self.execution_errors)
            msg = f"Sync completed with errors:\n{summary}"
            raise IntegrationCredentialSyncError(msg)

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
                for param_mapping in mapping.values():
                    if isinstance(param_mapping, dict):
                        locations.update(str(v).strip() for v in param_mapping.values())

        uncached_locations = [
            loc for loc in locations
            if self._resolve_secret_and_version(loc) not in self._secret_cache
        ]

        if not uncached_locations:
            return

        async def fetch_one(secret_loc: str) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    secret_id, version_id = self._resolve_secret_and_version(secret_loc)
                    await self._fetch_secret_value_pre_resolved(
                        secret_id,
                        version_id,
                        context_label=f"pre-fetch '{secret_loc}'",
                    )
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.debug("Failed pre-fetching secret '%s': %s", secret_loc, e)

        tasks = [fetch_one(loc) for loc in uncached_locations]
        await asyncio.gather(*tasks)

    async def _fetch_secret_value_pre_resolved(
        self,
        secret_id: str,
        version_id: str,
        *,
        context_label: str,
    ) -> str:
        """Fetch the secret value for a pre-resolved secret and version.

        Returns:
            str: The raw secret value payload.

        Raises:
            SecretAccessError: If fetching the secret from Akeyless fails.

        """
        cache_key = (secret_id, version_id)
        if cache_key in self._secret_cache:
            return self._secret_cache[cache_key]

        if self.akeyless_client is None:
            msg = "Akeyless client is not initialized."
            raise SecretAccessError(msg)

        try:
            secret_value: str = await asyncio.to_thread(
                self.akeyless_client.get_secret_value,
                secret_id=secret_id,
                version_id=version_id,
            )
        except SecretAccessError:
            raise
        except Exception as e:
            msg = f"Failed to fetch secret '{mask_id(secret_id)}' for {context_label}: {e}"
            raise SecretAccessError(msg) from e

        self._secret_cache[cache_key] = secret_value
        return secret_value

    def _is_approaching_timeout(self) -> bool:
        """Check if the job is approaching its timeout.

        Returns:
            bool: True if approaching timeout threshold, False otherwise.

        """
        if not self.job_start_time:
            return False

        if int(time.time() * 1000) - self.job_start_time > TIMEOUT_THRESHOLD_MS:
            self.logger.info("Timeout approaching. Stopping execution gracefully.")
            return True

        return False

    def _resolve_secret_and_version(self, mapped_value: str) -> tuple[str, str]:
        """Parse the mapped string, resolving the version if not explicitly provided.

        Args:
            mapped_value (str): The value from the JSON mapping (e.g., 'secret-id:version').

        Returns:
            tuple[str, str]: The (secret_id, resolved_version).

        """
        mapped_value = str(mapped_value).strip()
        if ":" in mapped_value:
            secret_id, explicit_version = mapped_value.split(":", 1)
            return secret_id, explicit_version

        secret_id = mapped_value
        if self.akeyless_client:
            resolved_version = self.akeyless_client.resolve_latest_enabled_version(
                secret_id,
            )
        else:
            resolved_version = DEFAULT_SECRET_VERSION

        return secret_id, resolved_version

    async def _update_parameter(  # ruff:ignore[too-many-arguments]
        self,
        *,
        target_type: str,
        target_name: str,
        target_id: str,
        param_name: str,
        mapped_value: str,
        update_callback: Callable[[str], Any],
    ) -> None:
        """Fetch a secret from Akeyless and execute the update callback.

        Args:
            target_type: "instance", "connector", or "job".
            target_name: Display name of the target.
            target_id: Resolved identifier of the target.
            param_name: Name of the parameter to update.
            mapped_value: Akeyless secret location string ('secret_name' or 'secret_name:version').
            update_callback: Callback function to perform the actual update.

        """
        context: str = f"param '{param_name}' on {target_type} '{target_name}' (id: {target_id})"
        secret_id, version_id = self._resolve_secret_and_version(mapped_value)

        secret_value = await self._fetch_secret_value_pre_resolved(
            secret_id,
            version_id,
            context_label=context,
        )

        if asyncio.iscoroutinefunction(update_callback):
            await update_callback(secret_value)
        else:
            update_callback(secret_value)

        self.logger.info(
            f"Updated '{param_name}' on {target_type} '{target_name}' (id: {target_id}) "
            f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
        )

    async def _sync_integration_instances(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for integration instances concurrently."""
        instances: SingleJson = self.credential_mapping.get(
            INTEGRATION_INSTANCES_KEY,
            {},
        )

        if not instances:
            self.logger.info("No integration instances in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(instances)} integration instance(s)...")

        self.logger.info(
            f"Fetching integration instances for environment: {self.environment_name}"
        )
        response = await api.get_installed_integrations_of_environment(
            integration_identifier=ANY_INTEGRATION_FILTER_VALUE,
            environment=self.environment_name,
        )
        instances_list = response.get("instances", []) or response.get(
            "integrationInstances",
            [],
        )
        if not instances_list:
            msg = (
                f"Either the environment name '{self.environment_name}' is invalid "
                f"or no integration instances are configured in that environment."
            )
            self.logger.error(msg)
            self.execution_errors.append(msg)
            return

        self.instance_name_to_identifier = self._build_instance_name_lookup_from_json(
            instances_list,
        )

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
                except Exception as e:  # ruff:ignore[blind-except]
                    msg = f"Failed to update instance '{name}': {e}"
                    self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                    self.execution_errors.append(msg)

        tasks = list(starmap(update_task, instances.items()))
        await asyncio.gather(*tasks)

    def _build_instance_name_lookup_from_json(
        self,
        instances: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a name -> identifier mapping from raw JSON instances.

        Returns:
            NameIdentifierMap: Mapping from display name to identifier.

        """
        return build_lookup_with_warnings(
            items=instances,
            get_key=lambda i: i.get("displayName") or i.get("instanceName", ""),
            get_value=lambda i: i.get("identifier", ""),
            entity_type="instance name",
            logger=self.logger,
        )

    async def _update_single_integration_instance(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single integration instance.

        Args:
            api: The async API client.
            name (str): Display name of the instance.
            param_mapping (SingleJson): Param names to secret IDs.

        """
        self.logger.info("Processing integration instance: %s", name)

        identifier: str | None = self._resolve_instance_identifier(name)
        if identifier is None:
            self.logger.error("Skipping instance '%s' — could not resolve identifier.", name)
            return

        await self._set_integration_params(api, name, identifier, param_mapping)

    def _resolve_instance_identifier(
        self,
        instance_name: str,
    ) -> str | None:
        """Resolve an instance name to its identifier.

        Args:
            instance_name (str): The display name of the instance.

        Returns:
            str | None: The identifier string, or None if not found.

        """
        identifier: str | None = self.instance_name_to_identifier.get(instance_name)

        if identifier is None:
            env: str = self.environment_name
            available: list[str] = list(self.instance_name_to_identifier.keys())
            msg = (
                f"Integration instance '{instance_name}' not found in environment "
                f"'{env}'. Available instances: {available}."
            )
            self.logger.error(msg)
            self.execution_errors.append(msg)

        return identifier

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
            name (str): Display name of the instance.
            identifier (str): Resolved instance identifier.
            param_mapping (SingleJson): Param names to secret IDs.

        """
        async def update_single_param(param_name: str, mapped_value: str) -> None:
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
                    mapped_value=mapped_value,
                    update_callback=update_property,
                )
            except Exception as e:  # ruff:ignore[blind-except]
                msg = (
                    f"Failed to update '{param_name}' on instance '{name}' "
                    f"(id: {identifier}): {e}"
                )
                self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                self.execution_errors.append(msg)

        tasks = list(starmap(update_single_param, param_mapping.items()))
        await asyncio.gather(*tasks)

    async def _sync_connectors(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for connectors concurrently."""
        connectors: SingleJson = self.credential_mapping.get(CONNECTORS_KEY, {})

        if not connectors:
            self.logger.info("No connectors in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(connectors)} connector(s)...")

        response = await api.get_connector_cards(
            integration_name=ANY_INTEGRATION_FILTER_VALUE,
        )
        cards = response.get("connectorInstances", []) or response.get("items", [])
        if not cards:
            self.logger.warn("No connectors found in the platform.")
            return

        self.connector_name_to_identifier = self._build_connector_name_lookup_from_json(
            cards,
        )

        self.logger.info(f"Found {len(self.connector_name_to_identifier)} connector(s).")

        async def update_task(name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._update_single_connector(
                        api,
                        name,
                        param_mapping,
                    )
                except Exception as e:  # ruff:ignore[blind-except]
                    msg = f"Failed to update connector '{name}': {e}"
                    self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                    self.execution_errors.append(msg)

        tasks = list(starmap(update_task, connectors.items()))
        await asyncio.gather(*tasks)

    def _build_connector_name_lookup_from_json(
        self,
        connector_cards: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a display_name -> identifier mapping from raw JSON.

        Returns:
            NameIdentifierMap: Mapping from connector display name to identifier.

        """
        return build_lookup_with_warnings(
            items=connector_cards,
            get_key=lambda c: c.get("displayName", ""),
            get_value=lambda c: c.get("identifier", ""),
            entity_type="connector name",
            logger=self.logger,
        )

    async def _update_single_connector(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single connector.

        Args:
            api: The async API client.
            name (str): Display name of the connector.
            param_mapping (SingleJson): Param names to secret IDs.

        """
        self.logger.info("Processing connector: %s", name)

        identifier: str | None = self._resolve_connector_identifier(name)
        if identifier is None:
            self.logger.error("Skipping connector '%s' — could not resolve identifier.", name)
            return

        await self._set_connector_params(api, name, identifier, param_mapping)

    def _resolve_connector_identifier(
        self,
        connector_name: str,
    ) -> str | None:
        """Resolve a connector display name to its identifier.

        Args:
            connector_name (str): The display name of the connector.

        Returns:
            str | None: The identifier string, or None if not found.

        """
        identifier: str | None = self.connector_name_to_identifier.get(connector_name)
        if identifier is None:
            available: list[str] = list(self.connector_name_to_identifier.keys())
            msg = f"Connector '{connector_name}' not found. Available connectors: {available}."
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
            name (str): Display name of the connector.
            identifier (str): Resolved connector identifier.
            param_mapping (SingleJson): Param names to secret IDs.

        """
        async def update_single_param(param_name: str, mapped_value: str) -> None:
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
                    mapped_value=mapped_value,
                    update_callback=update_param,
                )
            except Exception as e:  # ruff:ignore[blind-except]
                msg = (
                    f"Failed to update '{param_name}' on connector '{name}' "
                    f"(id: {identifier}): {e}"
                )
                self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                self.execution_errors.append(msg)

        tasks = list(starmap(update_single_param, param_mapping.items()))
        await asyncio.gather(*tasks)

    async def _sync_jobs(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for jobs concurrently."""
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})

        if not jobs:
            self.logger.info("No jobs in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(jobs)} job(s)...")

        job_instances: list[SingleJson] | None = await self._fetch_job_instances(api)
        if job_instances is None:
            return

        name_to_job: SingleJson = self._build_job_name_lookup(job_instances)

        self.logger.info(f"Found {len(name_to_job)} job(s).")

        async def update_task(job_name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    self.logger.info("Processing job: %s", job_name)
                    await self._update_single_job(
                        api,
                        job_name,
                        param_mapping,
                        name_to_job,
                    )
                except Exception as e:  # ruff:ignore[blind-except]
                    msg = f"Failed to update job '{job_name}': {e}"
                    self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                    self.execution_errors.append(msg)

        tasks = list(starmap(update_task, jobs.items()))
        await asyncio.gather(*tasks)

    async def _fetch_job_instances(
        self,
        api: AsyncMarketplaceApi,
    ) -> list[SingleJson] | None:
        """Fetch and normalise the list of installed jobs.

        Returns:
            A flat list of job instance dicts, or ``None`` if the fetch fails or the
            response format is unexpected.

        """
        installed_jobs_response: SingleJson = await api.get_installed_jobs()

        if isinstance(installed_jobs_response, dict) and "job_instances" in installed_jobs_response:
            job_instances: list[SingleJson] = installed_jobs_response["job_instances"]
        elif isinstance(installed_jobs_response, list):
            job_instances = installed_jobs_response
        else:
            self.logger.error(
                "Unexpected response format from get_installed_jobs: "
                "expected list or dict with 'job_instances', got "
                f"{type(installed_jobs_response).__name__}."
            )
            return None

        if not job_instances:
            self.logger.warn("No installed jobs found.")
            return None

        return job_instances

    def _build_job_name_lookup(
        self,
        job_instances: list[SingleJson],
    ) -> SingleJson:
        """Build a display-name -> job-dict lookup.

        Args:
            job_instances (list[SingleJson]): Flat list of job dicts.

        Returns:
            SingleJson: Mapping of display name to job dict.

        """
        return build_lookup_with_warnings(
            items=job_instances,
            get_key=lambda j: j.get("displayName") or j.get("name", ""),
            get_value=lambda j: j,
            entity_type="job name",
            logger=self.logger,
        )

    async def _update_single_job(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        param_mapping: SingleJson,
        name_to_job: SingleJson,
    ) -> None:
        """Update parameters for a single job.

        Args:
            api: The async API client.
            job_name (str): The display name of the job.
            param_mapping (SingleJson): Map of param name -> secret ID.
            name_to_job (SingleJson): Lookup of display name -> job dict.

        """
        resolved: tuple[SingleJson, list[SingleJson]] | None = await self._resolve_job_data(
            api,
            job_name,
            name_to_job,
        )
        if resolved is None:
            return

        job_data: SingleJson
        parameters: list[SingleJson]
        job_data, parameters = resolved

        param_index: dict[str, int] = self._build_param_index(parameters)

        updated_count: int = await self._apply_secrets_to_params(
            job_name,
            param_mapping,
            parameters,
            param_index,
        )

        if updated_count == 0:
            self.logger.warn(f"No parameters updated for job '{job_name}' — skipping save.")
            return

        job_data["parameters"] = parameters
        await self._persist_job(api, job_name, job_data, updated_count)

    async def _resolve_job_data(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        name_to_job: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters are available for update.

        If the list response omitted parameters, fetches the full job details.

        Args:
            api: The async API client.
            job_name (str): The display name of the job.
            name_to_job (SingleJson): Lookup of display name -> job dict.

        Returns:
            tuple[SingleJson, list[SingleJson]] | None: A tuple of (job_data, parameters),
                or None if resolution fails.

        """
        job_data: SingleJson | None = name_to_job.get(job_name)
        if job_data is None:
            available: list[str] = list(name_to_job.keys())
            msg = f"Job '{job_name}' not found. Available jobs: {available}."
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
            ) or (None, None)
            if job_data is None:
                return None

        if not isinstance(parameters, list):
            self.logger.error(
                f"Unexpected parameters format for job '{job_name}': "
                f"expected list, got {type(parameters).__name__}."
            )
            return None

        if not parameters:
            self.logger.warn(f"Job '{job_name}' has an empty parameters list — nothing to update.")
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
            job_name (str): Display name (for logging).
            job_data (SingleJson): The partial job dict from the list response.

        Returns:
            tuple[SingleJson, list[SingleJson]] | None: A (job_data, parameters) tuple, or None on failure.

        """
        job_instance_id: str | None = job_data.get("id")
        if job_instance_id is None:
            self.logger.error("Job '%s' has no id and no parameters — cannot update.", job_name)
            return None

        self.logger.info("Fetching full details for job '%s' (id: %s).", job_name, job_instance_id)
        try:
            full_job: SingleJson = await api.get_installed_jobs(
                job_instance_id=job_instance_id,
            )
        except Exception as e:  # ruff:ignore[blind-except]
            self.logger.error(  # ruff:ignore[error-instead-of-exception]
                f"Failed to fetch full details for job '{job_name}' (id: {job_instance_id}): {e}"
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

    def _build_param_index(self, parameters: list[SingleJson]) -> dict[str, int]:
        """Build a parameter-name -> list-index lookup.

        Args:
            parameters (list[SingleJson]): The job's parameter list.

        Returns:
            dict[str, int]: Mapping of param display name to its index in the list.

        """
        indexed_params = list(enumerate(parameters))

        return build_lookup_with_warnings(
            items=indexed_params,
            get_key=lambda item: item[1].get("displayName") or item[1].get("name", ""),
            get_value=operator.itemgetter(0),
            entity_type="job parameter",
            logger=self.logger,
        )

    async def _apply_secrets_to_params(
        self,
        job_name: str,
        param_mapping: SingleJson,
        parameters: list[SingleJson],
        param_index: dict[str, int],
    ) -> int:
        """Fetch secrets and swap values into the parameters list.

        Args:
            job_name (str): Display name (for logging).
            param_mapping (SingleJson): Map of param name -> secret ID.
            parameters (list[SingleJson]): The mutable parameter list.
            param_index (dict[str, int]): Name -> index lookup.

        Returns:
            int: The number of parameters successfully updated.

        """
        async def update_single_param(param_name: str, mapped_value: str) -> bool:
            if param_name not in param_index:
                msg = (
                    f"Parameter '{param_name}' not found on "
                    f"job '{job_name}'. Available parameters: "
                    f"{list(param_index.keys())}."
                )
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
                    mapped_value=mapped_value,
                    update_callback=update_job_param,
                )
            except Exception as e:  # ruff:ignore[blind-except]
                msg = (
                    f"Failed to fetch secret '{mapped_value}' for param "
                    f"'{param_name}' on job '{job_name}': {e}"
                )
                self.logger.error(msg)  # ruff:ignore[error-instead-of-exception]
                self.execution_errors.append(msg)
                return False
            else:
                return True

        tasks = list(starmap(update_single_param, param_mapping.items()))
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
            job_name (str): Display name (for logging).
            job_data (SingleJson): The full job dict with updated parameters.
            updated_count (int): Number of params changed (for logging).

        Raises:
            JobSaveError: If the API call fails.

        """
        try:
            await api.save_or_update_job(job_data=job_data)
            self.logger.info("Saved job '%s' with %s updated parameter(s).", job_name, updated_count)
        except JobSaveError:
            raise
        except Exception as e:
            msg = f"Failed to save job '{job_name}': {e}"
            raise JobSaveError(msg) from e


# Alias for backwards compatibility
SyncIntegrationCredentialJob = SyncIntegrationCredentialsJob


def main() -> None:
    """Run the credential synchronization job."""
    SyncIntegrationCredentialsJob().start()


if __name__ == "__main__":
    main()
