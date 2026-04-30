"""List Service Accounts action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import (
    DEFAULT_PAGE_NUMBER,
    DEFAULT_PAGE_SIZE,
    LIST_SERVICE_ACCOUNTS_SCRIPT_NAME,
    SA_INDEX_FIELDS,
)

SUCCESS_MESSAGE: str = "Successfully retrieved {count} service accounts (page {page})."
ERROR_MESSAGE: str = "Failed to list service accounts!"


class ListServiceAccounts(SilverfortAction):
    """Action to list service accounts from Silverfort."""

    def __init__(self) -> None:
        """Initialize the List Service Accounts action."""
        super().__init__(LIST_SERVICE_ACCOUNTS_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.page_size = extract_action_param(
            self.soar_action,
            param_name="Page Size",
            default_value=DEFAULT_PAGE_SIZE,
            input_type=int,
            print_value=True,
        )
        self.params.page_number = extract_action_param(
            self.soar_action,
            param_name="Page Number",
            default_value=DEFAULT_PAGE_NUMBER,
            input_type=int,
            print_value=True,
        )
        self.params.fields = extract_action_param(
            self.soar_action,
            param_name="Fields",
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        """Perform the list service accounts action."""
        client = self._get_service_account_client()

        # Parse fields if provided
        fields = None
        if self.params.fields:
            fields = [f.strip() for f in self.params.fields.split(",")]
            # Validate fields
            invalid_fields = [f for f in fields if f not in SA_INDEX_FIELDS]
            if invalid_fields:
                self.logger.warning(
                    f"Invalid fields specified (will be ignored): {invalid_fields}. "
                    f"Valid fields are: {SA_INDEX_FIELDS}"
                )
                fields = [f for f in fields if f in SA_INDEX_FIELDS]

        result = client.list_service_accounts(
            page_size=self.params.page_size,
            page_number=self.params.page_number,
            fields=fields,
        )

        # Set JSON result
        self.json_results = result.to_json()

        self.output_message = SUCCESS_MESSAGE.format(
            count=len(result.service_accounts),
            page=self.params.page_number,
        )


def main() -> None:
    """Main entry point for the List Service Accounts action."""
    ListServiceAccounts().run()


if __name__ == "__main__":
    main()
