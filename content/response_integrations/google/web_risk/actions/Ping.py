from __future__ import annotations
from web_risk.core.WebRiskBaseAction import BaseAction
from web_risk.core.WebRiskConstants import PING_SCRIPT_NAME

SUCCESS_MESSAGE = (
    "Successfully connected to the Web Risk server with the provided connection "
    "parameters!"
)
ERROR_MESSAGE = "Failed to connect to the Web Risk server!"


class Ping(BaseAction):

    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
