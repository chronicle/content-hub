from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.base_action import BaseProofPointPSAction
from ..core.constants import PING_ACTION_NAME

if TYPE_CHECKING:
    from typing import Never, NoReturn


class Ping(BaseProofPointPSAction):
    """Ping action to test connectivity."""

    def __init__(self) -> None:
        super().__init__(PING_ACTION_NAME)

    def _perform_action(self, _: Never) -> None:
        """Execute the connectivity test.

        Args:
            _: Never input.

        """
        self.api_client.test_connectivity()
        self.result_value = True
        self.output_message = "Connection Established"


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
