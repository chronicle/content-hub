from __future__ import annotations

from typing import NoReturn

from TIPCommon.base.action import Action
from core import action_init
from core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME
from core import MicrosoftGraphMailDelegatedManager as api_manager


SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {INTEGRATION_NAME} service with "
    "the provided connection parameters!"
)
ERROR_MESSAGE: str = f"Failed to connect to the {INTEGRATION_NAME} server!"


class Ping(Action):

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self.api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
