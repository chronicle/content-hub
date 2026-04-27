from __future__ import annotations

import dataclasses
import json

from TIPCommon.base.job import Job

from ..core.constants import FEDERATION_SYNC_JOB_SCRIPT_NAME, SUCCESS_STATUS_CODE
from ..core.exceptions import MissingParameterError
from ..core.FederationSyncManager import (
    FederationSyncManager,
    ApiClientParameters,
    AuthParameters,
    FederationSyncExecutionData,
)

LAST_EXECUTION_DATA_KEY = "lastExecutionData"


class CaseFederationSyncJob(Job):

    def _validate_params(self) -> None:
        """Validate job params"""

        if not self.params.target_platform or not self.params.api_key:
            raise MissingParameterError(
                "API Key and Target Platform must be provided"
            )

    def _init_api_clients(self) -> FederationSyncManager:
        """
        Create a federation synchronization manager instance, that will sync the cases.

        If this platform is marked as primary, then sync will be done to localhost.
        Otherwise, we expect a target platform to sync to, and an API key for
        authentication as parameters.
        """
        session = self.soar_job.session

        return FederationSyncManager(
            session,
            self.logger,
            ApiClientParameters(
                sync_api_root=f"https://{self.params.target_platform}/api",
            ),
            AuthParameters(api_key=self.params.api_key),
            chronicle_soar=self.soar_job,
        )

    def _perform_job(self) -> None:
        """Perform the main flow of job"""
        previous_execution_data = self._fetch_previous_execution_data()
        self.logger.info(
            f"Previous execution details: {previous_execution_data.execution_message}"
        )

        sync_result = self.api_client.sync_cases_from(
            previous_execution_data.continuation_token
        )

        if sync_result.status_code == SUCCESS_STATUS_CODE:
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
                    f"Sync finished successfully, execution details: "
                    f"{new_execution_data.execution_message}"
                )

        else:
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
            identifier=self.name_id, property_key=LAST_EXECUTION_DATA_KEY
        )

        if previous_execution_data_json is None:
            # This is the first run, provide default first values to sync all items
            return FederationSyncExecutionData(
                continuation_token=None,
                execution_message=(
                    "This is the first execution, starting sync of all relevant cases."
                ),
            )

        previous_execution_data = json.loads(previous_execution_data_json)
        return FederationSyncExecutionData(
            continuation_token=previous_execution_data["continuation_token"],
            execution_message=previous_execution_data["execution_message"],
        )

    def _save_next_execution_data(
        self, execution_data: FederationSyncExecutionData
    ) -> None:
        """Save the current execution data of the job, with its unique id.

        Args:
            execution_data: Data to save about the current sync execution.
        """
        self.soar_job.set_job_context_property(
            identifier=self.name_id,
            property_key=LAST_EXECUTION_DATA_KEY,
            property_value=json.dumps(dataclasses.asdict(execution_data)),
        )


def main() -> None:
    CaseFederationSyncJob(FEDERATION_SYNC_JOB_SCRIPT_NAME).start()


if __name__ == "__main__":
    main()
