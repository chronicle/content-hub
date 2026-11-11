from __future__ import annotations

from TIPCommon.base.action import Action
from TIPCommon.base.utils import validate_manager
from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.base.action.consts import EXECUTION_STATE
from TIPCommon import validation
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from intezer.core import constants
from intezer.core import exceptions
from intezer.core.IntezerManager import IntezerManager


class SubmitAlert(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.error_output_message = "Error executing action 'Submit Alert'. "
        self.json_results = {}
        self.output_message = ""
        self.result_value = True
        self.execution_state = None

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
        self.params.source = extract_action_param(
            self.soar_action, param_name="Source", print_value=True, is_mandatory=True
        )
        self.params.raw_alert = extract_action_param(
            self.soar_action,
            param_name="Raw Alert",
            print_value=True,
            is_mandatory=True,
        )
        self.params.alert_mapping = extract_action_param(
            self.soar_action,
            param_name="Alert Mapping",
            print_value=True,
            is_mandatory=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)
        self.params.raw_alert = validator.validate_json(
            param_name="Raw Alert", json_string=self.params.raw_alert
        )

        self.params.alert_mapping = validator.validate_json(
            param_name="Alert Mapping", json_string=self.params.alert_mapping
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

        try:
            response = manager.submit_alert(
                alert_source=self.params.source,
                alert_json=self.params.raw_alert,
                alert_mapping=self.params.alert_mapping,
            )
            self.json_results = {"alert_id": response.alert_id}
            self.output_message = (
                "Successfully submitted details about "
                f"the following alert: {response.alert_id}"
            )
        except exceptions.IntezerManagerError as e:
            self.error_output_message = "Error executing action 'Submit Alert'. "
            raise exceptions.IntezerManagerError(e) from e

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
    SubmitAlert(constants.SUBMIT_ALERT_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
