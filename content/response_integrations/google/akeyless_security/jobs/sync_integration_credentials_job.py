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

"""Credential synchronization job for Akeyless Security."""

from __future__ import annotations

import asyncio
import json
import time
from itertools import starmap
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
    SYNC_CREDENTIALS_JOB_SCRIPT_NAME,
    TIMEOUT_THRESHOLD_MS,
    NameIdentifierMap,
    SecretCacheKey,
)
from ..core.datamodels import AkeylessClientConfig, ComponentTarget
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
    resolve_secret_and_version,
    validate_param_mappings,
)

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class SyncIntegrationCredentialsJob(Job):
    """Syncs credentials from Akeyless Security to the SOAR platform."""

    _resolve_secret_and_version = staticmethod(resolve_secret_and_version)

    def __init__(self) -> None:
        """Initialize the credential synchronization job."""
        super().__init__(SYNC_CREDENTIALS_JOB_SCRIPT_NAME)
        self.akeyless_client: AkeylessClient | None = None
        self.credential_mapping: SingleJson = {}
        self.environment_name: str = ""
        self.instance_name_to_identifier: NameIdentifierMap = {}
        self.connector_name_to_identifier: NameIdentifierMap = {}
        self.job_name_to_identifier: NameIdentifierMap = {}
        self.name_to_job: SingleJson = {}
        self.job_start_time: int = int(time.time() * 1000)
        self.state_context: dict[str, str] = {}
        self._secret_cache: dict[SecretCacheKey, str] = {}
        self._sync_errors: list[str] = []

    @property
    def execution_errors(self) -> list[str]:
        """List of synchronization errors."""
        return self._sync_errors

    @execution_errors.setter
    def execution_errors(self, value: list[str]) -> None:
        """Set the list of synchronization errors."""
        self._sync_errors = value

    def _init_api_clients(self) -> None:
        """Skip synchronous client initialization in favor of async setup."""

    def _has_job_level_parameters(self) -> bool:
        """Check whether the job instance has connection parameters in UI configuration.

        Returns:
            True if job-level connection parameters are configured, False otherwise.

        """
        return bool(
            getattr(self.params, "access_id", None)
            and getattr(self.params, "access_key", None)
        )

    def _extract_from_job_params(self) -> AkeylessClientConfig:
        """Extract connection parameters directly from the Job UI configuration.

        Returns:
            Extracted Akeyless client configuration.

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
        """Extract parameters from the global integration configuration.

        Returns:
            Extracted fallback Akeyless client configuration.

        """
        return extract_integration_parameters(self.soar_job)

    def _get_integration_parameters(self) -> AkeylessClientConfig:
        """Extract Akeyless parameters from Job UI or fall back to global configuration.

        Returns:
            Resolved Akeyless client configuration.

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
            raise ConnectivityError(msg) from e
        self.logger.info("Successfully connected and authenticated to Akeyless Security.")

    def _validate_params(self) -> None:
        """Validate job parameters before execution.

        Raises:
            InvalidConfigurationError: If the YAML/JSON mapping is invalid or empty.

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
            validate_param_mappings(category, self.credential_mapping.get(category, {}))
            for category in valid_keys
        )
        if total_mappings == 0:
            msg = (
                "Credential Mapping must contain at least one mapped parameter under "
                f"'{INTEGRATION_INSTANCES_KEY}', '{CONNECTORS_KEY}', or '{JOBS_KEY}'."
            )
            raise InvalidConfigurationError(msg)

    def _perform_job(self) -> None:
        """Fetch secrets and sync them to the SOAR platform."""
        self.logger.info("Starting 'Sync Integration Credentials Job'.")
        asyncio.run(self._async_main())
        self.logger.info("'Sync Integration Credentials Job' completed.")

    async def _async_main(self) -> None:
        """Execute the main asynchronous synchronization workflow."""
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

    async def _run_sync_pipeline(self, api: AsyncMarketplaceApi, semaphore: asyncio.Semaphore) -> None:
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
        """Raise IntegrationCredentialSyncError if any synchronization errors occurred.

        Raises:
            IntegrationCredentialSyncError: If one or more errors occurred during sync.

        """
        if self._sync_errors:
            summary: str = "\n".join(f"- {err}" for err in self._sync_errors)
            msg: str = f"Credential synchronization completed with one or more errors:\n{summary}"
            raise IntegrationCredentialSyncError(msg)

    def _load_context(self) -> None:
        """Load job context state from the SOAR platform."""
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
        """Save job context state back to the SOAR platform."""
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

    async def _prefetch_all_secrets(self, semaphore: asyncio.Semaphore) -> None:
        """Extract unique secret locations from credential_mapping and pre-fetch concurrently."""
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
            if resolve_secret_and_version(loc) not in self._secret_cache
        ]
        if not uncached_locations:
            return

        async def fetch_one(secret_loc: str) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    secret_id, version_id = resolve_secret_and_version(secret_loc)
                    await self._fetch_secret_value_pre_resolved(
                        secret_id,
                        version_id,
                        context_label=f"pre-fetch '{secret_loc}'",
                    )
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.debug(f"Failed pre-fetching secret '{secret_loc}': {e}")

        await asyncio.gather(*(fetch_one(loc) for loc in uncached_locations))

    async def _fetch_secret_value_pre_resolved(
        self,
        secret_id: str,
        version_id: str,
        *,
        context_label: str,
    ) -> str:
        """Fetch the secret value for a pre-resolved secret and version.

        Returns:
            The retrieved secret value.

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
        """Check whether the job execution is approaching the timeout threshold.

        Returns:
            True if the execution time has exceeded the timeout threshold, False otherwise.

        """
        if not self.job_start_time:
            return False

        if int(time.time() * 1000) - self.job_start_time > TIMEOUT_THRESHOLD_MS:
            self.logger.info("Timeout approaching. Stopping execution gracefully.")
            return True

        return False

    async def _fetch_environment_instances(self, api: AsyncMarketplaceApi) -> list[SingleJson]:
        """Fetch and normalize installed integration instances for the target environment.

        Returns:
            List of integration instance dictionaries for the configured environment.

        """
        env_name = self.environment_name or getattr(self.params, "environment_name", "")
        response = await api.get_installed_integrations_of_environment(
            integration_identifier=ANY_INTEGRATION_FILTER_VALUE,
            environment=env_name,
        )
        if isinstance(response, list):
            return response

        return response.get("instances", []) or response.get("integrationInstances", [])

    async def _sync_integration_instances(
        self,
        api: AsyncMarketplaceApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for integration instances concurrently."""
        instances: SingleJson = self.credential_mapping.get(INTEGRATION_INSTANCES_KEY, {})
        if not instances:
            self.logger.info("No integration instances in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(instances)} integration instance(s)...")
        env_name = self.environment_name or getattr(self.params, "environment_name", "")
        instances_list = await self._fetch_environment_instances(api)
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
                    await self._update_single_integration_instance(api, name, param_mapping)
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.warn(f"Failed to update instance '{name}': {e}")
                    self._sync_errors.append(f"Failed to update instance '{name}'")

        await asyncio.gather(*starmap(update_task, instances.items()))

    def _build_instance_name_lookup_from_json(
        self,
        instances: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a display-name to identifier mapping from raw JSON instances.

        Returns:
            Dictionary mapping integration instance display names to identifiers.

        """
        return build_lookup_with_warnings(
            items=instances,
            extract_pair=lambda i: (
                i.get("displayName") or i.get("instanceName", ""),
                i.get("identifier", ""),
            ),
            logger=self.logger,
        )

    async def _update_single_integration_instance(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single integration instance."""
        self.logger.info(f"Processing integration instance: {name}")
        identifier: str | None = self._resolve_instance_identifier(name)
        if identifier is None:
            self.logger.warn(f"Skipping instance '{name}' — could not resolve identifier.")
            return

        target = ComponentTarget(name=name, identifier=identifier)
        await self._set_integration_params(api, target, param_mapping)

    def _resolve_instance_identifier(self, instance_name: str) -> str | None:
        """Resolve an integration instance display name to its identifier.

        Returns:
            The resolved instance identifier, or None if not found.

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

    def _is_secret_state_up_to_date(self, state_key: str, mapped_value: str, version_id: str) -> bool:
        """Check whether a pinned secret version is already recorded in state_context.

        Returns:
            True if the parameter already matches the pinned secret version, False otherwise.

        """
        state_val: str = f"{mapped_value}::{version_id}"

        return (
            version_id != DEFAULT_SECRET_VERSION
            and self.state_context.get(state_key) == state_val
        )

    async def _set_integration_params(
        self,
        api: AsyncMarketplaceApi,
        target: ComponentTarget,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on an integration instance.

        Raises:
            ParameterUpdateError: If updating a parameter fails.

        """
        for param_name, mapped_value in param_mapping.items():
            context = f"param '{param_name}' on instance '{target.name}' (id: {target.identifier})"
            secret_id, version_id = resolve_secret_and_version(mapped_value)
            state_key = f"instance:{target.identifier}:{param_name}"
            if self._is_secret_state_up_to_date(state_key, mapped_value, version_id):
                self.logger.info(
                    f"Skipping '{param_name}' on instance '{target.name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' (version '{version_id}')."
                )
                continue

            secret_value = await self._fetch_secret_value_pre_resolved(
                secret_id, version_id, context_label=context
            )
            try:
                await api.set_configuration_property(
                    integration_instance_identifier=target.identifier,
                    property_name=param_name,
                    property_value=secret_value,
                )
            except Exception as e:
                msg = f"Failed to set {context}: {e}"
                raise ParameterUpdateError(msg) from e

            self.state_context[state_key] = f"{mapped_value}::{version_id}"
            self.logger.info(
                f"Updated '{param_name}' on instance '{target.name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

    async def _sync_connectors(self, api: AsyncMarketplaceApi, semaphore: asyncio.Semaphore) -> None:
        """Sync credentials for connectors concurrently."""
        connectors: SingleJson = self.credential_mapping.get(CONNECTORS_KEY, {})
        if not connectors:
            self.logger.info("No connectors in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(connectors)} connector(s)...")
        response = await api.get_connector_cards(integration_name=ANY_INTEGRATION_FILTER_VALUE)
        cards = (
            response
            if isinstance(response, list)
            else (response.get("connectorInstances", []) or response.get("items", []))
        )
        self.connector_name_to_identifier = self._build_connector_name_lookup_from_json(cards)
        self.logger.info(f"Found {len(self.connector_name_to_identifier)} connector(s).")

        async def update_task(name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._update_single_connector(api, name, param_mapping)
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.warn(f"Failed to update connector '{name}': {e}")
                    self._sync_errors.append(f"Failed to update connector '{name}'")

        await asyncio.gather(*starmap(update_task, connectors.items()))

    def _build_connector_name_lookup_from_json(
        self,
        connector_cards: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a display-name to identifier mapping from raw connector cards.

        Returns:
            Dictionary mapping connector display names to identifiers.

        """
        return build_lookup_with_warnings(
            items=connector_cards,
            extract_pair=lambda c: (c.get("displayName", ""), c.get("identifier", "")),
            logger=self.logger,
        )

    async def _update_single_connector(
        self,
        api: AsyncMarketplaceApi,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single connector."""
        self.logger.info(f"Processing connector: {name}")
        identifier: str | None = self._resolve_connector_identifier(name)
        if identifier is None:
            self.logger.warn(f"Skipping connector '{name}' — could not resolve identifier.")
            return

        target = ComponentTarget(name=name, identifier=identifier)
        await self._set_connector_params(api, target, param_mapping)

    def _resolve_connector_identifier(self, connector_name: str) -> str | None:
        """Resolve a connector display name to its identifier.

        Returns:
            The resolved connector identifier, or None if not found.

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
        target: ComponentTarget,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on a connector instance.

        Raises:
            ParameterUpdateError: If updating a parameter fails.

        """
        for param_name, mapped_value in param_mapping.items():
            context = f"param '{param_name}' on connector '{target.name}' (id: {target.identifier})"
            secret_id, version_id = resolve_secret_and_version(mapped_value)
            state_key = f"connector:{target.identifier}:{param_name}"
            if self._is_secret_state_up_to_date(state_key, mapped_value, version_id):
                self.logger.info(
                    f"Skipping '{param_name}' on connector '{target.name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' (version '{version_id}')."
                )
                continue

            secret_value = await self._fetch_secret_value_pre_resolved(
                secret_id, version_id, context_label=context
            )
            try:
                await api.set_connector_parameter(
                    connector_instance_identifier=target.identifier,
                    parameter_name=param_name,
                    parameter_value=secret_value,
                )
            except Exception as e:
                msg = f"Failed to set {context}: {e}"
                raise ParameterUpdateError(msg) from e

            self.state_context[state_key] = f"{mapped_value}::{version_id}"
            self.logger.info(
                f"Updated '{param_name}' on connector '{target.name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

    async def _sync_jobs(self, api: AsyncMarketplaceApi, semaphore: asyncio.Semaphore) -> None:
        """Sync credentials for jobs concurrently."""
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})
        if not jobs:
            self.logger.info("No jobs in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(jobs)} job(s)...")
        job_instances: list[SingleJson] | None = await self._fetch_job_instances(api)
        if job_instances is None:
            self._sync_errors.append("Failed to fetch installed jobs from platform.")
            return

        self.name_to_job = self._build_job_name_lookup(job_instances)

        async def update_task(job_name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    self.logger.info(f"Processing job: {job_name}")
                    await self._update_single_job(api, job_name, param_mapping)
                except Exception as e:  # ruff:ignore[blind-except]
                    self.logger.warn(f"Failed to update job '{job_name}': {e}")
                    self._sync_errors.append(f"Failed to update job '{job_name}'")

        await asyncio.gather(*starmap(update_task, jobs.items()))

    async def _fetch_job_instances(self, api: AsyncMarketplaceApi) -> list[SingleJson] | None:
        """Fetch and normalize the list of installed jobs.

        Returns:
            List of job instance dictionaries, or None if the response format is invalid.

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

    def _build_job_name_lookup(self, job_instances: list[SingleJson]) -> SingleJson:
        """Build a display-name to job-dict lookup.

        Returns:
            Dictionary mapping job display names to job dictionaries.

        """
        return build_lookup_with_warnings(
            items=job_instances,
            extract_pair=lambda j: (j.get("displayName") or j.get("name", ""), j),
            logger=self.logger,
        )

    async def _update_single_job(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Update parameters for a single job."""
        resolved = await self._resolve_job_data(api, job_name)
        if resolved is None:
            return

        job_data, parameters = resolved
        pending_state_updates = await self._apply_secrets_to_params(
            job_name, param_mapping, parameters
        )
        if not pending_state_updates:
            self.logger.info(f"No parameters updated for job '{job_name}' — skipping save.")
            return

        job_data["parameters"] = parameters
        await self._persist_job(api, job_name, job_data)
        self.state_context.update(pending_state_updates)

    async def _resolve_job_data(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters list is available for update.

        Returns:
            Tuple of (job_data, parameters), or None if resolution fails.

        """
        job_data: SingleJson | None = self.name_to_job.get(job_name)
        if job_data is None:
            available: list[str] = list(self.name_to_job.keys())
            msg = f"Job '{job_name}' not found. Available jobs: {available}."
            self.logger.warn(msg)
            self._sync_errors.append(msg)
            return None

        job_data = dict(job_data)
        parameters: list[SingleJson] | None = job_data.get("parameters")
        if parameters is None:
            job_data, parameters = await self._fetch_full_job_details(
                api, job_name, job_data
            ) or (None, None)
            if job_data is None:
                return None

        if not isinstance(parameters, list):
            self.logger.warn(
                f"Unexpected parameter format for Job '{job_name}'. "
                f"Expected 'parameters' field to be a list, got {type(parameters).__name__}."
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

        Returns:
            Tuple of (full_job_data, parameters), or None on invalid format.

        Raises:
            JobFetchError: If fetching the job details fails.

        """
        job_instance_id: str | None = job_data.get("id")
        if job_instance_id is None:
            self.logger.warn(f"Job '{job_name}' has no id and no parameters — cannot update.")
            return None

        self.logger.info(f"Fetching full details for job '{job_name}' (id: {job_instance_id}).")
        try:
            full_job: SingleJson = await api.get_installed_jobs(job_instance_id=job_instance_id)
        except JobFetchError:
            raise
        except Exception as e:
            msg = f"Failed to fetch details for job '{job_name}' (id: {job_instance_id}): {e}"
            raise JobFetchError(msg) from e

        if not isinstance(full_job, dict):
            self.logger.warn(
                f"Unexpected response format when fetching job details for "
                f"'{job_name}': expected dict, got {type(full_job).__name__}."
            )
            return None

        return full_job, full_job.get("parameters", [])

    def _build_param_index(self, parameters: list[SingleJson]) -> dict[str, int]:
        """Build a parameter display-name to list-index lookup.

        Returns:
            Dictionary mapping parameter display names to their list indices.

        """
        return build_lookup_with_warnings(
            items=list(enumerate(parameters)),
            extract_pair=lambda item: (
                item[1].get("displayName") or item[1].get("name", ""),
                item[0],
            ),
            logger=self.logger,
        )

    async def _apply_secrets_to_params(
        self,
        job_name: str,
        param_mapping: SingleJson,
        parameters: list[SingleJson],
    ) -> dict[str, str]:
        """Fetch secrets and apply updated values to the job's parameters list.

        Returns:
            Dictionary of pending state updates for parameters that were modified.

        """
        param_index: dict[str, int] = self._build_param_index(parameters)
        pending_state_updates: dict[str, str] = {}

        for param_name, mapped_value in param_mapping.items():
            if param_name not in param_index:
                msg = (
                    f"Parameter '{param_name}' not found on job '{job_name}'. "
                    f"Available parameters: {list(param_index.keys())}."
                )
                self.logger.warn(msg)
                self._sync_errors.append(msg)
                continue

            secret_id, version_id = resolve_secret_and_version(mapped_value)
            state_key: str = f"job:{job_name}:{param_name}"
            if self._is_secret_state_up_to_date(state_key, mapped_value, version_id):
                self.logger.info(
                    f"Skipping '{param_name}' on job '{job_name}' — "
                    f"already up-to-date with secret '{mask_id(secret_id)}' (version '{version_id}')."
                )
                continue

            secret_value: str = await self._fetch_secret_value_pre_resolved(
                secret_id, version_id, context_label=f"param '{param_name}' on job '{job_name}'"
            )
            parameters[param_index[param_name]]["value"] = secret_value
            pending_state_updates[state_key] = f"{mapped_value}::{version_id}"
            self.logger.info(
                f"Set '{param_name}' on job '{job_name}' "
                f"from secret '{mask_id(secret_id)}' (version '{version_id}')."
            )

        return pending_state_updates

    async def _persist_job(
        self,
        api: AsyncMarketplaceApi,
        job_name: str,
        job_data: SingleJson,
    ) -> None:
        """Save the modified job back to the platform.

        Raises:
            JobSaveError: If saving the job data back to the platform fails.

        """
        try:
            await api.save_or_update_job(job_data=job_data)
            self.logger.info(f"Saved job '{job_name}'.")
        except JobSaveError:
            raise
        except Exception as e:
            msg = f"Failed to save job '{job_name}': {e}"
            raise JobSaveError(msg) from e


SyncIntegrationCredentialJob = SyncIntegrationCredentialsJob


def main() -> None:
    """Run the credential synchronization job."""
    SyncIntegrationCredentialsJob().start()


if __name__ == "__main__":
    main()
