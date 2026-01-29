from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import SampleAction
from ..core.constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the API Service server with the provided connection parameters!"
)
ERROR_MESSAGE: str = "Failed to connect to the API Service server!"


class Ping(SampleAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
