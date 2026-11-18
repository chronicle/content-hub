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

""" List service account roles actions script."""
from __future__ import annotations

from functools import reduce
from itertools import islice

from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon import validation
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.utils import is_empty_string_or_none
from ..core import constants
from ..core.exceptions import (
    GoogleCloudAssetInventoryError,
    InsufficientResourcePermissionError,
)
from ..core.GoogleCloudAssetInventoryManager import GoogleCloudAssetInventoryManager


class ListServiceAccountRoles(Action):
    """List Service Account Roles Action main class."""

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            f"Error executing action "
            f'"{constants.LIST_SERVICE_ACCOUNT_ROLES_SCRIPT_NAME}"'
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

        # Action Paramters
        self.params.service_accounts = extract_action_param(
            self.soar_action,
            param_name="Service Accounts",
            is_mandatory=True,
            print_value=True,
        )
        self.params.check_roles = extract_action_param(
            self.soar_action,
            param_name="Check Roles",
            is_mandatory=False,
            print_value=True,
        )
        self.params.check_permissions = extract_action_param(
            self.soar_action,
            param_name="Check Permissions",
            is_mandatory=False,
            print_value=True,
        )
        self.params.expand_permissions = extract_action_param(
            self.soar_action,
            param_name="Expand Permissions",
            is_mandatory=False,
            print_value=True,
            input_type=bool,
        )
        self.params.max_roles_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Roles To Return",
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_permissions_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Permissions To Return",
            is_mandatory=True,
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

        service_accounts = validator.validate_csv(
            param_name="Service Accounts", csv_string=self.params.service_accounts
        )

        self.params.service_accounts = [
            (
                service_account.split("/")[-1]
                if "/" in service_account
                else service_account
            )
            for service_account in service_accounts
        ]

        self.params.check_roles = validator.validate_csv(
            param_name="Check Roles", csv_string=self.params.check_roles
        )
        self.params.check_permissions = validator.validate_csv(
            param_name="Check Permissions", csv_string=self.params.check_permissions
        )
        self.params.max_roles_to_return = validator.validate_positive(
            param_name="Max Roles To Return", value=self.params.max_roles_to_return
        )
        self.params.max_permissions_to_return = validator.validate_positive(
            param_name="Max Permissions To Return",
            value=self.params.max_permissions_to_return,
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

        self.logger.info("Getting the information about the service accounts.")

        json_results = {}
        enriched_sa = []
        failed_sa = []

        for service_account in self.params.service_accounts:
            try:
                aqr_list = manager.analyze_iam_policy(
                    identity=service_account,
                    roles=self.params.check_roles,
                    permissions=self.params.check_permissions,
                    expand_roles=self.params.expand_permissions,
                )

            except InsufficientResourcePermissionError:
                raise

            except GoogleCloudAssetInventoryError as e:
                self.logger.error(
                    f"Failed to fetch roles for service account "
                    f"{service_account}. Reason: {e}"
                )
                failed_sa.append(service_account)
                continue

            unique_permissions = list(
                islice(
                    reduce(
                        lambda aqr1, aqr2: aqr1.union(aqr2),
                        map(lambda aqr: aqr.get_unique_permissions(), aqr_list),
                        set(),
                    ),
                    self.params.max_permissions_to_return,
                )
            )
            roles = [aqr.iam_binding_role for aqr in aqr_list][
                : self.params.max_roles_to_return
            ]

            if not (roles or unique_permissions):
                failed_sa.append(service_account)
                continue

            json_results[service_account] = {
                "roles": roles,
                "unique_permissions": unique_permissions,
            }
            enriched_sa.append(service_account)

        if enriched_sa:
            self.output_message = (
                f"Successfully enriched for the following services accounts"
                f" using information from {constants.INTEGRATION_DISPLAY_NAME}:"
                f' {",".join(enriched_sa)}'
            )

            if failed_sa:
                self.output_message += (
                    f"\n\nAction wasn’t able to enrich the following service"
                    f" accounts using information from"
                    f" {constants.INTEGRATION_DISPLAY_NAME}:"
                    f' {",".join(failed_sa)}'
                )
        else:
            self.output_message = "None of the service accounts were enriched."
            self.result_value = False
            return

        self.json_results = convert_dict_to_json_result_dict(json_results)


def main() -> None:
    ListServiceAccountRoles(constants.LIST_SERVICE_ACCOUNT_ROLES_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
