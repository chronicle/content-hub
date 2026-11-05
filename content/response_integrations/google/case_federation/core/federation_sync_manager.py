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
import os
from typing import TYPE_CHECKING

import requests
from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import AuthorizedSession, Request
from TIPCommon.base.utils import CreateSession
from TIPCommon.rest.auth import get_secops_siem_tenant_credentials
from TIPCommon.rest.soar_api import get_federation_cases, patch_federation_cases
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.utils import camel_to_snake_case

from .constants import (
    BATCH_PATCH_FEDERATED_CASES_ENDPOINT_SUFFIX,
    CLIENT_ADDRESS_ENV_VAR,
    CLIENT_ADDRESS_NOT_FOUND_ERROR_MESSAGE,
    CREDENTIALS_REFRESH_ERROR_MESSAGE,
    GCP_PROJECT_ID_ENV_VAR,
    REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER,
    SUCCESS_STATUS_CODE,
    SYNC_REQUEST_ERROR_MESSAGE,
)
from .exceptions import CaseFederationError

if TYPE_CHECKING:
    import google.auth.credentials
    import TIPCommon.types
    from soar_sdk.SiemplifyLogger import SiemplifyLogger


@dataclasses.dataclass
class ApiClientParameters:
    sync_api_root: str
    verify_ssl: bool = True


@dataclasses.dataclass
class AuthParameters:
    api_key: str | None


@dataclasses.dataclass
class FederationSyncResult:
    status_code: int
    execution_data: FederationSyncExecutionData | None
    cases_payload: list[TIPCommon.types.SingleJson] | None = None
    response_text: str | None = None


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
        auth_parameters: AuthParameters | None = None,
    ) -> None:
        self.session = session
        self.logger = logger
        self.sync_endpoint = api_client_parameters.sync_api_root
        self.api_key = auth_parameters.api_key if auth_parameters is not None else None
        self.chronicle_soar = chronicle_soar
        self.verify_ssl = api_client_parameters.verify_ssl
        self.http_client = (
            None if auth_parameters is not None else self._prepare_http_client(self._get_credentials_using_p4sa())
        )

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
            execution_message=fetch_body.get("executionMessage", "No additional execution details available."),
        )
        case_ids = convert_list_to_comma_string([case["id"] for case in updated_cases])
        self.logger.info(f"Modified cases IDs: {case_ids}")
        self.logger.info(f"Number of cases to sync: {len(updated_cases)}")

        if len(updated_cases) > 0:
            if self.http_client is not None:
                for case in updated_cases:
                    for sla_key in ("alertsSla", "caseSla"):
                        if (sla := case.get(sla_key)) and (expiration_status := sla.get("expirationStatus")):
                            sla["expirationStatus"] = camel_to_snake_case(expiration_status)
            sync_result = self._sync(cases_payload=updated_cases)
            self.logger.info(f"Response status code: {sync_result.status_code}")

            return FederationSyncResult(
                status_code=sync_result.status_code,
                execution_data=execution_data,
                cases_payload=updated_cases,
                response_text=sync_result.text,
            )

        return FederationSyncResult(status_code=SUCCESS_STATUS_CODE, execution_data=execution_data)

    def _get_cases_to_sync(
        self,
        continuation_token: str | None,
    ) -> TIPCommon.types.SingleJson:
        """Retrieve list of cases that have been created or modified since the last sync execution.

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

        Raises:
            CaseFederationError: If the CLIENT_ADDRESS environment variable is not set,
                or if authenticating or sending the sync request fails.

        """
        if self.http_client is None:
            return patch_federation_cases(
                chronicle_soar=self.chronicle_soar,
                cases_payload=cases_payload,
                api_root=self.sync_endpoint,
                api_key=self.api_key,
            )

        client_address = os.getenv(CLIENT_ADDRESS_ENV_VAR)
        if not client_address:
            raise CaseFederationError(CLIENT_ADDRESS_NOT_FOUND_ERROR_MESSAGE)

        url = f"{self.sync_endpoint.rstrip('/')}{BATCH_PATCH_FEDERATED_CASES_ENDPOINT_SUFFIX}"
        payload = json.dumps({"cases": cases_payload})
        header = {REMOTE_PLATFORM_BACKSTORY_REDIRECT_HEADER: client_address}
        try:
            return self.http_client.request("POST", url, data=payload, headers=header)
        except RefreshError as error:
            raise CaseFederationError(CREDENTIALS_REFRESH_ERROR_MESSAGE) from error
        except (TransportError, requests.RequestException) as error:
            raise CaseFederationError(SYNC_REQUEST_ERROR_MESSAGE) from error

    def _get_credentials_using_p4sa(self) -> google.auth.credentials.Credentials:
        """Retrieve short-lived SIEM tenant credentials using the P4SA.

        Returns:
            The short-lived Google auth credentials for the SIEM tenant.

        """
        project_id = os.getenv(GCP_PROJECT_ID_ENV_VAR)

        return get_secops_siem_tenant_credentials(
            chronicle_soar=self.chronicle_soar,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            quota_project_id=project_id,
        )

    def _prepare_http_client(self, credentials: google.auth.credentials.Credentials) -> AuthorizedSession:
        """Create and configure an AuthorizedSession for syncing federated cases.

        Args:
            credentials: Credentials used to authorize outgoing HTTP requests.

        Returns:
            The configured authorized HTTP session.

        """
        auth_session = CreateSession.create_session()
        auth_session.verify = self.verify_ssl
        http_client = AuthorizedSession(credentials, auth_request=Request(session=auth_session))
        http_client.verify = self.verify_ssl
        return http_client
