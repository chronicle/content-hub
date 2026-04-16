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

import json
from typing import TYPE_CHECKING

from TIPCommon.base.job import Job
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.rest.soar_api import (
    get_connector_cards,
    get_installed_integrations_of_environment,
    get_installed_jobs,
    save_or_update_job,
)

from ..core.GoogleSecretManagerClient import GoogleSecretManagerClient
from ..core.GoogleSecretManagerConstants import (
    ANY_INTEGRATION_FILTER_VALUE,
    CONNECTORS_KEY,
    DEFAULT_SECRET_VERSION,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    PROJECT_ID_PARAM,
    SERVICE_ACCOUNT_JSON_PARAM,
    SYNC_CREDENTIAL_JOB_SCRIPT_NAME,
    WORKLOAD_IDENTITY_EMAIL_PARAM,
)
from ..core.GoogleSecretManagerExceptions import (
    InvalidConfigurationError,
    JobFetchError,
    JobSaveError,
    ParameterUpdateError,
    SecretAccessError,
)

if TYPE_CHECKING:
    from TIPCommon.data_models import (
        ConnectorCard,
        InstalledIntegrationInstance,
    )
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

    def _init_api_clients(self) -> GoogleSecretManagerClient:
        """Initialize the Google Secret Manager client."""
        service_account_json = extract_configuration_param(
            self.soar_job,
            param_name=SERVICE_ACCOUNT_JSON_PARAM,
            is_mandatory=False,
            print_value=False,
        )
        project_id = extract_configuration_param(
            self.soar_job,
            param_name=PROJECT_ID_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        workload_identity_email = extract_configuration_param(
            self.soar_job,
            param_name=WORKLOAD_IDENTITY_EMAIL_PARAM,
            is_mandatory=False,
            print_value=True,
        )

        self.secret_manager_client = GoogleSecretManagerClient(
            service_account_json=service_account_json,
            project_id=project_id,
            workload_identity_email=workload_identity_email,
        )

        return self.secret_manager_client

    def _perform_job(self) -> None:
        """Fetch secrets and sync to SOAR platform."""
        self._parse_credential_mapping()

        env: str = self.params.environment_name
        self.logger.info(f"Starting credential sync for environment: {env}")

        self._sync_integration_instances()
        self._sync_connectors()
        self._sync_jobs()

        self.logger.info("Credential sync completed.")

    def _parse_credential_mapping(self) -> None:
        """Parse the Credential Mapping JSON string.

        Raises:
            ValueError: If the JSON string is invalid.
        """
        try:
            self.credential_mapping: SingleJson = json.loads(
                self.params.credential_mapping
            )
        except json.JSONDecodeError as e:
            raise InvalidConfigurationError(
                f"Invalid Credential Mapping JSON: {e}"
            ) from e

    def _resolve_secret_and_version(self, mapped_value: str) -> tuple[str, str]:
        """Parse the mapped string, resolving the version if not explicitly provided.

        Args:
            mapped_value (str): The value from the JSON mapping (e.g., 'secret-id:version').

        Returns:
            tuple[str, str]: The (secret_id, resolved_version).
        """
        if ":" in mapped_value:
            secret_id, explicit_version = mapped_value.split(":", 1)
            self.logger.info(
                f"Secret ID '{secret_id}': Using explicitly provided version '{explicit_version}'."
            )
            return secret_id, explicit_version

        secret_id = mapped_value
        if self.secret_manager_client:
            resolved_version = self.secret_manager_client.resolve_latest_enabled_version(secret_id)
        else:
            resolved_version = DEFAULT_SECRET_VERSION

        if resolved_version == DEFAULT_SECRET_VERSION:
            self.logger.info(
                f"Secret ID '{secret_id}': No active versions discovered. "
                f"Falling back to default alias '{DEFAULT_SECRET_VERSION}'."
            )
        else:
            self.logger.info(
                f"Secret ID '{secret_id}': Automatically resolved to latest "
                f"enabled version '{resolved_version}'."
            )

        return secret_id, resolved_version

    def _sync_integration_instances(self) -> None:
        """Sync credentials for integration instances."""
        instances: SingleJson = self.credential_mapping.get(
            INTEGRATION_INSTANCES_KEY,
            {},
        )

        if not instances:
            self.logger.info(
                "No integration instances in credential mapping. Skipping."
            )
            return None

        self.logger.info(f"Processing {len(instances)} integration instance(s)...")

        instances_list: list[InstalledIntegrationInstance] = (
            self._fetch_integration_instances_for_environment()
        )
        if not instances_list:
            self.logger.info(
                "No integration instances found in environment. Skipping."
            )
            return None

        self.instance_name_to_identifier = self._build_instance_name_lookup(
            instances_list,
        )

        self.logger.info(
            f"Found {len(self.instance_name_to_identifier)} integration instance(s) "
            f"in environment '{self.params.environment_name}'."
        )

        for name, param_mapping in instances.items():
            self._update_single_integration_instance(name, param_mapping)

    def _fetch_integration_instances_for_environment(self) -> list[InstalledIntegrationInstance]:
        """Fetch all integration instances for the configured environment.

        Returns:
            List of InstalledIntegrationInstance objects.
        """
        environment: str = self.params.environment_name
        self.logger.info(
            f"Fetching integration instances for environment: {environment}"
        )

        return get_installed_integrations_of_environment(
            chronicle_soar=self.soar_job,
            environment=environment,
            integration_identifier=ANY_INTEGRATION_FILTER_VALUE,
        )

    @staticmethod
    def _build_instance_name_lookup(
        instances: list[InstalledIntegrationInstance]
    ) -> NameIdentifierMap:
        """Build a name → identifier mapping for instances."""
        return {inst.instance_name: inst.identifier for inst in instances}

    def _update_single_integration_instance(
        self,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single integration instance.

        Args:
            name (str): Display name of the instance.
            param_mapping (SingleJson): Param names to secret IDs.
        """
        self.logger.info(f"Processing integration instance: {name}")

        identifier: str | None = self._resolve_instance_identifier(name)
        if identifier is None:
            self.logger.error(
                f"Skipping instance '{name}' — could not resolve identifier."
            )
            return None

        self._set_integration_params(name, identifier, param_mapping)

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

    def _set_integration_params(
        self,
        name: str,
        identifier: str,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on an integration instance.

        Args:
            name (str): Display name of the instance.
            identifier (str): Resolved instance identifier.
            param_mapping (SingleJson): Param names to secret IDs.
        """
        for param_name, mapped_value in param_mapping.items():
            try:
                secret_id, version_id = self._resolve_secret_and_version(mapped_value)
                secret_value: str = self.secret_manager_client.get_secret_value(
                    secret_id=secret_id,
                    version_id=version_id,
                )
                self.soar_job.set_configuration_property(
                    integration_instance_identifier=identifier,
                    property_name=param_name,
                    property_value=secret_value,
                )
                self.logger.info(
                    f"Updated '{param_name}' on instance '{name}' (id: {identifier}) "
                    f"from secret '{secret_id}' version '{version_id}'."
                )
            except (SecretAccessError, ParameterUpdateError):
                raise
            except Exception as e:
                raise ParameterUpdateError(
                    f"Failed to update '{param_name}' on instance '{name}' "
                    f"(id: {identifier}) from secret '{secret_id}': {e}"
                ) from e

    def _sync_connectors(self) -> None:
        """Sync credentials for connectors."""
        connectors: SingleJson = self.credential_mapping.get(CONNECTORS_KEY, {})

        if not connectors:
            self.logger.info("No connectors in credential mapping. Skipping.")
            return

        self.logger.info(f"Processing {len(connectors)} connector(s)...")

        cards: list[ConnectorCard] = self._fetch_connector_cards()
        if not cards:
            self.logger.info("No connectors configured. Skipping.")
            return None

        self.connector_name_to_identifier: NameIdentifierMap = (
            self._build_connector_name_lookup(cards)
        )

        self.logger.info(f"Found {len(self.connector_name_to_identifier)} connector(s).")

        for name, param_mapping in connectors.items():
            self._update_single_connector(name, param_mapping)

    def _fetch_connector_cards(self) -> list[ConnectorCard]:
        """Fetch connector cards for all connectors.

        Returns:
            List of ConnectorCard objects.
        """
        self.logger.info("Fetching connector cards...")

        return get_connector_cards(
            chronicle_soar=self.soar_job,
            integration_name=ANY_INTEGRATION_FILTER_VALUE,
        )

    @staticmethod
    def _build_connector_name_lookup(
        connector_cards: list[ConnectorCard],
    ) -> NameIdentifierMap:
        """Build a display_name → identifier mapping for connectors."""

        return {card.display_name: card.identifier for card in connector_cards}

    def _update_single_connector(
        self,
        name: str,
        param_mapping: SingleJson,
    ) -> None:
        """Resolve and update a single connector.

        Args:
            name (str): Display name of the connector.
            param_mapping (SingleJson): Param names to secret IDs.
        """
        self.logger.info(f"Processing connector: {name}")

        identifier: str | None = self._resolve_connector_identifier(name)
        if identifier is None:
            self.logger.error(
                f"Skipping connector '{name}' — could not resolve identifier."
            )
            return None

        self._set_connector_params(name, identifier, param_mapping)

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
                f"Connector '{connector_name}' not found. "
                f"Available connectors: {available}."
            )

        return identifier

    def _set_connector_params(
        self,
        name: str,
        identifier: str,
        param_mapping: SingleJson,
    ) -> None:
        """Set parameters on a connector instance.

        Args:
            name (str): Display name of the connector.
            identifier (str): Resolved connector identifier.
            param_mapping (SingleJson): Param names to secret IDs.
        """
        for param_name, mapped_value in param_mapping.items():
            try:
                secret_id, version_id = self._resolve_secret_and_version(mapped_value)
                secret_value: str = self.secret_manager_client.get_secret_value(
                    secret_id=secret_id,
                    version_id=version_id,
                )
                self.soar_job.set_connector_parameter(
                    connector_instance_identifier=identifier,
                    parameter_name=param_name,
                    parameter_value=secret_value,
                )
                self.logger.info(
                    f"Updated '{param_name}' on connector '{name}' "
                    f"(id: {identifier}) from secret '{secret_id}' version '{version_id}'."
                )
            except (SecretAccessError, ParameterUpdateError):
                raise
            except Exception as e:
                raise ParameterUpdateError(
                    f"Failed to update '{param_name}' on connector '{name}' "
                    f"(id: {identifier}) from secret '{secret_id}': {e}"
                ) from e

    def _sync_jobs(self) -> None:
        """Sync credentials for jobs.

        Performs a read-modify-write cycle for each job
        listed in the credential mapping.
        """
        jobs: SingleJson = self.credential_mapping.get(JOBS_KEY, {})

        if not jobs:
            self.logger.info("No jobs in credential mapping.")
            return None

        self.logger.info(f"Processing {len(jobs)} job(s)...")

        job_instances: list[SingleJson] | None = self._fetch_job_instances()
        if job_instances is None:
            return None

        name_to_job: SingleJson = self._build_job_name_lookup(job_instances)

        for job_name, param_mapping in jobs.items():
            self.logger.info(f"Processing job: {job_name}")
            self._update_single_job(job_name, param_mapping, name_to_job)

    def _fetch_job_instances(self) -> list[SingleJson] | None:
        """Fetch and normalise the list of installed jobs.

        Returns:
            A flat list of job instance dicts, or ``None`` if the fetch fails or the
            response format is unexpected.
        """
        installed_jobs_response: SingleJson | list[SingleJson] = get_installed_jobs(
            self.soar_job,
        )

        # 1P wraps in {"job_instances": [...]}.
        if (
            isinstance(installed_jobs_response, dict)
            and "job_instances" in installed_jobs_response
        ):
            job_instances: list[SingleJson] = installed_jobs_response["job_instances"]
        elif isinstance(installed_jobs_response, list):
            job_instances: list[SingleJson] = installed_jobs_response
        else:
            self.logger.error(
                "Unexpected response format from get_installed_jobs: "
                "expected list or dict with 'job_instances', got "
                f"{type(installed_jobs_response).__name__}."
            )
            return None

        if not job_instances:
            self.logger.warning("No jobs returned from platform.")
            return None

        return job_instances

    @staticmethod
    def _build_job_name_lookup(
        job_instances: list[SingleJson],
    ) -> SingleJson:
        """Build a display-name → job-dict lookup.

        1P uses ``displayName``; Legacy uses ``name``.

        Args:
            job_instances (list[SingleJson]): Flat list of job dicts.

        Returns:
            Mapping of display name to job dict.
        """
        return {
            inst.get("displayName") or inst.get("name", ""): inst
            for inst in job_instances
        }

    def _update_single_job(
        self,
        job_name: str,
        param_mapping: SingleJson,
        name_to_job: SingleJson,
    ) -> None:
        """Update parameters for a single job.

        Args:
            job_name (str): The display name of the job.
            param_mapping (SingleJson): Map of param name → secret ID.
            name_to_job (SingleJson): Lookup of display name → job dict.
        """
        resolved: tuple[SingleJson, list[SingleJson]] | None = self._resolve_job_data(
            job_name,
            name_to_job,
        )
        if resolved is None:
            return None

        job_data, parameters = resolved

        param_index: SingleJson = self._build_param_index(parameters)

        updated_count: int = self._apply_secrets_to_params(
            job_name,
            param_mapping,
            parameters,
            param_index,
        )

        if updated_count == 0:
            self.logger.warning(
                f"No parameters updated for job '{job_name}' — skipping save."
            )
            return None

        job_data["parameters"] = parameters
        self._persist_job(job_name, job_data, updated_count)

    def _resolve_job_data(
        self,
        job_name: str,
        name_to_job: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Look up a job by name and ensure its parameters are available for update.

        If the list response omitted parameters, fetches the full job details.

        Args:
            job_name (str): The display name of the job.
            name_to_job (SingleJson): Lookup of display name → job dict.

        Returns:
            A ``(job_data, parameters)`` tuple, or ``None`` if the job cannot be resolved.
        """
        job_data: SingleJson | None = name_to_job.get(job_name)
        if job_data is None:
            available: list[str] = list(name_to_job.keys())
            self.logger.error(
                f"Job '{job_name}' not found. Available jobs: {available}."
            )
            return None

        # Shallow copy to avoid mutating the original dict in the lookup.
        job_data: SingleJson = dict(job_data)

        parameters: list[SingleJson] | None = job_data.get("parameters")
        if parameters is None:
            job_data, parameters = self._fetch_full_job_details(job_name, job_data) or (
                None,
                None,
            )
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
            self.logger.warning(
                f"Job '{job_name}' has an empty parameters list — nothing to "
                "update."
            )
            return None

        return job_data, parameters

    def _fetch_full_job_details(
        self,
        job_name: str,
        job_data: SingleJson,
    ) -> tuple[SingleJson, list[SingleJson]] | None:
        """Fetch full job details when the list response omits parameters.

        Args:
            job_name (str): Display name (for logging).
            job_data (SingleJson): The partial job dict from the list response.

        Returns:
            A (job_data, parameters) tuple, or None on failure.
        """
        job_instance_id: str | None = job_data.get("id")
        if job_instance_id is None:
            self.logger.error(
                f"Job '{job_name}' has no id and no parameters — cannot update."
            )
            return None

        self.logger.info(
            f"Fetching full details for job '{job_name}' (id: {job_instance_id})."
        )
        try:
            full_job: SingleJson = get_installed_jobs(
                chronicle_soar=self.soar_job,
                job_instance_id=job_instance_id,
            )
        except JobFetchError:
            raise
        except Exception as e:
            raise JobFetchError(
                f"Failed to fetch details for job '{job_name}' "
                f"(id: {job_instance_id}): {e}"
            ) from e

        if not isinstance(full_job, dict):
            self.logger.error(
                f"Unexpected response format when fetching job details for "
                f"'{job_name}': expected dict, got "
                f"{type(full_job).__name__}."
            )
            return None

        return full_job, full_job.get("parameters", [])

    @staticmethod
    def _build_param_index(parameters: list[SingleJson]) -> dict[str, int]:
        """Build a parameter-name → list-index lookup.

        1P params use ``displayName``; Legacy use ``name``.

        Args:
            parameters (list[SingleJson]): The job's parameter list.

        Returns:
            Mapping of param display name to its index in the list.
        """
        param_index: dict[str, int] = {}
        for idx, p in enumerate(parameters):
            p_name: str = p.get("displayName") or p.get("name", "")
            param_index[p_name] = idx

        return param_index

    def _apply_secrets_to_params(
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
        updated_count = 0
        for param_name, mapped_value in param_mapping.items():
            if param_name not in param_index:
                self.logger.error(
                    f"Parameter '{param_name}' not found on job '{job_name}'. "
                    f"Available parameters: {list(param_index.keys())}."
                )
                continue

            try:
                secret_id, version_id = self._resolve_secret_and_version(mapped_value)
                secret_value: str = self.secret_manager_client.get_secret_value(
                    secret_id=secret_id,
                    version_id=version_id,
                )
                idx: int = param_index[param_name]
                parameters[idx]["value"] = secret_value
                updated_count += 1
                self.logger.info(
                    f"Set '{param_name}' on job '{job_name}' from secret '{secret_id}' version '{version_id}'."
                )
            except SecretAccessError:
                raise
            except Exception as e:
                raise SecretAccessError(
                    f"Failed to fetch secret from location '{secret_id}' for param "
                    f"'{param_name}' on job '{job_name}': {e}"
                ) from e

        return updated_count

    def _persist_job(
        self,
        job_name: str,
        job_data: SingleJson,
        updated_count: int,
    ) -> None:
        """Save the modified job back to the platform.

        Args:
            job_name (str): Display name (for logging).
            job_data (SingleJson): The full job dict with updated parameters.
            updated_count (int): Number of params changed (for logging).
        """
        try:
            save_or_update_job(
                chronicle_soar=self.soar_job,
                job_data=job_data,
            )
            self.logger.info(
                f"Saved job '{job_name}' with {updated_count} updated parameter(s)."
            )
        except JobSaveError:
            raise
        except Exception as e:
            raise JobSaveError(
                f"Failed to save job '{job_name}': {e}"
            ) from e


def main() -> None:
    SyncIntegrationCredentialJob().start()


if __name__ == "__main__":
    main()
