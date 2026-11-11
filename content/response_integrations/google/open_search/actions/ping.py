from __future__ import annotations

from typing import TYPE_CHECKING
from open_search.core import constants
from open_search.core.base_action import BaseAction

if TYPE_CHECKING:
    from typing import Never, NoReturn


class Ping(BaseAction):
    def __init__(self):
        super().__init__(constants.PING_SCRIPT_NAME)

    def _perform_action(self, _: Never) -> None:
        self.api_client.test_connectivity()
        self.output_message: str = "Successfully connected to the OpenSearch server."
        self.result_value: bool = True


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
