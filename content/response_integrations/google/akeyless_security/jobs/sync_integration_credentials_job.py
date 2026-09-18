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
from itertools import starmap
from operator import itemgetter
from typing import TYPE_CHECKING

import yaml
from TIPCommon.base.job import Job
from TIPCommon.rest.async_soar_platform_clients.secops_soar import AsyncChronicleSOAR
from TIPCommon.rest.async_soar_platform_clients.soar_api_client import (
    AsyncMarketplaceApi,
)

from ..core.constants import (
    ANY_INTEGRATION_FILTER_VALUE,
    ASYNC_SEMAPHORE_LIMIT,
    CONNECTORS_KEY,
    DEFAULT_API_GATEWAY_URL,
    DEFAULT_SECRET_VERSION,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    RESOURCE_NAME_PATTERN,
    SYNC_CREDENTIALS_JOB_SCRIPT_NAME,
    TIMEOUT_THRESHOLD_MS,
    NameIdentifierMap,
    SecretCacheKey,
)
from ..core.datamodels import AkeylessClientConfig
from ..core.exceptions import (
    ConnectivityError,
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
    JobFetchError,
    JobSaveError,
    ParameterUpdateError,
    SecretAccessError,
)
from ..core.manager import AkeylessClient
from ..core.utils import (
    build_lookup_with_warnings,
    extract_integration_parameters,
    mask_id,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class SyncIntegrationCredentialsJob(Job):
    """Syncs credentials from Akeyless Security to SOAR.

    Reads a credential mapping JSON/YAML from job parameters, fetches
    the corresponding secrets from Akeyless Security, and
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
        self.job_name_to_identifier: NameIdentifierMap = {}
        self.job_start_time: int = int(time.time() * 1000)
        self.state_context: dict[str, str] = {}
        self._secret_cache: dict[SecretCacheKey, str] = {}
        self._sync_errors: list[str] = []

    @property
    def execution_errors(self) -> list[str]:
        """Alias for ``_sync_errors`` for backward compatibility."""
        return self._sync_errors

    @execution_errors.setter
    def execution_errors(self, value: list[str]) -> None:
        self._sync_errors = value

    def _init_api_clients(self) -> None:
        """No-op. Async API clients are initialized inside the async event loop."""

    def _has_job_level_parameters(self) -> bool:
        """Check if the job instance has connection parameters in UI configuration.

        Returns:
            bool: True if job level parameters are set, False otherwise.

        """
        return bool(
            getattr(self.params, "access_id", None)
            and getattr(self.params, "access_key", None)
        )

    def _extract_from_job_params(self) -> AkeylessClientConfig:
        """Extract connection parameters directly from the Job UI configuration container.

        Returns:
            AkeylessClientConfig: Extracted parameters.

        """
        api_gateway_url = getattr(self.params, "api_gateway_url", None)
        verify_ssl = getattr(self.params, "verify_ssl", None)
        return AkeylessClientConfig(
            access_id=self.params.access_id,
            access_key=self.params.access_key,
            api_gateway_url=(
                api_gateway_url
                if isinstance(api_gateway_url, str) and api_gateway_url.strip()
                else DEFAULT_API_GATEWAY_URL
            ),
            verify_ssl=verify_ssl if verify_ssl is not None else True,
        )

    def _extract_from_fallback_configuration(self) -> AkeylessClientConfig:
        """Extract parameters from global integration configuration.

        Returns:
            AkeylessClientConfig: Extracted fallback parameters.

        """
        return extract_integration_parameters(self.soar_job)

    def _get_integration_parameters(self) -> AkeylessClientConfig:
        """Extract Akeyless parameters from Job UI or fall back to global configuration.

        Returns:
            AkeylessClientConfig: Connection parameters.

        """
        if self._has_job_level_parameters():
            self.logger.info(
                "Extracting Akeyless Security connection parameters directly from the Job's UI configuration settings."
            )
            return self._extract_from_job_params()

        self.logger.info(
            "Job UI configuration parameters are empty or incomplete. "
            "Falling back to the global Integration Instance configuration..."
        )
        return self._extract_from_fallback_configuration()

    async def _init_akeyless_client(self) -> None:
        """Initialize the Akeyless client and verify connectivity.

        Raises:
            ConnectivityError: If connection or authentication to Akeyless fails.

        """
        config = self._get_integration_parameters()

        self.akeyless_client = await asyncio.to_thread(
            AkeylessClient,
            config,
            logger=self.logger,
        )
        self.logger.info("Testing connectivity to Akeyless Security...")
        try:
            await asyncio.to_thread(self.akeyless_client.test_connectivity)
        except Exception as e:
            msg = f"Failed to connect or authenticate to Akeyless Security: {e}"
            self.logger.exception(msg)
            raise ConnectivityError(msg) from e
        self.logger.info("Successfully connected and authenticated to Akeyless Security.")

    def _validate_params(self) -> None:
        """Validate job parameters before execution.

        Parses and validates the Credential Mapping YAML/JSON
        string provided via the job configuration UI.

        Raises:
            InvalidConfigurationError: If the YAML/JSON string
                is invalid, empty, or if the mapped values are in an invalid format.

        """
        raw_mapping = getattr(self.params, "credential_mapping", None)
        if not raw_mapping or not str(raw_mapping).strip():
            msg = "Credential Mapping cannot be empty."
            raise InvalidConfigurationError(msg)

        try:
            self.credential_mapping = yaml.safe_load(raw_mapping)
        except yaml.YAMLError as e:
            msg = f"Invalid Credential Mapping syntax: {e}"
            raise InvalidConfigurationError(msg) from e

        if not isinstance(self.credential_mapping, dict) or not self.credential_mapping:
            msg = "Credential Mapping must be a non-empty dictionary."
            raise InvalidConfigurationError(msg)

        valid_keys = {INTEGRATION_INSTANCES_KEY, CONNECTORS_KEY, JOBS_KEY}
        invalid_keys = set(self.credential_mapping.keys()) - valid_keys
        if invalid_keys:
            msg = (
                f"Invalid root keys in Credential Mapping: {list(invalid_keys)}. "
                f"Allowed keys are: {list(valid_keys)}."
            )
            raise InvalidConfigurationError(msg)

        total_mappings: int = sum(
            self._validate_param_mappings(category, self.credential_mapping.get(category, {}))
            for category in valid_keys
        )

        if total_mappings == 0:
            msg = (
                "Credential Mapping must contain at least one mapped parameter under "
                f"'{INTEGRATION_INSTANCES_KEY}', '{CONNECTORS_KEY}', or '{JOBS_KEY}'."
            )
            raise InvalidConfigurationError(msg)

    @staticmethod
    def _validate_param_mappings(
        category: str,
        category_mapping: SingleJson,
    ) -> int:
        """Validate component parameter mappings within a category.

        Args:
            category (str): Category name (instances, connectors, or jobs).
            category_mapping (SingleJson): Dictionary of component to param mappings.

        Returns:
            int: Number of valid mapped parameters found.

        Raises:
            InvalidConfigurationError: If any component or parameter format is invalid.

        """
        if not isinstance(category_mapping, dict):
            msg = f"Category '{category}' must be a dictionary."
            raise InvalidConfigurationError(msg)

        mappings_count: int = 0
        for component_name, param_mapping in category_mapping.items():
            if not isinstance(param_mapping, dict):
                msg = f"Parameters for '{component_name}' in category '{category}' must be a dictionary."
                raise InvalidConfigurationError(msg)

            for param_name, mapped_value in param_mapping.items():
                mappings_count += 1
                val = str(mapped_value).strip()
                if not RESOURCE_NAME_PATTERN.match(val):
                    msg = (
                        f"Invalid format for parameter '{param_name}' of '{component_name}' "
                        f"in category '{category}': '{val}'. "
                        f"Expected format: 'secret_name' or 'secret_name:version'."
                    )
                    raise InvalidConfigurationError(msg)

        return mappings_count

    def _perform_job(self) -> None:
        """Fetch secrets and sync to SOAR platform."""
        self.logger.info("Starting 'Sync Integration Credentials Job'.")
        asyncio.run(self._async_main())
        self.logger.info("'Sync Integration Credentials Job' completed.")

    async def _async_main(self) -> None:
        """Execute the main asynchronous flow."""
        await self._init_akeyless_client()
        self.environment_name = getattr(self.params, "environment_name", None) or getattr(
            self, "environment_name", "Default Environment"
        )
        self._load_context()
        async_soar = AsyncChronicleSOAR(self.soar_job)
        try:
            api = AsyncMarketplaceApi(async_soar)
            semaphore = asyncio.Semaphore(ASYNC_SEMAPHORE_LIMIT)
            await self._run_sync_pipeline(api, semaphore)
        finally:
            self._save_context()
            self.logger.info("Closing async client session.")
            await async_soar.close()

    async def _run_sync_pipeline(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Run synchronization tasks across instances, connectors, and jobs."""
        await self._prefetch_all_secrets(semaphore)
        if self._is_approaching_timeout():
            self._check_sync_errors_and_raise()
            return

        await self._sync_integration_instances(api, semaphore)
        if self._is_approaching_timeout():
            self._check_sync_errors_and_raise()
            return

        await self._sync_connectors(api, semaphore)
        if self._is_approaching_timeout():
            self._check_sync_errors_and_raise()
            return

        await self._sync_jobs(api, semaphore)
        self._check_sync_errors_and_raise()

    def _check_sync_errors_and_raise(self) -> None:
        """Raise IntegrationCredentialSyncError if any errors occurred.

        Raises:
            IntegrationCredentialSyncError: If one or more errors occur
                during credential synchronization.

        """
        if self._sync_errors:
            summary: str = "\n".join(f"- {err}" for err in self._sync_errors)
            msg: str = f"Credential synchronization completed with one or more errors:\n{summary}"
            raise IntegrationCredentialSyncError(msg)

    def _load_context(self) -> None:
        """Load job context property from SOAR platform."""
        self.logger.info("Loading job context state...")
        if not hasattr(self, "soar_job") or self.soar_job is None:
            self.state_context = {}
            return

        context_str: str = self.soar_job.get_job_context_property(
            self.name_id,
            "sync_credentials_state",
        )
        if not context_str or not isinstance(context_str, str):
            self.logger.info("No existing sync state found. Starting fresh.")
            self.state_context = {}
            return

        try:
            loaded = yaml.safe_load(context_str)
        except yaml.YAMLError as e:
            self.logger.warn(f"Failed to parse job context: {e}. Starting fresh.")
            self.state_context = {}
            return

        if isinstance(loaded, dict):
            self.state_context = loaded
        else:
            self.logger.warn("Parsed job context is not a dictionary. Starting fresh.")
            self.state_context = {}

    def _save_context(self) -> None:
        """Save job context property back to SOAR platform."""
        self.logger.info("Saving job context state...")
        if not hasattr(self, "soar_job") or self.soar_job is None:
            return

        try:
            self.soar_job.set_job_context_property(
                identifier=self.name_id,
                property_key="sync_credentials_state",
                property_value=json.dumps(self.state_context),
            )
        except Exception:
            self.logger.exception("Failed to save job context state.")

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
            loc
            for loc in locations
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
                    self.logger.debug(f"Failed pre-fetching secret '{secret_loc}': {e}")

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

        Args:
            secret_id (str): The ID/path of the secret in Akeyless.
            version_id (str): The version of the secret to retrieve.
            context_label (str): Context label for logging/errors.

        Returns:
            str: The retrieved secret value.

        Raises:
            SecretAccessError: If fetching the secret from Akeyless fails.

        """
        cache_key = (secret_id, version_id)
        if cache_key in self._secret_cache:
            self.logger.info(
                f"Using cached payload for secret '{mask_id(secret_id)}' (version '{version_id}')."
            )
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
            msg = (
                f"Failed to fetch secret '{mask_id(secret_id)}' "
                f"(version '{version_id}') for {context_label}: {e}"
            )
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
        """Parse the mapped string, defaulting to DEFAULT_SECRET_VERSION if not explicitly provided.

        Args:
            mapped_value (str): The value from the JSON/YAML mapping (e.g., 'secret-id:version').

        Returns:
            tuple[str, str]: The (secret_id, resolved_version).

        Raises:
            InvalidConfigurationError: If the mapped value is in an invalid format.

        """
        mapped_value = str(mapped_value).strip()
        match = RESOURCE_NAME_PATTERN.match(mapped_value)
        if not match:
            msg = (
                f"Invalid credential mapping format for value '{mapped_value}'. "
                f"Expected format: 'secret_name' or 'secret_name:version'."
            )
            raise InvalidConfigurationError(msg)

        gd = match.groupdict()
        secret_id = gd["secret"]
        version_id = gd["version"] or DEFAULT_SECRET_VERSION

        if hasattr(self, "logger") and self.logger is not None:
            self.logger.info(
                f"Resolved mapped value '{mapped_value}' to secret '{mask_id(secret_id)}' "
                f"(version '{version_id}')."
            )
        return secret_id, version_id

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

        env_name = self.environment_name or getattr(self.params, "environment_name", "")
        response = await api.get_installed_integrations_of_environment(
            integration_identifier=ANY_INTEGRATION_FILTER_VALUE,
            environment=env_name,
        )
        instances_list = (
            response
            if isinstance(response, list)
            else (
                response.get("instances", [])
                or response.get("integrationInstances", [])
            )
        )
        if not instances_list:
            msg = (
                f"Either the environment name '{env_name}' is invalid "
                f"or no integration instances are configured in that environment."
            )
            self.logger.error(msg)
            self._sync_errors.append(msg)
            return

        self.instance_name_to_identifier = self._build_instance_name_lookup_from_json(
            instances_list,
        )

        self.logger.info(
            f"Found {len(self.instance_name_to_identifier)} integration instance(s) "
            f"in environment '{env_name}'."
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
                    self.logger.warn(f"Failed to update instance '{name}': {e}")
                    self._sync_errors.append(f"Failed to update instance '{name}'")

        tasks = list(starmap(update_task, instances.items()))
        await asyncio.gather(*tasks)

    def _build_instance_name_lookup_from_json(
        self,
        instances: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a name -> identifier mapping from raw JSON instances.

        Args:
            instances (list[SingleJson]): The list of raw JSON instance data.

        Returns:
            NameIdentifierMap: A dictionary mapping instance display names
                to their identifiers.

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
        self.logger.info(f"Processing integration instance: {name}")

        identifier: str | None = self._resolve_instance_identifier(name)
        if identifier is None:
            self.logger.warn(f"Skipping instance '{name}' — could not resolve identifier.")
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
            env: str = self.environment_name or getattr(self.params, "environment_name", "")
            available: list[str] = list(self.instance_name_to_identifier.keys())
            msg = (
                f"Integration instance '{instance_name}' not found in environment "
                f"'{env}'. Available instances: {available}."
            )
            self.logger.warn(msg)
            self._sync_errors.append(msg)

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

        Raises:
            ParameterUpdateError: If updating a parameter fails.

        """
        for param_name, mapped_value in param_mapping.items():
            context: str = f"param '{param_name}' on instance '{name}' (id: {identifier})"
            secret_id, version_id = self._resolve_secret_and_version(mapped_value)

            state_key: str = f"instance:{identifier}:{param_name}"
            state_val: str = f"{mapped_value}::{version_id}"
            if version_id != DEFAULT_SECRET_VERSION and self.state_context.get(state_key) == state_val:
                self.logger.info(
                    f"Skipping '{param_name}' on instance '{name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' (version '{version_id}')."
                )
                continue

            secret_value: str = await self._fetch_secret_value_pre_resolved(
                secret_id,
                version_id,
                context_label=context,
            )
            try:
                await api.set_configuration_property(
                    integration_instance_identifier=identifier,
                    property_name=param_name,
                    property_value=secret_value,
                )
            except Exception as e:
                msg = f"Failed to set {context}: {e}"
                raise ParameterUpdateError(msg) from e

            self.state_context[state_key] = state_val
            self.logger.info(
                f"Updated '{param_name}' on instance '{name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

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
        cards = (
            response
            if isinstance(response, list)
            else (
                response.get("connectorInstances", [])
                or response.get("items", [])
            )
        )

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
                    self.logger.warn(f"Failed to update connector '{name}': {e}")
                    self._sync_errors.append(f"Failed to update connector '{name}'")

        tasks = list(starmap(update_task, connectors.items()))
        await asyncio.gather(*tasks)

    def _build_connector_name_lookup_from_json(
        self,
        connector_cards: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a display_name -> identifier mapping from raw JSON.

        Args:
            connector_cards (list[SingleJson]): Raw connector card data.

        Returns:
            NameIdentifierMap: A dictionary mapping connector names
                to their identifiers.

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
        self.logger.info(f"Processing connector: {name}")

        identifier: str | None = self._resolve_connector_identifier(name)
        if identifier is None:
            self.logger.warn(f"Skipping connector '{name}' — could not resolve identifier.")
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
            self.logger.warn(msg)
            self._sync_errors.append(msg)

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

        Raises:
            ParameterUpdateError: If updating a parameter fails.

        """
        for param_name, mapped_value in param_mapping.items():
            context: str = f"param '{param_name}' on connector '{name}' (id: {identifier})"
            secret_id, version_id = self._resolve_secret_and_version(mapped_value)

            state_key: str = f"connector:{identifier}:{param_name}"
            state_val: str = f"{mapped_value}::{version_id}"
            if version_id != DEFAULT_SECRET_VERSION and self.state_context.get(state_key) == state_val:
                self.logger.info(
                    f"Skipping '{param_name}' on connector '{name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' (version '{version_id}')."
                )
                continue

            secret_value: str = await self._fetch_secret_value_pre_resolved(
                secret_id,
                version_id,
                context_label=context,
            )
            try:
                await api.set_connector_parameter(
                    connector_instance_identifier=identifier,
                    parameter_name=param_name,
                    parameter_value=secret_value,
                )
            except Exception as e:
                msg = f"Failed to set {context}: {e}"
                raise ParameterUpdateError(msg) from e

            self.state_context[state_key] = state_val
            self.logger.info(
                f"Updated '{param_name}' on connector '{name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

    async def _sync_jobs(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for jobs concurrently.

        Performs a read-modify-write cycle for each job
        listed in the credential mapping.
        """
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})

        if not jobs:
            self.logger.info("No jobs in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(jobs)} job(s)...")

        job_instances: list[SingleJson] | None = await self._fetch_job_instances(api)
        if job_instances is None:
            self._sync_errors.append("Failed to fetch installed jobs from platform.")
            return

        name_to_job: SingleJson = self._build_job_name_lookup(job_instances)

        async def update_task(job_name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    self.logger.info(f"Processing job: {job_name}")
                    await self._update_single_job(
                        api,
                        job_name,
                        param_mapping,
                        name_to_job,
                    )
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.warn(f"Failed to update job '{job_name}': {e}")
                    self._sync_errors.append(f"Failed to update job '{job_name}'")

        tasks = list(starmap(update_task, jobs.items()))
        await asyncio.gather(*tasks)

    async def _fetch_job_instances(
        self,
        api: AsyncMarketplaceApi,
    ) -> list[SingleJson] | None:
        """Fetch and normalize the list of installed jobs.

        Returns:
            A flat list of job instance dicts, or ``None`` if the fetch fails or the
            response format is unexpected.

        """
        installed_jobs_response: SingleJson = await api.get_installed_jobs()

        if isinstance(installed_jobs_response, dict) and (
            "job_instances" in installed_jobs_response
            or "jobInstances" in installed_jobs_response
        ):
            job_instances: list[SingleJson] = (
                installed_jobs_response.get("job_instances")
                or installed_jobs_response.get("jobInstances")
                or []
            )
        elif isinstance(installed_jobs_response, list):
            job_instances = installed_jobs_response
        else:
            self.logger.warn(
                "Unexpected response format from get_installed_jobs: "
                "expected list or dict with 'job_instances'/'jobInstances', got "
                f"{type(installed_jobs_response).__name__}."
            )
            return None

        if not job_instances:
            self.logger.warn("No jobs returned from platform.")
            return []

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
        resolved = await self._resolve_job_data(
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

        pending_state_updates: dict[str, str] = {}
        updated_count: int = await self._apply_secrets_to_params(
            job_name,
            param_mapping,
            parameters,
            param_index,
            pending_state_updates,
        )

        if updated_count == 0:
            self.logger.info(f"No parameters updated for job '{job_name}' — skipping save.")
            return

        job_data["parameters"] = parameters
        await self._persist_job(api, job_name, job_data, updated_count)
        self.state_context.update(pending_state_updates)

    async def _resolve_job_data(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        name_to_job: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters are available for update.

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
            self.logger.warn(msg)
            self._sync_errors.append(msg)
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
            self.logger.warn(
                f"Unexpected parameter format for Job '{job_name}'. "
                f"Expected 'parameters' field to be a list, "
                f"got {type(parameters).__name__}."
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

        Raises:
            JobFetchError: If fetching the job details fails.

        """
        job_instance_id: str | None = job_data.get("id")
        if job_instance_id is None:
            self.logger.warn(f"Job '{job_name}' has no id and no parameters — cannot update.")
            return None

        self.logger.info(f"Fetching full details for job '{job_name}' (id: {job_instance_id}).")
        try:
            full_job: SingleJson = await api.get_installed_jobs(
                job_instance_id=job_instance_id,
            )
        except JobFetchError:
            raise
        except Exception as e:
            msg = f"Failed to fetch details for job '{job_name}' (id: {job_instance_id}): {e}"
            raise JobFetchError(msg) from e

        if not isinstance(full_job, dict):
            self.logger.warn(
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
            get_value=itemgetter(0),
            entity_type="job parameter",
            logger=self.logger,
        )

    async def _apply_secrets_to_params(
        self,
        job_name: str,
        param_mapping: SingleJson,
        parameters: list[SingleJson],
        param_index: dict[str, int],
        pending_state_updates: dict[str, str] | None = None,
    ) -> int:
        """Fetch secrets and swap values into the parameters list.

        Args:
            job_name (str): Display name (for logging).
            param_mapping (SingleJson): Map of param name -> secret ID.
            parameters (list[SingleJson]): The mutable parameter list.
            param_index (dict[str, int]): Name -> index lookup.
            pending_state_updates (dict[str, str] | None): State updates to apply after save.

        Returns:
            int: The number of parameters successfully updated.

        """
        if pending_state_updates is None:
            pending_state_updates = {}

        updated_count: int = 0
        for param_name, mapped_value in param_mapping.items():
            if param_name not in param_index:
                msg = (
                    f"Parameter '{param_name}' not found on "
                    f"job '{job_name}'. Available parameters: "
                    f"{list(param_index.keys())}."
                )
                self.logger.warn(msg)
                self._sync_errors.append(msg)
                continue

            context: str = f"param '{param_name}' on job '{job_name}'"
            secret_id, version_id = self._resolve_secret_and_version(mapped_value)

            state_key: str = f"job:{job_name}:{param_name}"
            state_val: str = f"{mapped_value}::{version_id}"
            if version_id != DEFAULT_SECRET_VERSION and self.state_context.get(state_key) == state_val:
                self.logger.info(
                    f"Skipping '{param_name}' on job '{job_name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' "
                    f"(version '{version_id}')."
                )
                continue

            secret_value: str = await self._fetch_secret_value_pre_resolved(
                secret_id,
                version_id,
                context_label=context,
            )
            idx: int = param_index[param_name]
            parameters[idx]["value"] = secret_value
            updated_count += 1
            pending_state_updates[state_key] = state_val
            self.logger.info(
                f"Set '{param_name}' on job '{job_name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

        return updated_count

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
            JobSaveError: If saving the job data back to the platform fails.

        """
        try:
            await api.save_or_update_job(job_data=job_data)
            self.logger.info(f"Saved job '{job_name}' with {updated_count} updated parameter(s).")
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
