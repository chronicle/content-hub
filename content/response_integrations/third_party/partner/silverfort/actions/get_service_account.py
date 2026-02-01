"""Get Service Account action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import GET_SERVICE_ACCOUNT_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully retrieved service account: {display_name} ({guid})"
ERROR_MESSAGE: str = "Failed to get service account information!"


class GetServiceAccount(SilverfortAction):
    """Action to get service account details from Silverfort."""

    def __init__(self) -> None:
        """Initialize the Get Service Account action."""
        super().__init__(GET_SERVICE_ACCOUNT_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.guid = extract_action_param(
            self.soar_action,
            param_name="Service Account GUID",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        """Perform the get service account action."""
        client = self._get_service_account_client()

        service_account = client.get_service_account(self.params.guid)

        # Set JSON result
        self.json_results = service_account.to_json()

        display_name = service_account.display_name or service_account.upn or self.params.guid
        self.output_message = SUCCESS_MESSAGE.format(
            display_name=display_name,
            guid=self.params.guid,
        )


def main() -> None:
    """Main entry point for the Get Service Account action."""
    GetServiceAccount().run()


if __name__ == "__main__":
    main()
