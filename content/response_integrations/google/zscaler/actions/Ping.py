from __future__ import annotations

from zscaler.core.base_action import ZscalerBaseAction
from zscaler.core.constants import PING_SCRIPT_NAME
from zscaler.core.exceptions import ZscalerManagerError


class PingAction(ZscalerBaseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = "Connection Established"
        self.result_value: bool = False

    def _perform_action(self, _=None) -> None:
        """Perform the ping action."""
        try:
            self.api_client.test_connectivity()
            self.result_value = True
        except Exception as error:
            raise ZscalerManagerError(
                f"Failed to connect to the Zscaler server! {error}"
            ) from error


def main() -> None:
    PingAction().run()


if __name__ == "__main__":
    main()
