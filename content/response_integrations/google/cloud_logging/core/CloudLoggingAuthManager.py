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

from google.auth.transport.requests import AuthorizedSession
from google.auth.exceptions import RefreshError

from TIPCommon.rest.auth import (
    get_auth_request,
    build_credentials_from_sa,
)
from TIPCommon.rest.gcp import (
    get_workload_sa_email,
    retrieve_project_id
)
from TIPCommon.types import ChronicleSOAR, SingleJson
from TIPCommon.utils import is_empty_string_or_none

from ..core.consts import SCOPES
from ..core.datamodels import ApiManagerParams
from ..core.exceptions import CloudAuthenticationError
from ..core.utils import parse_string_to_dict, get_integration_params, IntegrationParams


def build_auth_manager(chronicle_soar: ChronicleSOAR) -> CloudLoggingAuthManager:
    """
    Extract auth params and build Auth manager.

    Args:
         chronicle_soar: ChronicleSOAR SDK object

    Returns:
        Google Gmail Api manager object
    """

    integration_params: IntegrationParams = get_integration_params(chronicle_soar)

    return CloudLoggingAuthManager(
        api_root=integration_params.api_root,
        service_account_json=integration_params.service_account_json,
        workload_identity_email=integration_params.workload_identity_email,
        quota_project_id=integration_params.quota_project_id,
        project_id=integration_params.project_id,
        organization_id=integration_params.organization_id,
        verify_ssl=integration_params.verify_ssl,
    )


def build_api_manager_params(auth_manager: CloudLoggingAuthManager) -> ApiManagerParams:
    return ApiManagerParams(
        api_root=auth_manager.api_root,
        project_id=auth_manager.project_id,
        organization_id=auth_manager.organization_id,
    )


class CloudLoggingAuthManager:
    def __init__(
        self,
        api_root: str | None,
        service_account_json: str | SingleJson | None,
        workload_identity_email: str | None,
        quota_project_id: str | None,
        project_id: str | None,
        organization_id: str | None,
        verify_ssl: bool,
    ):
        self.api_root = api_root if api_root.endswith("/") else f"{api_root}/"
        self.verify_ssl = verify_ssl
        self.project_id = project_id or retrieve_project_id(
            service_account_json, workload_identity_email
        )
        self.organization_id = organization_id
        self.service_account_json = service_account_json
        self.workload_identity_email = workload_identity_email
        if not is_empty_string_or_none(service_account_json) and not isinstance(
            service_account_json, dict
        ):
            service_account_json = parse_string_to_dict(service_account_json)

        try:
            self.credentials = build_credentials_from_sa(
                user_service_account=service_account_json,
                target_principal=workload_identity_email,
                scopes=SCOPES,
                quota_project_id=quota_project_id,
                verify_ssl=verify_ssl,
            )

        except RefreshError as e:
            workload_sa_email = get_workload_sa_email("Unknown Principal")
            raise CloudAuthenticationError(
                "Impersonation is not allowed for the provided service "
                f"account {workload_identity_email}. "
                'Please add the "Service Account Token Creator" role to the '
                f"service account: {workload_sa_email}"
            ) from e

    def prepare_session(self) -> AuthorizedSession:
        """Preparse session object to be used in API session."""
        session = AuthorizedSession(
            self.credentials,
            auth_request=get_auth_request(verify_ssl=self.verify_ssl),
        )
        session.verify = self.verify_ssl

        return session
