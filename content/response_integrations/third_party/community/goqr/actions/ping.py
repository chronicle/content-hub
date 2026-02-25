from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import GOQRBaseAction
from ..core.constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import Never, NoReturn


SUCCESS_MESSAGE: str = "Successfully connected to the QR Server API."
ERROR_MESSAGE: str = "Failed to connect to the QR Server API. Please check the API Root."


class Ping(GOQRBaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _: Never) -> None:
        self.api_client.ping()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
