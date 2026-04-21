from ..core.base_action import BaseAction
from ..core.constants import GET_ANOMALY_EXCS_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully got Anomaly exceptions!"
ERROR_MESSAGE: str = "Failed getting Anomaly exceptions!"


class GetAnomalyExceptions(BaseAction):

    def __init__(self) -> None:
        super().__init__(GET_ANOMALY_EXCS_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.json_results = self.api_client.get_anomaly_exceptions()


def main() -> None:
    GetAnomalyExceptions().run()


if __name__ == "__main__":
    main()
