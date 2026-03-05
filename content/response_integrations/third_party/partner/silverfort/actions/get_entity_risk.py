"""Get Entity Risk action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import GET_ENTITY_RISK_SCRIPT_NAME
from ..core.exceptions import SilverfortInvalidParameterError

SUCCESS_MESSAGE: str = "Successfully retrieved risk information for: {entity}"
ERROR_MESSAGE: str = "Failed to get entity risk information!"


class GetEntityRisk(SilverfortAction):
    """Action to get risk information for a user or resource."""

    def __init__(self) -> None:
        """Initialize the Get Entity Risk action."""
        super().__init__(GET_ENTITY_RISK_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.user_principal_name = extract_action_param(
            self.soar_action,
            param_name="User Principal Name",
            print_value=True,
        )
        self.params.resource_name = extract_action_param(
            self.soar_action,
            param_name="Resource Name",
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        if not self.params.user_principal_name and not self.params.resource_name:
            raise SilverfortInvalidParameterError(
                "Either 'User Principal Name' or 'Resource Name' must be provided."
            )

    def _perform_action(self, _=None) -> None:
        """Perform the get entity risk action."""
        client = self._get_risk_client()

        entity_risk = client.get_entity_risk(
            user_principal_name=self.params.user_principal_name,
            resource_name=self.params.resource_name,
        )

        # Set JSON result
        self.json_results = entity_risk.to_json()

        # Determine entity identifier for message
        entity = self.params.user_principal_name or self.params.resource_name
        self.output_message = SUCCESS_MESSAGE.format(entity=entity)


def main() -> None:
    """Main entry point for the Get Entity Risk action."""
    GetEntityRisk().run()


if __name__ == "__main__":
    main()
