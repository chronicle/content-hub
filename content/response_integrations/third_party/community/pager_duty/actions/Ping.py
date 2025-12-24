from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action import Action
from TIPCommon.extraction import extract_configuration_param

from ..core.constants import INTEGRATION_NAME, SCRIPT_NAME_PING
from ..core.PagerDutyManager import PagerDutyManager

if TYPE_CHECKING:
    from typing import NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the PagerDuty API."
)
ERROR_MESSAGE: str = "Failed to connect to the PagerDuty API."


class Ping(Action):
    def __init__(self) -> None:
        super().__init__(SCRIPT_NAME_PING)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        self.api_key = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_NAME,
            param_name="api_key",
            is_mandatory=True,
        )

    def _init_api_clients(self):
        """Prepare API client"""
        return PagerDutyManager(self.api_key)

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
