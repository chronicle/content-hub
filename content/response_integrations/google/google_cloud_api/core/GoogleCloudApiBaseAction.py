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

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from google_cloud_api.core.GoogleCloudApiAuthManager import build_auth_manager
from google_cloud_api.core.GoogleCloudApiManager import ApiManager
from google_cloud_api.core.GoogleCloudApiConstants import INTEGRATION_IDENTIFIER
from google_cloud_api.core.GoogleCloudApiDatamodels import IntegrationPlaceholders


class BaseAction(Action):
    """This is a base action class."""

    def _init_api_clients(
            self,
    ) -> ApiManager:
        """Prepare API client."""
        auth_manager = build_auth_manager(self.soar_action)

        organizations_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Organization ID",
            print_value=True
        )
        project_id = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Project ID",
            print_value=True
        )
        integration_placeholders = IntegrationPlaceholders(
            project_id=project_id or auth_manager.project_id,
            org_id=organizations_id
        )

        return ApiManager(
            auth_manager.prepare_session(),
            placeholders=integration_placeholders,
            logger=self.logger
        )
