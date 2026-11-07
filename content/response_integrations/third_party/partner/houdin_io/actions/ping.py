from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import HoudinAction
from ..core.houdin_constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from soar_sdk.SiemplifyDataModel import DomainEntityInfo

SUCCESS_MESSAGE: str = "Successfully connected to the Houdin-io server with the provided connection parameters!"
ERROR_MESSAGE: str = "Failed to connect to the Houdin-io server!"


class Ping(HoudinAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _: DomainEntityInfo | None = None) -> None:
        self.api_client.ping()


def main() -> None:
    Ping().run()


if __name__ == "__main__":
    main()
