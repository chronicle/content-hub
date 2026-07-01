from .base_action import BaseAction


class UpdateSectoolException(BaseAction):

    def __init__(
            self,
            name: str,
            output_message: str,
            error_output: str,
            sectool_name: str
    ) -> None:
        super().__init__(name)
        self.output_message: str = output_message
        self.error_output_message: str = error_output
        self.sectool_name: str = sectool_name

    def _extract_action_parameters(self) -> None:
        self.params.exception_type = self.soar_action.extract_action_param(
            param_name="Exception Type",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.exception_string = self.soar_action.extract_action_param(
            param_name="Exception String",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.comment = self.soar_action.extract_action_param(
            param_name="Comment",
            print_value=True,
            is_mandatory=False
        )
        self.params.exception_payload_condition = self.soar_action.extract_action_param(
            param_name="Exception Payload Condition",
            print_value=True,
            is_mandatory=False
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        exception_string = self.params.exception_string
        comment = self.params.comment
        exception_payload_condition = self.params.exception_payload_condition

        exception = {
            'exceptionType':exception_type,
            'exceptionStr':exception_string,
            'comment':comment
        }
        if exception_payload_condition:
            exception["exceptionPayload"] = {
                "condition": exception_payload_condition
            }
        self.json_results = self.api_client.update_sectool_exception(
            sectool=self.sectool_name,
            exception=exception
        )
