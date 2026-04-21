from ..core.base_action import BaseAction
from ..core.constants import GET_AP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anti-Phishing exceptions!"
ERROR_MESSAGE: str = "Failed getting Anti-Phishing exceptions!"


class GetAPExceptions(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_AP_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.params.exception_type = self.soar_action.extract_action_param(
            param_name="Exception Type",
            print_value=True,
            is_mandatory=True,
            default_value=None,
        )
        self.params.exc_id = self.soar_action.extract_action_param(
            param_name="Exc ID",
            print_value=True,
            is_mandatory=False
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        if exc_id := self.params.exc_id:
            self.json_results = self.api_client.get_ap_exception(exception_type, exc_id)
        else:
            self.json_results = self.api_client.get_ap_exceptions(exception_type)


def main() -> None:
    GetAPExceptions().run()


if __name__ == "__main__":
    main()
