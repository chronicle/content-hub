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

from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from .GoogleSecretManagerClient import GoogleSecretManagerClient
from .GoogleSecretManagerConstants import (
    PROJECT_ID_PARAM,
    SERVICE_ACCOUNT_JSON_PARAM,
    VERIFY_SSL_PARAM,
    WORKLOAD_IDENTITY_EMAIL_PARAM,
)


class GoogleSecretManagerAction(Action, ABC):
    """Base action class for Google Secret Manager actions."""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.secret_manager_client: GoogleSecretManagerClient | None = None

    def _init_api_clients(self) -> GoogleSecretManagerClient:
        """Extract config and initialize the API client."""
        service_account_json = extract_configuration_param(
            self.soar_action,
            param_name=SERVICE_ACCOUNT_JSON_PARAM,
            is_mandatory=False,
            print_value=False,
        )
        project_id = extract_configuration_param(
            self.soar_action,
            param_name=PROJECT_ID_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        workload_identity_email = extract_configuration_param(
            self.soar_action,
            param_name=WORKLOAD_IDENTITY_EMAIL_PARAM,
            is_mandatory=False,
            print_value=True,
        )
        verify_ssl = extract_configuration_param(
            self.soar_action,
            param_name=VERIFY_SSL_PARAM,
            default_value=True,
            input_type=bool,
            is_mandatory=False,
            print_value=True,
        )

        self.secret_manager_client = GoogleSecretManagerClient(
            service_account_json=service_account_json,
            project_id=project_id,
            workload_identity_email=workload_identity_email,
            verify_ssl=verify_ssl,
        )

        return self.secret_manager_client
