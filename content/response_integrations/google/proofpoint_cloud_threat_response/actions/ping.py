from __future__ import annotations

from typing import TYPE_CHECKING

from proofpoint_cloud_threat_response.core.base_action import ProofpointCloudThreatResponseAction
from proofpoint_cloud_threat_response.core.constants import PING_SCRIPT_NAME

if TYPE_CHECKING:
    from typing import Never, NoReturn


SUCCESS_MESSAGE: str = (
    "Successfully connected to the Proofpoint Cloud Threat Response server with the "
    "provided connection parameters!"
)
ERROR_MESSAGE: str = "Failed to connect to the Proofpoint Cloud Threat Response server!"


class Ping(ProofpointCloudThreatResponseAction):
    def __init__(self) -> None:
        super().__init__(PING_SCRIPT_NAME)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE

    def _perform_action(self, _: Never) -> None:
        self.api_client.test_connectivity()


def main() -> NoReturn:
    Ping().run()


if __name__ == "__main__":
    main()
