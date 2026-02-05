"""Change Policy State action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import CHANGE_POLICY_STATE_SCRIPT_NAME

SUCCESS_MESSAGE: str = "Successfully {action} policy: {policy_id}"
ERROR_MESSAGE: str = "Failed to change policy state!"


class ChangePolicyState(SilverfortAction):
    """Action to enable or disable a policy in Silverfort."""

    def __init__(self) -> None:
        """Initialize the Change Policy State action."""
        super().__init__(CHANGE_POLICY_STATE_SCRIPT_NAME)
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
        self.params.enabled = extract_action_param(
            self.soar_action,
            param_name="Enable Policy",
            is_mandatory=True,
            input_type=bool,
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        """Perform the change policy state action."""
        client = self._get_policy_client()

        client.change_policy_state(
            policy_id=self.params.policy_id,
            state=self.params.enabled,
        )

        action = "enabled" if self.params.enabled else "disabled"

        self.json_results = {
            "policy_id": self.params.policy_id,
            "enabled": self.params.enabled,
            "status": action,
        }

        self.output_message = SUCCESS_MESSAGE.format(
            action=action,
            policy_id=self.params.policy_id,
        )


def main() -> None:
    """Main entry point for the Change Policy State action."""
    ChangePolicyState().run()


if __name__ == "__main__":
    main()
