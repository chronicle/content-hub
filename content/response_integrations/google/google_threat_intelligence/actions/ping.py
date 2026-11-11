from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


SUCCESS_MESSAGE = (
    f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server with the "
    "provided connection parameters!"
)
ERROR_MESSAGE = f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} server!"


class Ping(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.json_results = {}

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> None:
    Ping(PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
