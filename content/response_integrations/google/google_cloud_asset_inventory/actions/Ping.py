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
from TIPCommon.base.utils import validate_manager
from TIPCommon import validation
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.utils import is_empty_string_or_none
from ..core import constants
from ..core.GoogleCloudAssetInventoryManager import GoogleCloudAssetInventoryManager


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            "Successfully connected to the"
            f" {constants.INTEGRATION_DISPLAY_NAME} server with the provided"
            " connection parameters!"
        )
        self.error_output_message = (
            "Failed to connect to the" f" {constants.INTEGRATION_DISPLAY_NAME} service!"
        )

    def _extract_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
            remove_whitespaces=True,
        )
        self.params.organization_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Organization ID",
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Project ID",
            is_mandatory=False,
            print_value=True,
            remove_whitespaces=True,
        )
        self.params.user_service_account = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="User Service Account",
            is_mandatory=False,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.quota_project_id = extract_configuration_param(
            self.soar_action,
            param_name="Quota Project ID",
            is_mandatory=False,
            provider_name=constants.INTEGRATION_NAME,
        )
        self.params.workload_identity_email = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Workload Identity Email",
            is_mandatory=False,
            print_value=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.user_service_account):
            self.params.user_service_account = validator.validate_json(
                param_name="User Service Account",
                json_string=self.params.user_service_account,
                print_value=False,
            )
        if not is_empty_string_or_none(self.params.workload_identity_email):
            self.params.workload_identity_email = validator.validate_email(
                param_name="Workload Identity Email",
                email=self.params.workload_identity_email,
                print_value=True,
            )

    def _init_managers(self) -> GoogleCloudAssetInventoryManager:
        return GoogleCloudAssetInventoryManager(
            api_root=self.params.api_root,
            organization_id=self.params.organization_id,
            project_id=self.params.project_id,
            verify_ssl=self.params.verify_ssl,
            service_account_=self.params.user_service_account,
            quota_project_id=self.params.quota_project_id,
            workload_identity_email=self.params.workload_identity_email,
            logger=self.logger,
        )

    def _perform_action(
        self, manager: GoogleCloudAssetInventoryManager, _=None
    ) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)
        self.logger.info("Testing connectivity")
        manager.test_connectivity()
        self.logger.info("Successfully connected to Google Cloud Asset Inventory")


def main() -> None:
    Ping(constants.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
