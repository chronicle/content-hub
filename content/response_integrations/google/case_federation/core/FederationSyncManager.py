from __future__ import annotations

import dataclasses
import requests

from soar_sdk.SiemplifyLogger import SiemplifyLogger

from TIPCommon.rest.soar_api import get_federation_cases, patch_federation_cases
from TIPCommon.transformation import convert_list_to_comma_string
import TIPCommon.types

from .constants import SUCCESS_STATUS_CODE


@dataclasses.dataclass
class ApiClientParameters:
    sync_api_root: str


@dataclasses.dataclass
class AuthParameters:
    api_key: str | None


@dataclasses.dataclass
class FederationSyncResult:
    status_code: int
    execution_data: FederationSyncExecutionData | None


@dataclasses.dataclass
class FederationSyncExecutionData:
    continuation_token: str | None
    execution_message: str | None


class FederationSyncManager:

    def __init__(
        self,
        session: requests.Session,
        logger: SiemplifyLogger,
        api_client_parameters: ApiClientParameters,
        auth_parameters: AuthParameters,
        chronicle_soar: TIPCommon.types.ChronicleSOAR,
    ) -> None:
        self.session = session
        self.logger = logger
        self.sync_endpoint = api_client_parameters.sync_api_root
        self.api_key = auth_parameters.api_key
        self.chronicle_soar = chronicle_soar

    def sync_cases_from(self, continuation_token: str | None) -> FederationSyncResult:
        """Sync cases that were created or modified since the last sync execution.

        Args:
            continuation_token: Token received from the server for fetching the next
            batch of cases.

        Returns:
            The result of syncing cases.
        """
        fetch_body = self._get_cases_to_sync(continuation_token)
        updated_cases = fetch_body.get(
            "cases",
            fetch_body.get("legacyFederatedCases", []),
        )
        execution_data = FederationSyncExecutionData(
            continuation_token=fetch_body.get(
                "continuationToken",
                fetch_body.get("nextPageToken"),
            ),
            execution_message=fetch_body.get(
                "executionMessage",
                "No additional execution details available."
            ),
        )
        case_ids = convert_list_to_comma_string([case["id"] for case in updated_cases])
        self.logger.info(f"Modified cases IDs: {case_ids}")
        self.logger.info(f"Number of cases to sync: {len(updated_cases)}")

        if len(updated_cases) > 0:
            sync_result = self._sync(cases_payload=updated_cases)
            self.logger.info(f"Response status code: {sync_result.status_code}")

            return FederationSyncResult(
                status_code=sync_result.status_code, execution_data=execution_data
            )

        return FederationSyncResult(
            status_code=SUCCESS_STATUS_CODE, execution_data=execution_data
        )

    def _get_cases_to_sync(
        self,
        continuation_token: str | None,
    ) -> TIPCommon.types.SingleJson:
        """Retrieve list of cases that have been created or modified since the
        last sync execution.

        Args:
            continuation_token: Token received from the server for fetching the next
            batch of cases.

        Returns:
            The response body of fetching the cases which should be synced.
        """
        fetch_result = get_federation_cases(
            chronicle_soar=self.chronicle_soar,
            continuation_token=continuation_token,
        )
        self.logger.info(f"Response status code: {fetch_result.status_code}")
        return fetch_result.json()

    def _sync(self, cases_payload: TIPCommon.types.SingleJson) -> requests.Response:
        """Sync the updated cases.

        Args:
            cases_payload: The payload of the cases to sync.

        Returns:
            The response of the sync.
        """
        return patch_federation_cases(
            chronicle_soar=self.chronicle_soar,
            cases_payload=cases_payload,
            api_root=self.sync_endpoint,
            api_key=self.api_key,
        )
