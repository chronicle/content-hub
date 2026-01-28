"""Get Policy action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import GET_POLICY_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully retrieved policy: {policy_name} (ID: {policy_id})"
ERROR_MESSAGE: str = "Failed to get policy information!"


class GetPolicy(SilverfortAction):
    """Action to get policy details from Silverfort."""

    def __init__(self) -> None:
        """Initialize the Get Policy action."""
        super().__init__(GET_POLICY_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.policy_id = extract_action_param(
            self.soar_action,
            param_name="Policy ID",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        """Perform the get policy action."""
        client = self._get_policy_client()

        policy = client.get_policy(self.params.policy_id)

        # Set JSON result
        self.json_results = policy.to_json()

        policy_name = policy.policy_name or f"Policy {self.params.policy_id}"
        self.output_message = SUCCESS_MESSAGE.format(
            policy_name=policy_name,
            policy_id=self.params.policy_id,
        )


def main() -> None:
    """Main entry point for the Get Policy action."""
    GetPolicy().run()


if __name__ == "__main__":
    main()
