from __future__ import annotations

from ..core.base_action import SignalSciencesAction
from ..core.constants import PING_SCRIPT_NAME


class PingAction(SignalSciencesAction):
    def __init__(self):
        super().__init__(PING_SCRIPT_NAME)

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        self.output_message = "Successfully connected."
        self.result_value = True


def main():
    PingAction().run()


if __name__ == "__main__":
    main()
