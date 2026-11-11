from __future__ import annotations

from typing import Any

from TIPCommon.base.action import Action
from mandiant_managed_defense.core import api_utils
from mandiant_managed_defense.core import constants
from mandiant_managed_defense.core import AuthenticationManager as auth_manager
from mandiant_managed_defense.core import MandiantMDManager as api_manager


class Ping(Action):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully connected to the {constants.PROVIDER_NAME} server with the "
            f"provided connection parameters!"
        )
        self.error_output_message = (
            f"Failed to connect to the {constants.PROVIDER_NAME} server!"
        )

    def _extract_parameters(self) -> None:
        integration_params = api_utils.get_integration_params(self.soar_action)
        self.params.auth_params = integration_params.auth_params
        self.params.api_params = integration_params.api_params

    def _validate_params(self) -> None:
        pass

    def _init_managers(self) -> api_manager.ApiManager:
        session = auth_manager.get_authenticated_session(
            auth_params=self.params.auth_params
        )

        return api_manager.ApiManager(
            session=session,
            api_params=self.params.api_params,
            chronicle_soar=self._soar_action,
        )

    def _perform_action(self, manager: Any | None = None, _=None) -> None:
        manager.test_connectivity()


def main() -> None:
    Ping(constants.PING_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
