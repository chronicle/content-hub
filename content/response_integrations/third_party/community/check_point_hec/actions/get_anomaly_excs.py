"""Get Anomaly Exceptions action – retrieves all anomaly detection exception rules."""
from ..core.base_action import BaseAction
from ..core.constants import GET_ANOMALY_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anomaly exceptions!"
ERROR_MESSAGE: str = "Failed getting Anomaly exceptions!"


class GetAnomalyExceptions(BaseAction):
    """Retrieve the list of all current anomaly detection exceptions.

    Takes no additional parameters.  The full exception list is stored in
    ``json_results``.
    """

    def __init__(self) -> None:
        """Initialise the action with its script name and output messages."""
        super().__init__(GET_ANOMALY_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Call the anomaly exceptions endpoint and store the results."""
        self.json_results = self.api_client.get_anomaly_exceptions()


def main() -> None:
    GetAnomalyExceptions().run()


if __name__ == "__main__":
    main()
