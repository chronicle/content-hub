from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import HuntbaseAction
from ..core.constants import INTEGRATION_NAME, PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import NoReturn

SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {INTEGRATION_NAME} server with the provided connection parameters!"
)
ERROR_MESSAGE: str = f"Failed to connect to the {INTEGRATION_NAME} server!"


class Ping(HuntbaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _: object) -> None:
        self.manager.ping()


def main() -> NoReturn:
    """Run the action."""
    Ping().run()


if __name__ == "__main__":
    main()
