"""List Policies action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import LIST_POLICIES_SCRIPT_NAME, POLICY_INDEX_FIELDS

SUCCESS_MESSAGE: str = "Successfully retrieved {count} policies."
ERROR_MESSAGE: str = "Failed to list policies!"


class ListPolicies(SilverfortAction):
    """Action to list policies from Silverfort."""

    def __init__(self) -> None:
        """Initialize the List Policies action."""
        super().__init__(LIST_POLICIES_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.fields = extract_action_param(
            self.soar_action,
            param_name="Fields",
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        """Perform the list policies action."""
        client = self._get_policy_client()

        # Parse fields if provided
        fields = None
        if self.params.fields:
            fields = [f.strip() for f in self.params.fields.split(",")]
            # Validate fields
            invalid_fields = [f for f in fields if f not in POLICY_INDEX_FIELDS]
            if invalid_fields:
                self.logger.warning(
                    f"Invalid fields specified (will be ignored): {invalid_fields}. "
                    f"Valid fields are: {POLICY_INDEX_FIELDS}"
                )
                fields = [f for f in fields if f in POLICY_INDEX_FIELDS]

        result = client.list_policies(fields=fields)

        # Set JSON result
        self.json_results = result.to_json()

        self.output_message = SUCCESS_MESSAGE.format(count=len(result.policies))


def main() -> None:
    """Main entry point for the List Policies action."""
    ListPolicies().run()


if __name__ == "__main__":
    main()
