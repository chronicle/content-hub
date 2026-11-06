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

"""Get Resource Snapshot action script."""
from __future__ import annotations

from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict

from TIPCommon import convert_list_to_comma_string
from TIPCommon import validation
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from ..core import constants
from ..core.GoogleCloudAssetInventoryManager import GoogleCloudAssetInventoryManager


class GetResourceSnapshot(Action):
    """Main class with Get Resource Snapshot action flow."""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            f"Error executing action "
            f'"{constants.GET_RESOURCE_SNAPSHOT_SCRIPT_NAME}"'
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
        # Action Parameters
        self.params.resource_names = extract_action_param(
            self.soar_action,
            param_name="Resource Names",
            is_mandatory=True,
            print_value=True,
        )
        self.params.fields_to_return = extract_action_param(
            self.soar_action,
            param_name="Fields To Return",
            is_mandatory=False,
            print_value=True,
            default_value=constants.DEFAULT_FIELDS_TO_RETURN,
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
        self.params.resource_names = validator.validate_csv(
            param_name="Resource Names",
            csv_string=self.params.resource_names,
            print_value=False,
        )
        self.parse_and_validate_fields_to_return(validator)

    def parse_and_validate_fields_to_return(
        self, validator: validation.ParameterValidator
    ) -> None:
        """Parse and validate "Fields To Return" action parameter.

        Args:
            validator: Validator object.
        """

        fields_to_return = validator.validate_csv(
            param_name="Fields To Return", csv_string=self.params.fields_to_return
        )

        # Otherwise if we don't have "name" field in fields to return and query
        # is not "*", we need to include "name"
        if (
            constants.RESOURCE_SNAPSHOT_NAME_KEY not in fields_to_return
            and constants.DEFAULT_FIELDS_TO_RETURN not in fields_to_return
        ):
            fields_to_return.append(constants.RESOURCE_SNAPSHOT_NAME_KEY)

        self.params.fields_to_return = fields_to_return

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

        self.logger.info("Getting the information about the resources")

        resource_names = set(self.params.resource_names)

        found_resources = []
        not_found_resources = []

        snapshots = manager.get_resource_snapshots(
            asset_names=resource_names, read_mask=self.params.fields_to_return
        )

        response_resources_names = [snapshot.asset_name for snapshot in snapshots]

        for resource in resource_names:
            if resource in response_resources_names:
                found_resources.append(resource)
            else:
                not_found_resources.append(resource)

        if not found_resources:
            self.output_message = "No information was found for the provided resources."
            self.result_value = False
            return

        found_resources_csv = convert_list_to_comma_string(
            found_resources, delimiter=",\n"
        )

        self.output_message = (
            "Successfully enriched the following resources using"
            f" {constants.INTEGRATION_DISPLAY_NAME}: {found_resources_csv}"
        )

        if not_found_resources:
            not_found_resources_csv = convert_list_to_comma_string(
                not_found_resources, delimiter=",\n"
            )
            self.output_message += (
                "\n\nAction wasn't able to enrich the following"
                f" resources using {constants.INTEGRATION_DISPLAY_NAME}:"
                f" {not_found_resources_csv}"
            )

        self.logger.info("Adding resources data to JSON results")
        json_results = {
            snapshot.asset_name: snapshot.to_json() for snapshot in snapshots
        }

        self.json_results = convert_dict_to_json_result_dict(json_results)


def main() -> None:
    GetResourceSnapshot(constants.GET_RESOURCE_SNAPSHOT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
