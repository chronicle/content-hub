from ..core.base_action import BaseAction
from ..core.constants import DELETE_AP_EXC_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully deleted Anti-Phishing exception!"
ERROR_MESSAGE: str = "Failed deleting Anti-Phishing exception!"


class DeleteAPException(BaseAction):

    def __init__(self) -> None:
        super().__init__(DELETE_AP_EXC_SCRIPT_NAME)
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
            is_mandatory=True,
            default_value=None,
        )

    def _perform_action(self, _=None) -> None:
        exception_type = self.params.exception_type
        exc_id = self.params.exc_id
        self.json_results = self.api_client.delete_ap_exception(exception_type=exception_type, exc_id=exc_id)


def main() -> None:
    DeleteAPException().run()


if __name__ == "__main__":
    main()
