from __future__ import annotations

from typing import NoReturn

from TIPCommon.base.action import Action
from google_forms.core import constants
from google_forms.core.action_init import create_api_client
from google_forms.core.GoogleFormsManager import GoogleFormsManager


SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {constants.INTEGRATION_NAME} server with "
    "the provided connection parameters!"
)
ERROR_MESSAGE: str = f"Failed to connect to the {constants.INTEGRATION_NAME} server!"


class Ping(Action):
    def __init__(self) -> None:
        super().__init__(constants.PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _init_api_clients(self) -> GoogleFormsManager:
        return create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self._api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
