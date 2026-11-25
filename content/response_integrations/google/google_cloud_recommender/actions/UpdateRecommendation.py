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
import re

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from ..core import consts
from ..core import exceptions
from ..core.GoogleCloudRecommenderManager import (
    GoogleCloudRecommenderManager,
    GoogleCloudResourceManager,
)
from ..core.UtilsManager import test_service_connectivity


class UpdateRecommendation(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.recommendations_result = {}
        self.failed_recommendation = []
        self.failed_update_recommendation = []
        self.successful_recommendation = []
        self.recommendation_not_updated = False
        self.output_message = ""
        self.error_output_message = (
            "Error executing action " f'"{consts.UPDATE_RECOMMENDATION_SCRIPT_NAME}."'
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        validator.validate_ddl(
            param_name="Recommendation State",
            value=self.params.recommendation_state,
            ddl_values=consts.UPDATE_RECOMMENDATION_STATE.keys(),
            case_sensitive=True,
        )

        validator.validate_ddl(
            param_name="Recommendation Result",
            value=self.params.recommendation_result,
            ddl_values=consts.UPDATE_RECOMMENDATION_RESULT.keys(),
            case_sensitive=True,
        )

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
        self.params.recommendation_state = extract_action_param(
            self.soar_action,
            param_name="Recommendation State",
            is_mandatory=False,
            default_value=consts.DEFAULT_STATE,
            print_value=True,
        )
        self.params.recommendation_result = extract_action_param(
            self.soar_action,
            param_name="Recommendation Result",
            is_mandatory=False,
            default_value=consts.DEFAULT_RESULT,
            print_value=True,
        )

    def _perform_action(self, manager: GoogleCloudRecommenderManager, _=None) -> None:
        recommender_manager, resource_manager = manager

        test_service_connectivity(
            self, consts.SERVICES.get("recommender"), recommender_manager
        )
        test_service_connectivity(
            self, consts.SERVICES.get("resource"), resource_manager
        )

        recommendations = string_to_multi_value(
            self.params.recommendation_name, only_unique=True
        )
        for recommendation_name in recommendations:
            if self.params.recommendation_state != consts.DEFAULT_STATE:
                self.update_recommendation(
                    manager=recommender_manager,
                    recommendation_name=recommendation_name,
                    recommendation_type=self.params.recommendation_state,
                )
            if self.params.recommendation_result != consts.DEFAULT_STATE:
                self.update_recommendation(
                    manager=recommender_manager,
                    recommendation_name=recommendation_name,
                    recommendation_type=self.params.recommendation_result,
                )

        if self.recommendations_result:
            self.json_results = list(self.recommendations_result.values())

        if (
            self.params.recommendation_result == consts.DEFAULT_STATE
            and self.params.recommendation_state == consts.DEFAULT_STATE
        ):
            raise exceptions.GoogleCloudRecommenderStateNoChangeError(
                (
                    "Action failed to run as neither new result "
                    "or new state was not specified"
                )
            )

        if self.successful_recommendation and not self.recommendation_not_updated:
            self.output_message = (
                "Successfully updated recommendation in the "
                f"{consts.PROVIDER_NAME} service"
            )

        if self.recommendation_not_updated and len(recommendations) == 1:
            recommendation, err = self.failed_update_recommendation[0]
            self.output_message = (
                f"The following recommendation {recommendation} was not updated"
                f" in the Google Cloud Recommender service due to error: {err}"
            )
            self.result_value = False

        elif self.recommendation_not_updated:

            failed_recommend_names = [
                elem[0] for elem in self.failed_update_recommendation
            ]
            success_recommend_wo_failed = any(
                elem not in failed_recommend_names
                for elem in self.successful_recommendation
            )

            self.result_value = True if success_recommend_wo_failed else False

            msg = ""
            grouped_error_data = defaultdict(list)

            for recommendation_name, err in self.failed_update_recommendation:
                grouped_error_data[err].append(recommendation_name)

            for err, recommendation_name in grouped_error_data.items():
                msg += f'{err}: {", ".join(recommendation_name)}\n'

            self.output_message += (
                "\nThe following recommendations were not updated in the "
                f"Google Cloud Recommender service:\n{msg.strip()}"
            )

        if self.failed_recommendation:
            self.output_message += (
                "\nThe following recommendations were not found in the "
                f"{consts.PROVIDER_NAME}:\n"
                f'{", ".join(set(self.failed_recommendation))}'
            )

        if not self.successful_recommendation and not self.recommendation_not_updated:
            self.result_value = False
            self.output_message = (
                "No recommendations were found in the "
                "Google Cloud Recommender service"
            )
        if not self.successful_recommendation and self.recommendation_not_updated:
            self.result_value = False

    def update_recommendation(
        self,
        manager: GoogleCloudRecommenderManager,
        recommendation_name: str,
        recommendation_type: str,
    ):
        etag = ""
        try:
            action_result = manager.get_recommendation(
                recommendation_name=recommendation_name
            )
            etag = action_result.etag
            self.logger.info(
                "Successfully get recommendation for " f"{recommendation_name}"
            )
        except exceptions.GoogleCloudRecommenderStatusNotFoundError as error:
            self.failed_recommendation.append(recommendation_name)
            self.logger.error(
                f'Get recommendation failed for "{recommendation_name}"\n'
                f"Reason: {error}"
            )

        try:
            if etag:
                recommendation_result = manager.update_recommendation(
                    recommendation_name=recommendation_name,
                    recommendation_type=consts.UPDATE_RECOMMENDATION_STATE.get(
                        recommendation_type,
                        consts.UPDATE_RECOMMENDATION_RESULT.get(recommendation_type),
                    ),
                    etag=etag,
                )
                self.successful_recommendation.append(recommendation_name)
                self.recommendations_result.update(
                    {recommendation_name: recommendation_result.to_json()}
                )
                self.logger.info(
                    "Recommendation updated successfully for " f"{recommendation_name}"
                )

        except Exception as err:
            self.recommendation_not_updated = True
            if "Invalid State transition" in str(err):
                error = re.search(r"Invalid.*", str(err)).group()
            self.failed_update_recommendation.append((recommendation_name, str(error)))
            self.logger.error(
                f'Update recommendation failed for "{recommendation_name}"\n'
                f"Reason: {err}"
            )


def main() -> None:
    UpdateRecommendation(consts.UPDATE_RECOMMENDATION_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
