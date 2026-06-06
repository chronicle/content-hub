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

from .authentication import IntegrationParameters, build_auth_params
from .manager import GoogleSecretManagerClient


class GoogleSecretManagerAction(Action, ABC):
    """Base action class for Google Secret Manager actions."""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.secret_manager_client: GoogleSecretManagerClient | None = None
        self.error_output_message: str = ""

    def _init_api_clients(self) -> GoogleSecretManagerClient:
        """Extract config and initialize the API client.

        Returns:
            GoogleSecretManagerClient: The initialized client.

        """
        auth_params: IntegrationParameters = build_auth_params(self.soar_action)

        self.secret_manager_client = GoogleSecretManagerClient(
            service_account_json=auth_params.service_account_json,
            project_id=auth_params.project_id,
            workload_identity_email=auth_params.workload_identity_email,
            logger=self.logger,
            verify_ssl=auth_params.verify_ssl,
        )

        return self.secret_manager_client
