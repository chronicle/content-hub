from __future__ import annotations

from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.base.action.consts import EXECUTION_STATE
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from intezer.core import constants
from intezer.core.exceptions import IntezerManagerError
from intezer.core.IntezerManager import IntezerManager


class SubmitSuspiciousEmail(Action):
    def __init__(
        self, script_name: str, integration_display_name: str, integration_name: str
    ) -> None:
        super().__init__(script_name)
        self.integration_display_name = integration_display_name
        self.integration_name = integration_name
        self.json_results = {}
        self.output_message = ""
        self.error_output_message = ""
        self.result_value = True
        self.execution_state = None

    def _extract_parameters(self) -> None:
        # Configuration Parameters
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=self.integration_name,
            param_name="API Root",
            is_mandatory=True,
            print_value=True,
        )
        self.params.api_key = extract_configuration_param(
            self.soar_action,
            provider_name=self.integration_name,
            param_name="API key",
            is_mandatory=True,
            print_value=False,
            remove_whitespaces=False,
        )
        self.params.verify_ssl = extract_configuration_param(
            self.soar_action,
            provider_name=self.integration_name,
            param_name="Verify SSL",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )
        # Action Paramters
        self.params.email_file_path = extract_action_param(
            self.soar_action,
            param_name="Email File Path",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        pass

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
        self.logger.info("Submitting suspicious email")

        try:
            response = manager.submit_suspicious_email(self.params.email_file_path)
            result_details = {"alert_id": response.alert_id}
        except IOError as e:
            self.error_output_message = (
                f'Error executing action "{constants.INTEGRATION_NAME}"'
            )
            raise IntezerManagerError(e) from e
        except IntezerManagerError as e:
            self.error_output_message = (
                f'Error executing action "{constants.INTEGRATION_NAME}"'
            )
            raise IntezerManagerError(e) from e

        self.result_value = True
        self.output_message = (
            "Successfully submitted suspicious email "
            f'"{self.params.email_file_path}" in '
            f"{self.integration_display_name}."
        )
        self.json_results = result_details

    def _finalize_action_on_failure(self, error: Exception) -> None:
        self.logger.error(f"{self.error_output_message}")
        self.result_value = False
        self.output_message = f"{self.error_output_message}\nReason: {error}"
        self.execution_state = ExecutionState.FAILED
        self.logger.info(f"Result Value: {self.result_value}")
        self.logger.info(f"Output Message: {self.output_message}")
        self.logger.info(
            f"Execution State: {self.execution_state} - "
            f"{EXECUTION_STATE[self.execution_state]}"
        )

        self.soar_action.end(
            message=self.output_message,
            result_value=self.result_value,
            execution_state=self.execution_state.value,
        )
        self.logger.info("\n-------------------- Main - Finished --------------------")


def main() -> None:
    SubmitSuspiciousEmail(
        constants.SUBMIT_SUSPICIOUS_EMAIL,
        constants.INTEGRATION_DISPLAY_NAME,
        constants.INTEGRATION_NAME,
    ).run()


if __name__ == "__main__":
    main()
