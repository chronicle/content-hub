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

from collections import defaultdict

from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict

from TIPCommon import validation
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string
from TIPCommon.utils import is_empty_string_or_none
from ..core import constants
from ..core.GoogleCloudPolicyIntelligenceManager import GoogleCloudPolicyIntelligenceManager


class SearchServiceAccountActivity(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            "Error executing action"
            f' "{constants.SEARCH_SERVICE_ACCOUNT_ACTIVITY_SCRIPT_NAME}".'
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
        self.params.location_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Location ID",
            is_mandatory=False,
            print_value=True,
            default_value=constants.DEFAULT_LOCATION_ID
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
        self.params.target_project_id = extract_action_param(
            self.soar_action, param_name="Project ID", print_value=True
        )
        self.params.service_account_resource_name = extract_action_param(
            self.soar_action,
            param_name="Service Account Resource Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_activities_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Activities To Return",
            is_mandatory=True,
            print_value=True,
            input_type=str,
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
        self.params.service_account_resource_name = validator.validate_csv(
            param_name="Service Account Resource Name",
            csv_string=self.params.service_account_resource_name,
            print_value=True,
        )
        self.params.max_activities_to_return = validator.validate_range(
            param_name="Max Activities To Return",
            value=self.params.max_activities_to_return,
            min_limit=constants.MIN_ACTIVITIES_LIMIT,
            max_limit=constants.MAX_ACTIVITIES_LIMIT,
        )

    def _init_managers(self) -> GoogleCloudPolicyIntelligenceManager:
        return GoogleCloudPolicyIntelligenceManager(
            api_root=self.params.api_root,
            project_id=(self.params.target_project_id or self.params.project_id),
            verify_ssl=self.params.verify_ssl,
            service_account_=self.params.user_service_account,
            quota_project_id=self.params.quota_project_id,
            workload_identity_email=self.params.workload_identity_email,
            location_id=self.params.location_id,
            logger=self.logger,
        )

    def _perform_action(
        self, manager: GoogleCloudPolicyIntelligenceManager, _=None
    ) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        resources = self.params.service_account_resource_name

        self.logger.info(
            "Searching service account activities with "
            f"resources={resources} and "
            f"maxActivitiesLimit={self.params.max_activities_to_return}"
        )
        results = manager.search_service_account_activity(
            resource_names=resources, limit=self.params.max_activities_to_return
        )
        self.logger.info(f"Searched {len(results)} activities")

        response_resources_names = []
        json_results = defaultdict(list)
        for resource in results:
            response_resources_names.append(resource.resource_name)
            json_results[resource.resource_name].append(resource.to_json())

        activity_data_found = []
        activity_data_not_found = []
        for resource in resources:
            if resource in set(response_resources_names):
                activity_data_found.append(resource)
            else:
                activity_data_not_found.append(resource)

        if not activity_data_found:
            self.output_message = (
                "No activity was found for the provided service accounts in"
                f" {constants.INTEGRATION_DISPLAY_NAME}"
            )
            self.result_value = False
            return

        activity_data_found_csv = convert_list_to_comma_string(
            activity_data_found, delimiter=",\n"
        )
        self.output_message = (
            "Successfully found activity for the following service accounts in"
            f" {constants.INTEGRATION_DISPLAY_NAME}:"
            f" {activity_data_found_csv}"
        )

        if activity_data_not_found:
            activity_data_not_found_csv = convert_list_to_comma_string(
                activity_data_not_found, delimiter=",\n"
            )
            self.output_message += (
                "\n\nNo activity was found for the following service accounts"
                f" in {constants.INTEGRATION_DISPLAY_NAME}:"
                f" {activity_data_not_found_csv}"
            )

        self.logger.info("Adding service account data to JSON results")
        self.json_results = convert_dict_to_json_result_dict(json_results)


def main() -> None:
    SearchServiceAccountActivity(
        constants.SEARCH_SERVICE_ACCOUNT_ACTIVITY_SCRIPT_NAME
    ).run()


if __name__ == "__main__":
    main()
