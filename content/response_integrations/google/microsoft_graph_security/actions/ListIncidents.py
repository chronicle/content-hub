from __future__ import annotations

from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv
from TIPCommon.validation import ParameterValidator
from core import constants
from core.datamodels import Incident
from core.exceptions import (
    ActionParameterValidationError,
    MicrosoftGraphSecurityManagerError,
)
from core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


class ListIncidents(Action):
    def __init__(self) -> None:
        super().__init__(constants.LIST_INCIDENTS_SCRIPT_NAME)
        self.output_message = (
            "No incidents were found for the provided criteria in Microsoft Graph."
        )
        self.error_output_message = (
            f'Error executing action "{constants.LIST_INCIDENTS_SCRIPT_NAME}".'
        )
        self.filter_dict = None
        self.result_value = False
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client ID",
            is_mandatory=True,
        )
        self.params.secret_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Secret ID",
        )
        self.params.certificate_path = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Certificate Path",
        )
        self.params.certificate_password = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Certificate Password",
        )
        self.params.tenant = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Tenant",
            is_mandatory=True,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            default_value=False,
            print_value=True,
        )
        # Action parameters
        self.params.filter_key = extract_action_param(
            self.soar_action,
            param_name="Filter Key",
            is_mandatory=True,
            print_value=True,
        )
        self.params.filter_logic = extract_action_param(
            self.soar_action,
            param_name="Filter Logic",
            is_mandatory=True,
            print_value=True,
        )
        self.params.filter_value = extract_action_param(
            self.soar_action,
            param_name="Filter Value",
            print_value=True,
        )
        self.params.max_records_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Records To Return",
            input_type=int,
            default_value=constants.DEFAULT_MAX_RECORDS,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_lower_limit(
            param_name="Max Records To Return",
            value=self.params.max_records_to_return,
            limit=1,
        )
        self._validate_filter_params()

    def _validate_filter_params(self) -> None:
        if not self.params.filter_value:
            return

        self.filter_dict = {
            "key": (
                self.params.filter_key
                if self.params.filter_key != "Not Specified"
                else None
            ),
            "logic": (
                self.params.filter_logic
                if self.params.filter_logic != "Not Specified"
                else None
            ),
            "value": self.params.filter_value,
        }
        filter_params_invalid = any(self.filter_dict.values()) and not all(
            self.filter_dict.values()
        )
        if filter_params_invalid:
            raise ActionParameterValidationError(
                "you need to select a field from "
                'both the “Filter Key” and the "Filter Logic" parameter.'
            )

    def _init_api_clients(self) -> MicrosoftGraphSecurityManager:
        return MicrosoftGraphSecurityManager(
            client_id=self.params.client_id,
            client_secret=self.params.secret_id,
            certificate_path=self.params.certificate_path,
            certificate_password=self.params.certificate_password,
            tenant=self.params.tenant,
            verify_ssl=self.params.verify_ssl,
            siemplify=self.soar_action,
        )

    def _perform_action(self, _) -> None:
        try:
            incidents = self._api_client.list_incidents(
                filter_dict=self.filter_dict,
                max_incidents=self.params.max_records_to_return,
            )
            self._set_action_result(incidents)

        except MicrosoftGraphSecurityManagerError as e:
            if constants.CONTAINS_FILTER_NOT_SUPPORTED_ERROR in str(e).lower():
                raise ActionParameterValidationError(
                    "Contains filter is not supported for severity."
                ) from e

            raise e


    def _set_action_result(self, incidents: list[Incident]) -> None:
        if not incidents:
            return

        self.result_value = True
        self.json_results = [incident.to_json() for incident in incidents]
        table_result = construct_csv(
            [incident.to_table() for incident in incidents]
        )
        self.soar_action.result.add_data_table("Incidents", table_result)
        self.output_message = (
            f"Successfully found {len(incidents)} incidents for the provided "
            "criteria in Microsoft Graph."
        )


def main() -> NoReturn:
    ListIncidents().run()


if __name__ == "__main__":
    main()
