from __future__ import annotations

from ..core.base_action import BaseAction

SCRIPT_NAME = "Ping"


class Ping(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    def __init__(self, script_name: str) -> None:
        """Initialize the instance.

        Args:
            script_name: str value.
        """
        super().__init__(script_name)
        self.output_message = (
            f"Successfully connected to the {self.INTEGRATION_IDENTIFIER} server with the "
            "provided connection parameters!"
        )
        self.error_output_message = f"Failed to connect to the {self.INTEGRATION_IDENTIFIER} server! Error is {{error}}"
        self.json_results = {}

    def _perform_action(self, _=None) -> None:
        """Run an OpenCTI connectivity health check using the configured client.
        On success the action completes with the ping success message;
        on failure an exception propagates and the framework marks the action as failed.
        """
        self.api_client.health_check()


def main() -> None:
    """Action entry point."""
    Ping(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
