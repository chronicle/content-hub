"""Ping action for Silverfort integration."""

from __future__ import annotations

from ..core.auth import get_configured_api_types
from ..core.base_action import SilverfortAction
from ..core.constants import PING_SCRIPT_NAME, ApiType
from ..core.exceptions import SilverfortError

SUCCESS_MESSAGE: str = "Successfully connected to Silverfort API with the provided credentials!"
PARTIAL_SUCCESS_MESSAGE: str = (
    "Successfully connected to Silverfort API. "
    "Connected APIs: {connected_apis}. "
    "Failed APIs: {failed_apis}."
)
NO_CREDENTIALS_MESSAGE: str = (
    "No API credentials configured. Please configure at least one set of API credentials "
    "(Risk, Service Accounts, or Policies) in the integration settings."
)
ERROR_MESSAGE: str = "Failed to connect to Silverfort API!"


class Ping(SilverfortAction):
    """Ping action to test connectivity to Silverfort API."""

    def __init__(self) -> None:
        """Initialize the Ping action."""
        super().__init__(PING_SCRIPT_NAME)
        self.output_message: str = SUCCESS_MESSAGE
        self.error_output_message: str = ERROR_MESSAGE

    def _perform_action(self, _=None) -> None:
        """Perform the ping action to test API connectivity."""
        params = self._get_integration_params()
        configured_apis = get_configured_api_types(params)

        if not configured_apis:
            raise SilverfortError(NO_CREDENTIALS_MESSAGE)

        connected_apis: list[str] = []
        failed_apis: list[str] = []

        for api_type in configured_apis:
            try:
                self._test_api_connectivity(api_type)
                connected_apis.append(api_type.value)
            except Exception as e:
                self.logger.error(f"Failed to connect to {api_type.value} API: {e}")
                failed_apis.append(api_type.value)

        if not connected_apis:
            raise SilverfortError(
                f"Failed to connect to any Silverfort API. Failed APIs: {', '.join(failed_apis)}"
            )

        if failed_apis:
            self.output_message = PARTIAL_SUCCESS_MESSAGE.format(
                connected_apis=", ".join(connected_apis),
                failed_apis=", ".join(failed_apis),
            )
        else:
            self.output_message = SUCCESS_MESSAGE + f" Connected APIs: {', '.join(connected_apis)}"

    def _test_api_connectivity(self, api_type: ApiType) -> bool:
        """Test connectivity to a specific API.

        Args:
            api_type: Type of API to test.

        Returns:
            True if connectivity test succeeds.
        """
        if api_type == ApiType.RISK:
            client = self._get_risk_client()
            return client.test_connectivity()
        elif api_type == ApiType.SERVICE_ACCOUNTS:
            client = self._get_service_account_client()
            return client.test_connectivity()
        elif api_type == ApiType.POLICIES:
            client = self._get_policy_client()
            return client.test_connectivity()
        return False


def main() -> None:
    """Main entry point for the Ping action."""
    Ping().run()


if __name__ == "__main__":
    main()
