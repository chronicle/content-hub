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
import requests
import json
import os

from soar_sdk.SiemplifyLogger import SiemplifyLogger

from google.auth.transport.requests import AuthorizedSession, Request
from google.auth.exceptions import RefreshError

from TIPCommon.base.utils import CreateSession
from TIPCommon.rest.soar_api import get_federation_cases
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials
from TIPCommon.rest.auth import get_auth_request
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.utils import camel_to_snake_case
import TIPCommon.types

from .constants import SUCCESS_STATUS_CODE


@dataclasses.dataclass
class ApiClientParameters:
    sync_api_root: str


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
        chronicle_soar: TIPCommon.types.ChronicleSOAR,
    ) -> None:
        self.session = session
        self.logger = logger
        self.sync_endpoint = api_client_parameters.sync_api_root
        self.chronicle_soar = chronicle_soar
        self.http_client = None
        self._get_credentials_using_p4sa(
            verify_ssl=True
        )
        self._prepare_http_client()

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
            for case in updated_cases:
                if alerts_sla := case.get("alertsSla"):
                    if expiration_status := alerts_sla.get("expirationStatus"):
                        alerts_sla["expirationStatus"] = camel_to_snake_case(expiration_status)
                if case_sla := case.get("caseSla"):
                    if expiration_status := case_sla.get("expirationStatus"):
                        case_sla["expirationStatus"] = camel_to_snake_case(expiration_status)
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
        url = (self.sync_endpoint +
               "/legacyFederatedCases:legacyBatchPatchFederatedCases")
        payload = json.dumps({"cases":cases_payload})
        header = {"CLIENT-ADDRESS": os.getenv("CLIENT_ADDRESS")}
        response = (
            self.http_client.request("POST", url, data=payload, headers=header)
        )
        return response

    def _get_credentials_using_p4sa(self, verify_ssl: bool
    ) -> None:
        project_id = os.getenv("GCP_PROJECT_ID")

        self.creds = get_secops_siem_tenant_credentials(
            chronicle_soar=self.chronicle_soar,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            quota_project_id=project_id,
            fallback_to_env_email=True
        )


    def _prepare_http_client(self) -> None:
        """
        Prepare http client
        """
        auth_session = CreateSession.create_session()
        auth_session.verify = True
        self.http_client = AuthorizedSession(
            self.creds, auth_request=Request(session=auth_session)
        )
        self.http_client.verify = True
