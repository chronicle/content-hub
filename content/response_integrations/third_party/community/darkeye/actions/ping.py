from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import DarkEyeAction
from ..core.constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the DarkEye server with the provided connection parameters! Checked: {}."
)
ERROR_MESSAGE: str = "Failed to connect to the DarkEye server!"


class Ping(DarkEyeAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        self.output_message = SUCCESS_MESSAGE.format(", ".join(self.api_client.products))


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
