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

from typing import Any

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from ..core import consts
from ..core.exceptions import GoogleCloudRecommenderStatusNotFoundError
from ..core.GoogleCloudRecommenderManager import (
    GoogleCloudRecommenderManager,
    GoogleCloudResourceManager,
)
from ..core.UtilsManager import test_service_connectivity


class GetRecommendation(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully found recommendation in the {consts.PROVIDER_NAME}"
            " service"
        )
        self.error_output_message = (
            "Error executing action " f'"{consts.GET_RECOMMENDATION_SCRIPT_NAME}."'
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        validator.validate_csv(
            param_name="Recommendation Name", csv_string=self.params.recommendation_name
        )
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

    def _init_managers(
        self,
    ) -> tuple[GoogleCloudRecommenderManager, GoogleCloudResourceManager]:
        recommender_manager = GoogleCloudRecommenderManager(
            api_root=self.params.api_root,
            verify_ssl=self.params.verify_ssl,
            user_service_account=self.params.user_service_account,
            organization_id=self.params.organization_id,
            project_id=self.params.project_id,
            quota_project_id=self.params.quota_project_id,
            workload_identity_email=self.params.workload_identity_email,
            siemplify_logger=self.logger,
        )

        resource_manager = GoogleCloudResourceManager(
            api_root=self.params.resource_manager_api_root,
            verify_ssl=self.params.verify_ssl,
            user_service_account=self.params.user_service_account,
            organization_id=self.params.organization_id,
            project_id=self.params.project_id,
            quota_project_id=self.params.quota_project_id,
            workload_identity_email=self.params.workload_identity_email,
            siemplify_logger=self.logger,
        )

        return recommender_manager, resource_manager

    def _extract_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=consts.PROVIDER_NAME,
            param_name="API Root",
            is_mandatory=True,
        )
        self.params.user_service_account = extract_configuration_param(
            self.soar_action,
            provider_name=consts.PROVIDER_NAME,
            param_name="User Service Account",
            is_mandatory=False,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.resource_manager_api_root = extract_configuration_param(
            self.soar_action,
            param_name="Resource Manager API Root",
            is_mandatory=True,
            provider_name=consts.PROVIDER_NAME,
        )
        self.params.organization_id = extract_configuration_param(
            self.soar_action,
            param_name="Organization ID",
            is_mandatory=False,
            provider_name=consts.PROVIDER_NAME,
        )
        self.params.project_id = extract_configuration_param(
            self.soar_action,
            param_name="Project ID",
            is_mandatory=False,
            provider_name=consts.PROVIDER_NAME,
        )
        self.params.quota_project_id = extract_configuration_param(
            self.soar_action,
            param_name="Quota Project ID",
            is_mandatory=False,
            provider_name=consts.PROVIDER_NAME,
        )
        self.params.workload_identity_email = extract_configuration_param(
            self.soar_action,
            param_name="Workload Identity Email",
            is_mandatory=False,
            provider_name=consts.PROVIDER_NAME,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=consts.PROVIDER_NAME,
            param_name="Verify SSL",
            is_mandatory=False,
            input_type=bool,
        )

        # Action parameters
        self.params.recommendation_name = extract_action_param(
            self.soar_action,
            param_name="Recommendation Name",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, manager: Any, _=None) -> None:
        recommender_manager, resource_manager = manager

        test_service_connectivity(
            self, consts.SERVICES.get("recommender"), recommender_manager
        )
        test_service_connectivity(
            self, consts.SERVICES.get("resource"), resource_manager
        )

        self.logger.info("Getting Get Recommendations")
        recommendations = string_to_multi_value(
            self.params.recommendation_name, only_unique=True
        )
        successful_recommendation = []
        failed_recommendations = []

        for recommendation_name in recommendations:
            try:
                action_result = recommender_manager.get_recommendation(
                    recommendation_name=recommendation_name
                )
                successful_recommendation.append(action_result.to_json())
                self.logger.info(
                    "Successfully get recommendation for " f"{recommendation_name}"
                )

            except GoogleCloudRecommenderStatusNotFoundError as error:
                failed_recommendations.append(recommendation_name)
                self.logger.error(
                    f'Get recommendation failed for "{recommendation_name}"'
                    f"\nReason: {error}"
                )

        if successful_recommendation:
            self.json_results = successful_recommendation

        if failed_recommendations:
            self.output_message += (
                "\nThe following recommendations were not found in the "
                "Google Cloud Recommender service:\n"
                f'{", ".join(failed_recommendations)}'
            )

        if not successful_recommendation:
            self.output_message = (
                "No recommendations were found in the"
                f" {consts.PROVIDER_NAME} service"
            )
            self.result_value = False


def main() -> None:
    GetRecommendation(consts.GET_RECOMMENDATION_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
