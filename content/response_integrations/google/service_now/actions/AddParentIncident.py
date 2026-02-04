from __future__ import annotations

from TIPCommon import validation
from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import convert_list_to_comma_string

from ..core import constants, exceptions
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


class AddParentIncident(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = "Error executing action 'Add Parent Incident'."
        self.json_results = {}
        self.output_message = ""
        self.result_value = False
        self.successful_incidents = []

    def _extract_action_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.username = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Username",
            is_mandatory=True,
            print_value=True,
        )
        self.params.password = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Password",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.incident_table = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Incident Table",
            print_value=True,
            default_value=DEFAULT_TABLE,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )
        self.params.client_id = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client ID",
            print_value=True,
        )
        self.params.client_secret = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client Secret",
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.refresh_token = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Refresh Token",
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.use_oauth = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Use Oauth Authentication",
            input_type=bool,
            print_value=True,
        )

        # Action Parameters
        self.params.parent_incident_number = extract_action_param(
            self.soar_action,
            param_name="Parent Incident Number",
            print_value=True,
            is_mandatory=True,
        )
        self.params.child_incident_numbers = extract_action_param(
            self.soar_action,
            param_name="Child Incident Numbers",
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        self.params.child_incident_numbers_list = validator.validate_csv(
            param_name="Child Incident Numbers",
            csv_string=self.params.child_incident_numbers,
        )

    def _init_api_clients(self) -> ServiceNowManager:
        return ServiceNowManager(
            api_root=self.params.api_root,
            username=self.params.username,
            password=self.params.password,
            default_incident_table=self.params.incident_table,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.logger,
            client_id=self.params.client_id,
            client_secret=self.params.client_secret,
            refresh_token=self.params.refresh_token,
            use_oauth=self.params.use_oauth,
        )

    def _perform_action(self, _) -> None:
        try:
            parent_incident = self.api_client.check_incidents([self.params.parent_incident_number])
        except exceptions.ServiceNowNotFoundException as e:
            self.logger.exception(e)
            raise exceptions.ServiceNowNotFoundException(
                f"Parent Incident {self.params.parent_incident_number} wasn't found "
                f"in ServiceNow. Please check the spelling."
            ) from e

        if parent_incident:
            try:
                child_incidents = self.api_client.check_incidents(
                    self.params.child_incident_numbers_list
                )
                found_child_incident_numbers = [incident.number for incident in child_incidents]
                not_found_incident_numbers = [
                    number
                    for number in self.params.child_incident_numbers_list
                    if number not in found_child_incident_numbers
                ]
                if not_found_incident_numbers:
                    raise exceptions.ServiceNowException(
                        f"The following child incidents weren't found in ServiceNow: "
                        f"{convert_list_to_comma_string(not_found_incident_numbers)}. "
                        f"Please check the spelling."
                    )

                for child_incident in child_incidents:
                    self.successful_incidents.append(
                        self.api_client.add_child_incident(
                            child_incident.sys_id, parent_incident[0].sys_id
                        )
                    )
            except exceptions.ServiceNowNotFoundException as e:
                self.logger.exception(e)
                raise exceptions.ServiceNowNotFoundException(
                    f"The following child incidents weren't found in "
                    f"ServiceNow: {self.params.child_incident_numbers}. "
                    f"Please check the spelling."
                ) from e

        self.json_results = {
            "result": [child_inc.to_json() for child_inc in self.successful_incidents]
        }
        self.output_message = (
            f"Successfully set {self.params.parent_incident_number} as the "
            f"'Parent Incident' for the following incidents in "
            f"ServiceNow: {self.params.child_incident_numbers}."
        )
        self.result_value = True


def main() -> None:
    AddParentIncident(constants.ADD_PARENT_INCIDENT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
