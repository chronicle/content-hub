"""Get Anti-Phishing Exceptions action – retrieves AP exceptions by type, optionally by ID."""
from ..core.base_action import BaseAction
from ..core.constants import GET_AP_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anti-Phishing exceptions!"
ERROR_MESSAGE: str = "Failed getting Anti-Phishing exceptions!"


class GetAPExceptions(BaseAction):
    """Retrieve Anti-Phishing exceptions filtered by exception type.

    When *Exc ID* is provided the action fetches a single exception by that ID;
    otherwise it returns the full list for the given exception type
    (``whitelist`` or ``blacklist``).
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_AP_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract mandatory *Exception Type* and optional *Exc ID*."""
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
        """Fetch a single exception or the full list depending on whether *Exc ID* was supplied."""
        exception_type = self.params.exception_type
        if exc_id := self.params.exc_id:
            self.json_results = self.api_client.get_ap_exception(exception_type, exc_id)
        else:
            self.json_results = self.api_client.get_ap_exceptions(exception_type)


def main() -> None:
    GetAPExceptions().run()


if __name__ == "__main__":
    main()
