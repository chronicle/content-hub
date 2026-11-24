from __future__ import annotations

import re

from TIPCommon.base.action import Action
from TIPCommon.base.action import DataTable
from TIPCommon.extraction import extract_action_param
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.transformation import construct_csv
from TIPCommon.transformation import string_to_multi_value
from TIPCommon.validation import ParameterValidator
from TIPCommon.utils import is_empty_string_or_none
from google_cloud_recommender.core import consts
from google_cloud_recommender.core.GoogleCloudRecommenderManager import GoogleCloudRecommenderManager
from google_cloud_recommender.core.GoogleCloudRecommenderManager import GoogleCloudResourceManager
from google_cloud_recommender.core.UtilsManager import test_service_connectivity


class ListRecommendations(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = (
            "Error executing action " f'"{consts.LIST_RECOMMENDATION_SCRIPT_NAME}."'
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)

        try:
            self.params.max_records_to_return = validator.validate_positive(
                param_name="Max Records To Return",
                value=self.params.max_records_to_return,
            )
        except Exception as err:
            self.result_value = False
            self.error_output_message = (
                "Error executing action "
                f'"{consts.LIST_RECOMMENDATION_SCRIPT_NAME}". '
                "Reason: Invalid value was provided for "
                f'"Max Records To Return": {self.params.max_records_to_return}.'
                " Positive number should be provided."
            )
            raise err from err

        validator.validate_ddl(
            param_name="Recommendation State",
            value=self.params.recommendation_state,
            ddl_values=consts.RECOMMENDATION_STATE_TYPE,
            case_sensitive=True,
        )

        validator.validate_ddl(
            param_name="Recommender Subtype",
            value=self.params.recommender_subtype,
            ddl_values=consts.RECOMMENDER_SUBTYPE,
            case_sensitive=True,
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
        self.params.recommendation_filter = extract_action_param(
            self.soar_action,
            param_name="Recommendation Filter",
            is_mandatory=False,
            print_value=True,
        )
        self.params.recommendation_location = extract_action_param(
            self.soar_action,
            param_name="Recommendation Location",
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
        self.params.recommendation_priority = extract_action_param(
            self.soar_action,
            param_name="Recommendation Priority",
            is_mandatory=False,
            default_value=consts.DEFAULT_PRIORITY,
            print_value=True,
        )
        self.params.recommender_subtype = extract_action_param(
            self.soar_action,
            param_name="Recommender Subtype",
            is_mandatory=False,
            default_value=consts.DEFAULT_SUBTYPE,
            print_value=True,
        )
        self.params.max_records_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Records To Return",
            is_mandatory=False,
            default_value=consts.MAX_COUNT_OF_RECORDS,
            print_value=True,
        )

    def _perform_action(
        self,
        managers: (
            tuple[GoogleCloudRecommenderManager, GoogleCloudResourceManager] | None
        ) = None,
        _=None,
    ) -> None:
        recommender_manager, resource_manager = managers

        test_service_connectivity(
            self, consts.SERVICES.get("recommender"), recommender_manager
        )
        test_service_connectivity(
            self, consts.SERVICES.get("resource"), resource_manager
        )

        self.logger.info("Getting List Recommendations")
        resource_name = None
        resource_match = re.search(
            consts.RESOURCE_REGEX_PATTERN, self.params.recommendation_filter or ""
        )
        if resource_match:
            resource_name = resource_match.group()

        action_result = recommender_manager.list_recommendations(
            resource_name=resource_name,
            recommendation_location=self.params.recommendation_location,
            recommendation_state=self.params.recommendation_state,
            recommendation_priority=string_to_multi_value(
                self.params.recommendation_priority
            ),
            recommender_subtype=self.params.recommender_subtype,
            limit=self.params.max_records_to_return,
        )
        list_recommendations = action_result.get_recommendations()
        if len(list_recommendations) > 0:
            self.output_message = (
                "\nSuccessfully found recommendations for "
                f"the provided criteria in {consts.PROVIDER_NAME}"
                " service"
            )
            if resource_name:
                self.logger.info(
                    f"Recommendation Filter is provided and "
                    f"successfully parsed to {resource_name}"
                )
                self.output_message += (
                    f"\nRecommendation Filter is provided and "
                    f"successfully parsed to {resource_name}"
                )
            else:
                self.logger.info(
                    "Recommendation Filter is not provided,"
                    " taking the Project ID from the configured "
                    "service account"
                )
                self.output_message += (
                    "\nRecommendation Filter is not provided,"
                    " taking the Project ID from the configured "
                    "service account"
                )

            self.logger.info("Adding records data to JSON results")
            self.json_results = [
                recommendation.to_json() for recommendation in list_recommendations
            ]
            self.data_tables.append(
                DataTable(
                    title=consts.TABLE_NAME,
                    data_table=construct_csv(
                        [
                            recommendation.to_csv()
                            for recommendation in list_recommendations
                        ]
                    ),
                )
            )

        else:
            self.output_message = (
                "No recommendations were found for the provided criteria"
                f" in {consts.PROVIDER_NAME} service"
            )
            self.result_value = False


def main() -> None:
    ListRecommendations(consts.LIST_RECOMMENDATION_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
