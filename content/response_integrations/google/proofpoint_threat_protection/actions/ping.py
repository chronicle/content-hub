from __future__ import annotations

from typing import TYPE_CHECKING

from proofpoint_threat_protection.core.base_action import ProofpointThreatProtectionAction
from proofpoint_threat_protection.core.constants import (
    PING_SCRIPT_NAME,
    INVALID_ID_STATUS_CODE,
)
from proofpoint_threat_protection.core.exceptions import ProofpointTPError


if TYPE_CHECKING:
    from typing import Never, NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the Proofpoint Threat Protection "
    "server with the provided connection parameters!"
)
ERROR_MESSAGE: str = "Failed to connect to the Proofpoint Threat Protection server!"


class Ping(ProofpointThreatProtectionAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _: Never) -> None:
        try:
            self.api_client.test_connectivity()
        except ProofpointTPError as e:
            if str(INVALID_ID_STATUS_CODE) in str(e):
                raise ProofpointTPError(
                    "invalid cluster ID provided or "
                    "credentials in the integration configuration."
                ) from e
            raise


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
