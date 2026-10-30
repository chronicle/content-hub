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

import dataclasses
import json
import re
from urllib.parse import urlparse

from TIPCommon.base.job import Job

from ..core.constants import (
    CHRONICLE_API_URL_PATH_REGEX,
    FEDERATION_SYNC_JOB_SCRIPT_NAME,
    HAS_FAILED_KEY,
    INVALID_CHRONICLE_API_URL_ERROR_MESSAGE,
    LAST_EXECUTION_DATA_KEY,
    MISSING_PARAMETERS_ERROR_MESSAGE,
    SUCCESS_STATUS_CODE,
    V1ALPHA_PROJECTS_PATH_SEGMENT,
    VERSIONED_PROJECTS_PATH_REGEX,
)
from ..core.exceptions import InvalidParameterError, MissingParameterError
from ..core.federation_sync_manager import (
    ApiClientParameters,
    AuthParameters,
    FederationSyncExecutionData,
    FederationSyncManager,
)


def build_sync_api_root(chronicle_api_url: str) -> str:
    """Normalize the Chronicle API URL to use the v1alpha Chronicle API path.

    Args:
        chronicle_api_url: The configured Chronicle API URL of the primary platform.

    Returns:
        The normalized Chronicle API URL with the `/v1alpha/projects/` segment.

    """
    normalized = chronicle_api_url.rstrip("/")
    return re.sub(VERSIONED_PROJECTS_PATH_REGEX, V1ALPHA_PROJECTS_PATH_SEGMENT, normalized, count=1)


class CaseFederationSyncJob(Job):
    def _validate_params(self) -> None:
        """Validate job params.

        Raises:
            MissingParameterError: If neither Chronicle API URL nor both Target Platform and API Key are provided.
            InvalidParameterError: If the Chronicle API URL is not a valid Chronicle API URL.

        """
        if self.params.chronicle_apiurl:
            parsed_url = urlparse(self.params.chronicle_apiurl)
            if (
                parsed_url.scheme != "https"
                or not parsed_url.netloc
                or not re.match(CHRONICLE_API_URL_PATH_REGEX, parsed_url.path)
            ):
                raise InvalidParameterError(INVALID_CHRONICLE_API_URL_ERROR_MESSAGE)
            return

        if not self.params.target_platform or not self.params.api_key:
            raise MissingParameterError(MISSING_PARAMETERS_ERROR_MESSAGE)

    def _init_api_clients(self) -> FederationSyncManager:
        """Create a federation synchronization manager instance, that will sync the cases.

        Returns:
            The initialized federation synchronization manager.

        """
        session = self.soar_job.session
        verify_ssl: bool = getattr(self.params, "verify_ssl", True)

        if self.params.chronicle_apiurl:
            return FederationSyncManager(
                session,
                self.logger,
                ApiClientParameters(
                    sync_api_root=build_sync_api_root(self.params.chronicle_apiurl),
                    verify_ssl=verify_ssl,
                ),
                chronicle_soar=self.soar_job,
            )

        return FederationSyncManager(
            session,
            self.logger,
            ApiClientParameters(
                sync_api_root=f"https://{self.params.target_platform}/api",
                verify_ssl=verify_ssl,
            ),
            chronicle_soar=self.soar_job,
            auth_parameters=AuthParameters(api_key=self.params.api_key),
        )

    def _perform_job(self) -> None:
        """Perform the main flow of job."""
        previous_execution_data = self._fetch_previous_execution_data()
        self.logger.info(f"Previous execution details: {previous_execution_data.execution_message}")

        sync_result = self.api_client.sync_cases_from(previous_execution_data.continuation_token)

        if sync_result.status_code == SUCCESS_STATUS_CODE:
            if self._fetch_has_previous_run_failed():
                self._save_has_previous_run_failed(has_failed=False)

            new_execution_data = sync_result.execution_data
            if new_execution_data.continuation_token is None:
                self.logger.info(
                    "Sync finished successfully, without any cases to sync. "
                    "Keeping the previous execution data: "
                    f"{previous_execution_data.execution_message}"
                )

            else:
                self._save_next_execution_data(new_execution_data)
                self.logger.info(
                    f"Sync finished successfully, execution details: {new_execution_data.execution_message}"
                )

        else:
            if not self._fetch_has_previous_run_failed():
                self.logger.error(f"Failed cases payload: {json.dumps(sync_result.cases_payload)}")
                self.logger.error(f"Failed sync response: {sync_result.response_text}")
                self._save_has_previous_run_failed(has_failed=True)

            self.logger.error(
                f"Sync finished unsuccessfully with status code "
                f"{sync_result.status_code}, keeping previous execution data: "
                f"{previous_execution_data.execution_message}"
            )

    def _fetch_previous_execution_data(self) -> FederationSyncExecutionData:
        """Fetch the previous execution data of the job by its unique id.

        Returns:
            The previous execution data.

        """
        previous_execution_data_json = self.soar_job.get_job_context_property(
            identifier=self.name_id,
            property_key=LAST_EXECUTION_DATA_KEY,
        )

        if previous_execution_data_json is None:
            # This is the first run, provide default first values to sync all items
            return FederationSyncExecutionData(
                continuation_token=None,
                execution_message="This is the first execution, starting sync of all relevant cases.",
            )

        previous_execution_data: dict[str, str | None] = json.loads(previous_execution_data_json)
        return FederationSyncExecutionData(
            continuation_token=previous_execution_data["continuation_token"],
            execution_message=previous_execution_data["execution_message"],
        )

    def _save_next_execution_data(self, execution_data: FederationSyncExecutionData) -> None:
        """Save the current execution data of the job, with its unique id.

        Args:
            execution_data: Data to save about the current sync execution.

        """
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=LAST_EXECUTION_DATA_KEY,
            property_value=json.dumps(dataclasses.asdict(execution_data)),
        )

    def _fetch_has_previous_run_failed(self) -> bool:
        """Fetch whether the previous run of the job failed.

        Returns:
            True if the previous run failed, False otherwise.

        """
        has_failed_json = self.soar_job.get_job_context_property(identifier=self.name_id, property_key=HAS_FAILED_KEY)
        if has_failed_json is None:
            return False

        return bool(json.loads(has_failed_json))

    def _save_has_previous_run_failed(self, *, has_failed: bool) -> None:
        """Save whether the current run of the job failed.

        Args:
            has_failed: Whether the current sync execution failed.

        """
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=HAS_FAILED_KEY,
            property_value=json.dumps(has_failed),
        )


def main() -> None:
    """Run the case federation sync job."""
    CaseFederationSyncJob(FEDERATION_SYNC_JOB_SCRIPT_NAME).start()


if __name__ == "__main__":
    main()
