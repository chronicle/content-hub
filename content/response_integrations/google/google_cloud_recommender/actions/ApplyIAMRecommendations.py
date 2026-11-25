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
from typing import Any
from ..core import consts
from ..core.exceptions import GoogleCloudRecommenderError
from ..core.exceptions import GoogleCloudRecommenderPermissionsDeniedError
from ..core.GoogleCloudRecommenderManager import GoogleCloudRecommenderManager
from ..core.GoogleCloudRecommenderManager import GoogleCloudResourceManager
from TIPCommon import extract_action_param
from TIPCommon import extract_configuration_param
from TIPCommon.base.action import Action
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from ..core.UtilsManager import test_service_connectivity


class ApplyIAMRecommendations(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            "Error executing action " f'"{consts.APPLY_IAM_RECOMMENDATIONS}."'
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        iam_recommendations_json = validator.validate_json(
            param_name="IAM Recommendations JSON",
            json_string=self.params.iam_recommendations_json,
        )
        if isinstance(iam_recommendations_json, dict):
            iam_recommendations_json = [iam_recommendations_json]
        self.params.iam_recommendations_json = iam_recommendations_json

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

    def _extract_parameters(self):
        # Extract Integration params
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            param_name="API Root",
            is_mandatory=True,
            provider_name=consts.PROVIDER_NAME,
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
            param_name="Verify SSL",
            input_type=bool,
            provider_name=consts.PROVIDER_NAME,
            default_value=True,
        )
        self.params.user_service_account = extract_configuration_param(
            self.soar_action,
            param_name="User Service Account",
            is_mandatory=False,
            provider_name=consts.PROVIDER_NAME,
            remove_whitespaces=False,
            print_value=False,
        )

        # Extract Action params
        self.params.iam_recommendations_json = extract_action_param(
            self.soar_action, is_mandatory=True, param_name="IAM Recommendations JSON"
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

    def _perform_action(
        self,
        managers: (
            tuple[GoogleCloudRecommenderManager, GoogleCloudResourceManager] | None
        ) = None,
        current_entity: Any | None = None,
    ) -> None:
        recommender_manager, resource_manager = managers

        test_service_connectivity(
            self, consts.SERVICES.get("recommender"), recommender_manager
        )
        test_service_connectivity(
            self, consts.SERVICES.get("resource"), resource_manager
        )

        recommendations = recommender_manager.parse_recommendations(
            self.params.iam_recommendations_json
        )

        recommendations_by_resource = defaultdict(list)
        a_recommendations = []
        f_recommendations = []

        # Map recommendations per rec_resource
        for recommendation in recommendations:
            (
                recommendations_by_resource[recommendation.rec_resource].append(
                    recommendation
                )
            )

        for ov_resource, _recs in recommendations_by_resource.items():
            try:
                policy = resource_manager.get_current_policy(resource_name=ov_resource)

                success_status = policy.update_policy_with_recommendations(
                    _recs, self.logger
                )

                if not any(success_status):
                    f_recommendations.extend(_recs)
                    continue

                self.logger.info("Updating the policy")
                resource_manager.update_policy(
                    resource_name=ov_resource, new_policy=policy.to_json()
                )

                self.logger.info("Updating the recommendations statuses")
                _a_recs, _f_recs = (
                    recommender_manager.update_recommendation_status_after_apply(
                        recommendations=_recs, success_status=success_status
                    )
                )

                a_recommendations.extend(_a_recs)
                f_recommendations.extend(_f_recs)

            except GoogleCloudRecommenderPermissionsDeniedError as e:
                _message = (
                    f"Got a permissions denied error accessing the following "
                    f"resource - {ov_resource}, error is - {e}"
                )
                self.logger.info(_message)
                self.output_message += _message
                self.logger.exception(e)
                f_recommendations.extend(_recs)

            except GoogleCloudRecommenderError as e:
                _message = (
                    f"Failed to apply recommendations on the following "
                    f"resource - {ov_resource}, error is - {e}"
                )
                self.logger.info(_message)
                self.logger.exception(e)
                f_recommendations.extend(_recs)

        # Generate action output and result
        if a_recommendations:
            self.result_value = True
            if f_recommendations:
                self.output_message += (
                    "\nSuccessfully applied provided IAM recommendation, "
                    "but some of the recommendations were not applied."
                )
            else:
                self.output_message += (
                    "\nSuccessfully applied provided IAM recommendations."
                )
        else:
            self.result_value = False
            self.output_message += "\nNo provided IAM recommendations were applied"

        self.json_results = {
            "applied_recommendations": [r.to_json() for r in a_recommendations],
            "failed_recommendations": [r.to_json() for r in f_recommendations],
        }


def main() -> None:
    ApplyIAMRecommendations(consts.APPLY_IAM_RECOMMENDATIONS).run()


if __name__ == "__main__":
    main()
