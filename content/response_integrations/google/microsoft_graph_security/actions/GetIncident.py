from __future__ import annotations

from typing import NoReturn

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import flat_dict_to_csv
from core import constants
from core.datamodels import Incident
from core.exceptions import IncidentNotFoundException, MicrosoftGraphSecurityManagerError
from core.MicrosoftGraphSecurityManager import MicrosoftGraphSecurityManager


class GetIncident(Action):
    def __init__(self) -> None:
        super().__init__(constants.GET_INCIDENT_SCRIPT_NAME)
        self.output_message = ""
        self.error_output_message = (
            f'Error executing action "{constants.GET_INCIDENT_SCRIPT_NAME}".'
        )
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
        self.params.incident_id = extract_action_param(
            self.soar_action,
            param_name="Incident ID",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        pass

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
            incident = self._api_client.get_incident(
                incident_id=self.params.incident_id
            )
            self._set_action_result(incident)

        except MicrosoftGraphSecurityManagerError as e:
            error_msg = str(e).lower()
            if "incident" in error_msg and "was not found" in error_msg:
                raise IncidentNotFoundException(
                    f"Incident with ID {self.params.incident_id} wasn't found in "
                    "Microsoft Graph. Please check the spelling."
                ) from e

            raise e

    def _set_action_result(self, incident: Incident) -> None:
        self.json_results = incident.to_json()
        table_result = flat_dict_to_csv(incident.to_table())
        self.soar_action.result.add_data_table(
            f"Incident {self.params.incident_id}", table_result
        )
        self.output_message = (
            "Successfully returned information about the incident "
            f"{self.params.incident_id}"
        )


def main() -> NoReturn:
    GetIncident().run()


if __name__ == "__main__":
    main()
