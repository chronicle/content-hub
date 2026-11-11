from __future__ import annotations

import google.auth.credentials
import google_auth_httplib2
import httplib2

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param

from TIPCommon.utils import is_empty_string_or_none
from TIPCommon.validation import ParameterValidator
from google_cloud_armor.core import api_utils
from google_cloud_armor.core import constants
from google_cloud_armor.core import datamodels
from google_cloud_armor.core import exceptions
from google_cloud_armor.core import UtilsManager
from google_cloud_armor.core import AuthenticationManager as auth_manager
from google_cloud_armor.core import GoogleCloudArmorManager as api_manager


class AddRuleToSecurityPolicy(Action):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = ""
        self.error_output_message = (
            "Error executing action "
            f'"{constants.ADD_RULE_TO_SECURITY_POLICY_SCRIPT_NAME}".'
        )
        self.result_value = True
        self.json_results = {}

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.session_auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params
        self.params.policy_name = extract_action_param(
            self.soar_action,
            param_name="Policy Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.region = extract_action_param(
            self.soar_action,
            param_name="Region",
            default_value=constants.DEFAULT_ENVIRONMENT,
            print_value=True,
        )
        self.params.rule_json = extract_action_param(
            self.soar_action,
            param_name="Rule JSON",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        api_utils.validate_configuration_params(
            soar_action=self.soar_action,
            auth_params=self.params.session_auth_params,
            api_params=self.params.api_params,
        )
        validator = ParameterValidator(self.soar_action)
        if not is_empty_string_or_none(self.params.rule_json):
            self.params.rule_json = validator.validate_json(
                param_name="Policy JSON",
                json_string=self.params.rule_json,
                print_value=False,
            )

    def _init_managers(self) -> api_manager.ApiManager:
        credentials = self._get_authentication_credentials()
        session = self._get_authenticated_session(credentials=credentials)
        return api_manager.ApiManager(
            session=session, api_parameters=self.params.api_params, logger=self.logger
        )

    def _get_authentication_credentials(self) -> google.auth.credentials.Credentials:
        return auth_manager.get_authentication_credentials_or_raise_error(
            session_parameters=self.params.session_auth_params
        )

    def _get_authenticated_session(
        self, credentials
    ) -> httplib2.Http | google_auth_httplib2.AuthorizedHttp:
        return auth_manager.get_authenticated_session(
            credentials=credentials,
            verify_ssl=self.params.session_auth_params.verify_ssl,
        )

    def _perform_action(self, manager: api_manager.ApiManager) -> None:
        policy_fingerprint = self._get_security_policy_fingerprint(manager=manager)
        self._update_policy_fingerprint(fingerprint=policy_fingerprint)
        manager.add_rule_to_security_policy(
            policy_name=self.params.policy_name,
            region=self.params.region,
            policy_json=self.params.rule_json,
        )
        policy_data = UtilsManager.SecurityPolicyData(
            policy_name=self.params.policy_name, region=self.params.region
        )
        security_policy = UtilsManager.get_security_policy(
            get_policy=manager.get_security_policy,
            logger=self.logger,
            policy_data=policy_data,
        )
        self.logger.info(
            f'Successfully retrieved security policy "{policy_data.policy_name}".'
        )
        self._set_action_result(security_policy)

    def _get_security_policy_fingerprint(
        self, manager: api_manager.ApiManager
    ) -> datamodels.ListSecurityPolicy:
        """Get the security policy fingerprint.

        This method retrieves the security policy associated with the provided region
        and policy name and returns its fingerprint.

        Args:
            manager (api_manager.ApiManager): The API Manager instance.

        Returns:
            ListSecurityPolicy: The fingerprint of the retrieved security policy.

        Raises:
            GoogleCloudArmorInvalidRegionError: If the provided region is invalid.
            GoogleCloudArmorStatusNotFoundError: If the provided policy name is invalid.
        """
        try:
            return manager.get_security_policy(
                region=self.params.region, security_policy=self.params.policy_name
            ).fingerprint

        except exceptions.GoogleCloudArmorInvalidRegionError as e:
            raise exceptions.GoogleCloudArmorInvalidRegionError(
                f'The provided region "{self.params.region}" is invalid'
            ) from e

        except exceptions.GoogleCloudArmorStatusNotFoundError as e:
            raise exceptions.GoogleCloudArmorStatusNotFoundError(
                f'The provided policy name "{self.params.policy_name}" is invalid'
            ) from e

    def _update_policy_fingerprint(self, fingerprint) -> None:
        self.params.rule_json["fingerprint"] = fingerprint

    def _set_action_result(self, policy: datamodels.CreateSecurityPolicy) -> None:
        self.json_results = policy.to_json()["raw_data"]
        self.output_message = "Successfully added a new rule to the security policy!"


def main():
    action = AddRuleToSecurityPolicy(constants.ADD_RULE_TO_SECURITY_POLICY_SCRIPT_NAME)
    action.run()


if __name__ == "__main__":
    main()
