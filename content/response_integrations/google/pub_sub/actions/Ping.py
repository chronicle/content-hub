from __future__ import annotations

from pub_sub.core.PubSubBaseAction import BaseAction
from pub_sub.core.PubSubConstants import (
    PING_SCRIPT_NAME,
)

SUCCESS_MESSAGE = (
    "Successfully connected to the Pub/Sub server with the provided connection "
    "parameters!"
)
ERROR_MESSAGE = "Failed to connect to the Pub/Sub server!"


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
