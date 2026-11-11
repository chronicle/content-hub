from __future__ import annotations

from TIPCommon import convert_list_to_comma_string
from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.validation import ParameterValidator
from intezer.core import constants
from intezer.core import exceptions
from intezer.core.IntezerManager import IntezerManager


class DetonateFile(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = ""
        self.json_results = {}
        self.output_message = ""
        self.result_value = True

    def _extract_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.api_key = extract_configuration_param(
            self.soar_action,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API key",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
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
        self.params.file_path = extract_action_param(
            self.soar_action,
            param_name="File Path",
            is_mandatory=True,
            print_value=True,
        )
        self.params.related_alert_id = extract_action_param(
            self.soar_action,
            param_name="Related Alert ID",
            is_mandatory=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        self.params.file_path = validator.validate_csv(
            param_name="File Path", csv_string=self.params.file_path
        )

        self.params.related_alert_id = validator.validate_csv(
            param_name="Related Alert ID", csv_string=self.params.related_alert_id
        )

    def _init_managers(self) -> IntezerManager:
        return IntezerManager(
            api_root=self.params.api_root,
            api_key=self.params.api_key,
            verify_ssl=self.params.verify_ssl,
            siemplify_logger=self.logger,
        )

    def _perform_action(self, manager: IntezerManager, _=None) -> None:

        self.logger.info("Validating manager is not None")
        validate_manager(manager)

        self.logger.info("Getting the detonate file details")
        self.output_message = ""
        result = []
        self.result_value = False
        valid_file_path = []
        invalid_file_path = []
        for file_path in set(self.params.file_path):
            try:
                response = manager.get_detonate_file(
                    file_path=file_path.strip(),
                    related_alert_ids=convert_list_to_comma_string(
                        self.params.related_alert_id
                    ),
                )
                valid_file_path.append(file_path)
                result.append(
                    {
                        "analysis_id": response.analysis_id,
                        "analysis_status": response.analysis_status,
                        "analysis_type": response.analysis_type,
                        "identifier": response.identifier,
                    }
                )
            except (exceptions.IntezerManagerError, exceptions.IntezerNotFoundError):
                invalid_file_path.append(file_path)

        self.json_results = result

        if valid_file_path:
            self.output_message = (
                "Successfully fetched the analysis ids for the following file paths: "
                f"{convert_list_to_comma_string(valid_file_path)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )
            self.result_value = True

        if invalid_file_path:
            self.output_message += (
                "Action wasn't able to fetch the analysis ids "
                f"for the following file paths: "
                f"{convert_list_to_comma_string(invalid_file_path)} "
                f"in {constants.INTEGRATION_NAME}\n"
            )


def main() -> None:
    DetonateFile(constants.DETONATE_FILE_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
