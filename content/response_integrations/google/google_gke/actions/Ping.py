from __future__ import annotations

from TIPCommon.base.utils import validate_manager

from google_gke.core.GKEBaseAction import GKEBaseAction
from google_gke.core.GKEConsts import INTEGRATION_IDENTIFIER, INTEGRATION_DISPLAY_NAME, PING_SCRIPT_NAME
from google_gke.core.GKEServices import GKEBaseService


class Ping(GKEBaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = (
            f"Successfully connected to the {INTEGRATION_DISPLAY_NAME} "
            f"service with the provided connection parameters!"
        )
        self.error_output_message = (
            f"Failed to connect to the {INTEGRATION_DISPLAY_NAME} service!"
        )

    def _validate_params(self) -> None:
        pass

    def _extract_action_params(self) -> None:
        pass

    def _perform_action(self, manager: GKEBaseService | None = None, _=None) -> None:
        self.logger.info("Validating manager is not None")
        validate_manager(manager)
        self.logger.info("Testing connectivity")
        manager.api_manager.test_connectivity()
        self.logger.info(
            f"Successfully connected to {INTEGRATION_DISPLAY_NAME} service!"
        )


def main() -> None:
    Ping(f"{INTEGRATION_IDENTIFIER} - {PING_SCRIPT_NAME}").run()


if __name__ == "__main__":
    main()
