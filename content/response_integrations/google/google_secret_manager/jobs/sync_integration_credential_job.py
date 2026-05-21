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
import time
from typing import TYPE_CHECKING

import yaml

from TIPCommon.base.job import Job
from TIPCommon.rest.async_soar_platform_clients.async_credential_sync_api import (
    AsyncCredentialSyncApi,
)
from TIPCommon.rest.async_soar_platform_clients.secops_soar import AsyncChronicleSOAR

from ..core.auth import IntegrationParameters, build_auth_params
from ..core.manager import GoogleSecretManagerClient
from ..core.constants import (
    ANY_INTEGRATION_FILTER_VALUE,
    ASYNC_SEMAPHORE_LIMIT,
    CONNECTORS_KEY,
    DEFAULT_SECRET_VERSION,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    SYNC_CREDENTIAL_JOB_SCRIPT_NAME,
    TIMEOUT_THRESHOLD_MS,
)
from ..core.exceptions import (
    InvalidConfigurationError,
    JobFetchError,
    JobSaveError,
    ParameterUpdateError,
    SecretAccessError,
)
from ..core.utils import build_lookup_with_warnings, mask_id

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

NameIdentifierMap = dict[str, str]


class SyncIntegrationCredentialJob(Job):
    """Syncs credentials from GCP Secret Manager to SOAR.

    Reads a credential mapping JSON from job parameters, fetches
    the corresponding secrets from Google Secret Manager, and
    uses the SOAR SDK to set configuration properties on
    integration instances, connectors, and jobs.
    """

    def __init__(self) -> None:
        super().__init__(SYNC_CREDENTIAL_JOB_SCRIPT_NAME)
        self.secret_manager_client: GoogleSecretManagerClient | None = None
        self.credential_mapping: SingleJson = {}
        self.instance_name_to_identifier: NameIdentifierMap = {}
        self.connector_name_to_identifier: NameIdentifierMap = {}
        self.job_start_time: int = int(time.time() * 1000)

    def _init_api_clients(self) -> None:
        """No-op. Async API clients are initialized inside the async event loop."""

    def _init_secret_manager_client(self) -> None:
        """Initialize the Google Secret Manager client."""
        auth_params: IntegrationParameters = build_auth_params(self.soar_job)

        self.secret_manager_client = GoogleSecretManagerClient(
            service_account_json=auth_params.service_account_json,
            project_id=auth_params.project_id,
            workload_identity_email=auth_params.workload_identity_email,
        )

    def _validate_params(self) -> None:
        """Validate job parameters before execution.

        Parses and validates the Credential Mapping YAML/JSON
        string provided via the job configuration UI.

        Raises:
            InvalidConfigurationError: If the YAML/JSON string
                is invalid.

        """
        try:
            self.credential_mapping = yaml.safe_load(self.params.credential_mapping) or {}
        except yaml.YAMLError as e:
            raise InvalidConfigurationError(f"Invalid Credential Mapping syntax: {e}") from e

    def _perform_job(self) -> None:
        """Fetch secrets and sync to SOAR platform."""
        self.logger.info("Starting 'Sync Integration Credential Job'.")
        asyncio.run(self._async_main())
        self.logger.info("'Sync Integration Credential Job' completed.")

    async def _async_main(self) -> None:
        """Main async execution."""
        self._init_secret_manager_client()
        async_soar = AsyncChronicleSOAR(self.soar_job)
        try:
            api = AsyncCredentialSyncApi(async_soar)
            semaphore = asyncio.Semaphore(ASYNC_SEMAPHORE_LIMIT)

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

    def _is_approaching_timeout(self) -> bool:
        """Check if the job is approaching its timeout."""
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
        mapped_value = str(mapped_value)
        if ":" in mapped_value:
            secret_id: str
            explicit_version: str
            secret_id, explicit_version = mapped_value.split(":", 1)
            self.logger.info(
                f"Secret '{mask_id(secret_id)}': Using explicit version '{explicit_version}'."
            )

            return secret_id, explicit_version

        secret_id: str = mapped_value
        if self.secret_manager_client:
            resolved_version: str = self.secret_manager_client.resolve_latest_enabled_version(
                secret_id,
            )
        else:
            resolved_version = DEFAULT_SECRET_VERSION

        masked: str = mask_id(secret_id)
        if resolved_version == DEFAULT_SECRET_VERSION:
            self.logger.info(
                f"Secret '{masked}': No active versions. "
                f"Falling back to '{DEFAULT_SECRET_VERSION}'."
            )
        else:
            self.logger.info(
                f"Secret '{masked}': Resolved to latest enabled version '{resolved_version}'."
            )

        return secret_id, resolved_version

    async def _fetch_secret_value(
        self,
        mapped_value: str,
        *,
        context_label: str,
    ) -> tuple[str, str, str]:
        """Resolve a mapping entry and fetch the secret value.

        This is the shared logic used by integration instances,
        connectors, and jobs to resolve a secret reference,
        fetch the payload, and return all three pieces needed
        by the caller.

        The synchronous gRPC call to Google Secret Manager is
        wrapped with ``asyncio.to_thread`` to avoid blocking
        the event loop.

        Args:
            mapped_value: Raw mapping value (e.g. ``"my-secret"``
                or ``"my-secret:3"``).
            context_label: Human-readable label for error messages
                (e.g. ``"param 'API Key' on instance 'Foo'"``).

        Returns:
            Tuple of ``(secret_id, version_id, secret_value)``.

        Raises:
            SecretAccessError: If the secret cannot be fetched.

        """
        secret_id: str
        version_id: str
        secret_id, version_id = self._resolve_secret_and_version(
            mapped_value,
        )
        try:
            secret_value: str = await asyncio.to_thread(
                self.secret_manager_client.get_secret_value,
                secret_id=secret_id,
                version_id=version_id,
            )
        except SecretAccessError:
            raise
        except Exception as e:
            raise SecretAccessError(
                f"Failed to fetch secret '{mask_id(secret_id)}' for {context_label}: {e}"
            ) from e

        return secret_id, version_id, secret_value

    async def _sync_integration_instances(
        self,
        api: AsyncCredentialSyncApi,
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

        response = await api.get_installed_integrations_of_environment(
            integration_identifier=ANY_INTEGRATION_FILTER_VALUE,
            environment=self.params.environment_name,
        )
        instances_list = response.get("instances", []) or response.get(
            "integrationInstances", [],
        )
        if not instances_list:
            self.logger.info("No integration instances found in environment. Skipping.")
            return

        self.instance_name_to_identifier = self._build_instance_name_lookup_from_json(
            instances_list,
        )

        self.logger.info(
            f"Found {len(self.instance_name_to_identifier)} integration instance(s) "
            f"in environment '{self.params.environment_name}'."
        )

        async def update_task(name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    await self._update_single_integration_instance(
                        api, name, param_mapping,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update instance '{name}': {e}",
                    )

        tasks = [update_task(name, pm) for name, pm in instances.items()]
        await asyncio.gather(*tasks)

    def _build_instance_name_lookup_from_json(
        self,
        instances: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a name → identifier mapping from raw JSON instances."""
        return build_lookup_with_warnings(
            items=instances,
            get_key=lambda i: i.get("displayName") or i.get("instanceName", ""),
            get_value=lambda i: i.get("identifier", ""),
            entity_type="instance name",
            logger=self.logger,
        )

    async def _update_single_integration_instance(
        self,
        api: AsyncCredentialSyncApi,
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
            self.logger.error(f"Skipping instance '{name}' — could not resolve identifier.")
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
            The identifier string, or None if not found.

        """
        identifier: str | None = self.instance_name_to_identifier.get(instance_name)

        if identifier is None:
            env: str = self.params.environment_name
            available: list[str] = list(self.instance_name_to_identifier.keys())
            self.logger.error(
                f"Integration instance '{instance_name}' not found in environment "
                f"'{env}'. Available instances: {available}."
            )

        return identifier

    async def _set_integration_params(
        self,
        api: AsyncCredentialSyncApi,
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
        for param_name, mapped_value in param_mapping.items():
            context: str = f"param '{param_name}' on instance '{name}' (id: {identifier})"
            secret_id, version_id, secret_value = await self._fetch_secret_value(
                mapped_value,
                context_label=context,
            )
            try:
                await api.set_configuration_property(
                    integration_instance_identifier=identifier,
                    property_name=param_name,
                    property_value=secret_value,
                )
            except Exception as e:
                raise ParameterUpdateError(f"Failed to set {context}: {e}") from e

            self.logger.info(
                f"Updated '{param_name}' on instance '{name}'"
                f" from secret '{mask_id(secret_id)}'"
                f" (version '{version_id}')."
            )

    async def _sync_connectors(
        self,
        api: AsyncCredentialSyncApi,
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
        cards = response.get("connectorInstances", [])
        if not cards:
            self.logger.info("No connectors configured. Skipping.")
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
                        api, name, param_mapping,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update connector '{name}': {e}",
                    )

        tasks = [update_task(name, pm) for name, pm in connectors.items()]
        await asyncio.gather(*tasks)

    def _build_connector_name_lookup_from_json(
        self,
        connector_cards: list[SingleJson],
    ) -> NameIdentifierMap:
        """Build a display_name → identifier mapping from raw JSON."""
        return build_lookup_with_warnings(
            items=connector_cards,
            get_key=lambda c: c.get("displayName", ""),
            get_value=lambda c: c.get("identifier", ""),
            entity_type="connector name",
            logger=self.logger,
        )

    async def _update_single_connector(
        self,
        api: AsyncCredentialSyncApi,
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
            self.logger.error(f"Skipping connector '{name}' — could not resolve identifier.")
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
            The identifier string, or None if not found.

        """
        identifier: str | None = self.connector_name_to_identifier.get(connector_name)
        if identifier is None:
            available: list[str] = list(self.connector_name_to_identifier.keys())
            self.logger.error(
                f"Connector '{connector_name}' not found. Available connectors: {available}."
            )

        return identifier

    async def _set_connector_params(
        self,
        api: AsyncCredentialSyncApi,
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
        for param_name, mapped_value in param_mapping.items():
            context: str = f"param '{param_name}' on connector '{name}' (id: {identifier})"
            secret_id, version_id, secret_value = await self._fetch_secret_value(
                mapped_value,
                context_label=context,
            )
            try:
                await api.set_connector_parameter(
                    connector_instance_identifier=identifier,
                    parameter_name=param_name,
                    parameter_value=secret_value,
                )
            except Exception as e:
                raise ParameterUpdateError(f"Failed to set {context}: {e}") from e

            self.logger.info(
                f"Updated '{param_name}' on connector '{name}'"
                f" from secret '{mask_id(secret_id)}'"
                f" (version '{version_id}')."
            )

    async def _sync_jobs(
        self,
        api: AsyncCredentialSyncApi,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Sync credentials for jobs concurrently.

        Performs a read-modify-write cycle for each job
        listed in the credential mapping.
        """
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})

        if not jobs:
            self.logger.info("No jobs in credential mapping.")
            return

        self.logger.info(f"Processing {len(jobs)} job(s)...")

        job_instances: list[SingleJson] | None = await self._fetch_job_instances(api)
        if job_instances is None:
            return

        name_to_job: SingleJson = self._build_job_name_lookup(job_instances)

        async def update_task(job_name: str, param_mapping: SingleJson) -> None:
            if self._is_approaching_timeout():
                return
            async with semaphore:
                try:
                    self.logger.info(f"Processing job: {job_name}")
                    await self._update_single_job(
                        api, job_name, param_mapping, name_to_job,
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to update job '{job_name}': {e}",
                    )

        tasks = [update_task(name, pm) for name, pm in jobs.items()]
        await asyncio.gather(*tasks)

    async def _fetch_job_instances(
        self,
        api: AsyncCredentialSyncApi,
    ) -> list[SingleJson] | None:
        """Fetch and normalise the list of installed jobs.

        Returns:
            A flat list of job instance dicts, or ``None`` if the fetch fails or the
            response format is unexpected.

        """
        installed_jobs_response: SingleJson = await api.get_installed_jobs()

        # 1P wraps in {"job_instances": [...]}.
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
            self.logger.warn("No jobs returned from platform.")
            return None

        return job_instances

    def _build_job_name_lookup(
        self,
        job_instances: list[SingleJson],
    ) -> SingleJson:
        """Build a display-name → job-dict lookup.

        1P uses ``displayName``; Legacy uses ``name``.

        Args:
            job_instances (list[SingleJson]): Flat list of job dicts.

        Returns:
            Mapping of display name to job dict.

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
        api: AsyncCredentialSyncApi,
        job_name: str,
        param_mapping: SingleJson,
        name_to_job: SingleJson,
    ) -> None:
        """Update parameters for a single job.

        Args:
            api: The async API client.
            job_name (str): The display name of the job.
            param_mapping (SingleJson): Map of param name → secret ID.
            name_to_job (SingleJson): Lookup of display name → job dict.

        """
        resolved: tuple[SingleJson, list[SingleJson]] | None = await self._resolve_job_data(
            api, job_name, name_to_job,
        )
        if resolved is None:
            return

        job_data: SingleJson
        parameters: list[SingleJson]
        job_data, parameters = resolved

        param_index: SingleJson = self._build_param_index(parameters)

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
        api: AsyncCredentialSyncApi,
        job_name: str,
        name_to_job: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters are available for update.

        If the list response omitted parameters, fetches the full job details.

        Args:
            api: The async API client.
            job_name (str): The display name of the job.
            name_to_job (SingleJson): Lookup of display name → job dict.

        Returns:
            A ``(job_data, parameters)`` tuple, or ``None`` if the job cannot be resolved.

        """
        job_data: SingleJson | None = name_to_job.get(job_name)
        if job_data is None:
            available: list[str] = list(name_to_job.keys())
            self.logger.error(f"Job '{job_name}' not found. Available jobs: {available}.")
            return None

        # Shallow copy to avoid mutating the original dict in the lookup.
        job_data = dict(job_data)

        parameters: list[SingleJson] | None = job_data.get("parameters")
        if parameters is None:
            job_data, parameters = await self._fetch_full_job_details(
                api, job_name, job_data,
            ) or (None, None)
            if job_data is None:
                return None

        if not isinstance(parameters, list):
            self.logger.error(
                f"Unexpected parameter format for Job '{job_name}'. "
                f"Expected   'parameters' field to be a list, "
                f"got {type(parameters).__name__}."
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
        api: AsyncCredentialSyncApi,
        job_name: str,
        job_data: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Fetch full job details when the list response omits parameters.

        Args:
            api: The async API client.
            job_name (str): Display name (for logging).
            job_data (SingleJson): The partial job dict from the list response.

        Returns:
            A (job_data, parameters) tuple, or None on failure.

        """
        job_instance_id: str | None = job_data.get("id")
        if job_instance_id is None:
            self.logger.error(f"Job '{job_name}' has no id and no parameters — cannot update.")
            return None

        self.logger.info(f"Fetching full details for job '{job_name}' (id: {job_instance_id}).")
        try:
            full_job: SingleJson = await api.get_installed_jobs(
                job_instance_id=job_instance_id,
            )
        except JobFetchError:
            raise
        except Exception as e:
            raise JobFetchError(
                f"Failed to fetch details for job '{job_name}' (id: {job_instance_id}): {e}"
            ) from e

        if not isinstance(full_job, dict):
            self.logger.error(
                f"Unexpected response format when fetching job details for "
                f"'{job_name}': expected dict, got "
                f"{type(full_job).__name__}."
            )
            return None

        return full_job, full_job.get("parameters", [])

    def _build_param_index(self, parameters: list[SingleJson]) -> dict[str, int]:
        """Build a parameter-name → list-index lookup.

        1P params use ``displayName``; Legacy use ``name``.

        Args:
            parameters (list[SingleJson]): The job's parameter list.

        Returns:
            Mapping of param display name to its index in the list.

        """
        # Since we need to keep track of the index, we zip the items with their index
        # before passing to the generic lookup builder
        indexed_params = list(enumerate(parameters))

        return build_lookup_with_warnings(
            items=indexed_params,
            get_key=lambda item: item[1].get("displayName") or item[1].get("name", ""),
            get_value=lambda item: item[0],
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
            param_mapping (SingleJson): Map of param name → secret ID.
            parameters (list[SingleJson]): The mutable parameter list.
            param_index (dict[str, int]): Name → index lookup.

        Returns:
            The number of parameters successfully updated.

        """
        updated_count: int = 0
        for param_name, mapped_value in param_mapping.items():
            if param_name not in param_index:
                self.logger.error(
                    f"Parameter '{param_name}' not found on "
                    f"job '{job_name}'. Available parameters: "
                    f"{list(param_index.keys())}."
                )
                continue

            context: str = f"param '{param_name}' on job '{job_name}'"
            secret_id, version_id, secret_value = await self._fetch_secret_value(
                mapped_value,
                context_label=context,
            )
            idx: int = param_index[param_name]
            parameters[idx]["value"] = secret_value
            updated_count += 1
            self.logger.info(
                f"Set '{param_name}' on job '{job_name}'"
                f" from secret '{mask_id(secret_id)}'"
                f" (version '{version_id}')."
            )

        return updated_count

    async def _persist_job(
        self,
        api: AsyncCredentialSyncApi,
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

        """
        try:
            await api.save_or_update_job(job_data=job_data)
            self.logger.info(f"Saved job '{job_name}' with {updated_count} updated parameter(s).")
        except JobSaveError:
            raise
        except Exception as e:
            raise JobSaveError(f"Failed to save job '{job_name}': {e}") from e


def main() -> None:
    SyncIntegrationCredentialJob().start()


if __name__ == "__main__":
    main()
