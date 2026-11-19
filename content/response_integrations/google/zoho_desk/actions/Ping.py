from __future__ import annotations

from typing import NoReturn

from TIPCommon.base.action import Action
from zoho_desk.core import action_init
from zoho_desk.core.ZohoDeskApiManager import ZohoDeskApiClient
from zoho_desk.core.constants import INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME


class Ping(Action[ZohoDeskApiClient]):

    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)

    def _init_api_clients(self) -> ZohoDeskApiClient:
        return action_init.create_api_client(self.soar_action)

    def _perform_action(self, _) -> None:
        self.logger.info("Testing connection")
        self.api_client.test_connection()
        self.logger.info("Finished Successfully")
        self.output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} server "
            "with the provided connection parameters!"
        )


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
