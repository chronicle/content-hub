"""Update Policy action for Silverfort integration."""

from __future__ import annotations

import json

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import UPDATE_POLICY_SCRIPT_NAME
from ..core.data_models import PolicyDestination, PolicyIdentifier
from ..core.exceptions import SilverfortInvalidParameterError

SUCCESS_MESSAGE: str = "Successfully updated policy: {policy_id}"
ERROR_MESSAGE: str = "Failed to update policy!"


class UpdatePolicy(SilverfortAction):
    """Action to update an authentication policy in Silverfort."""

    def __init__(self) -> None:
        """Initialize the Update Policy action."""
        super().__init__(UPDATE_POLICY_SCRIPT_NAME)
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
            param_name="Enabled",
            input_type=bool,
            print_value=True,
        )
        self.params.add_users_and_groups = extract_action_param(
            self.soar_action,
            param_name="Add Users and Groups",
            print_value=True,
        )
        self.params.remove_users_and_groups = extract_action_param(
            self.soar_action,
            param_name="Remove Users and Groups",
            print_value=True,
        )
        self.params.add_sources = extract_action_param(
            self.soar_action,
            param_name="Add Sources",
            print_value=True,
        )
        self.params.remove_sources = extract_action_param(
            self.soar_action,
            param_name="Remove Sources",
            print_value=True,
        )
        self.params.add_destinations = extract_action_param(
            self.soar_action,
            param_name="Add Destinations",
            print_value=True,
        )
        self.params.remove_destinations = extract_action_param(
            self.soar_action,
            param_name="Remove Destinations",
            print_value=True,
        )

    def _parse_identifiers(self, identifiers_json: str | None) -> list[PolicyIdentifier] | None:
        """Parse JSON string of identifiers into PolicyIdentifier objects.

        Args:
            identifiers_json: JSON string of identifiers.

        Returns:
            List of PolicyIdentifier objects or None.
        """
        if not identifiers_json:
            return None

        try:
            identifiers_data = json.loads(identifiers_json)
            if not isinstance(identifiers_data, list):
                raise SilverfortInvalidParameterError(
                    "Identifiers must be a JSON array of objects."
                )
            return [PolicyIdentifier.from_json(i) for i in identifiers_data]
        except json.JSONDecodeError as e:
            raise SilverfortInvalidParameterError(f"Invalid JSON for identifiers: {e}")

    def _parse_destinations(self, destinations_json: str | None) -> list[PolicyDestination] | None:
        """Parse JSON string of destinations into PolicyDestination objects.

        Args:
            destinations_json: JSON string of destinations.

        Returns:
            List of PolicyDestination objects or None.
        """
        if not destinations_json:
            return None

        try:
            destinations_data = json.loads(destinations_json)
            if not isinstance(destinations_data, list):
                raise SilverfortInvalidParameterError(
                    "Destinations must be a JSON array of objects."
                )
            return [PolicyDestination.from_json(d) for d in destinations_data]
        except json.JSONDecodeError as e:
            raise SilverfortInvalidParameterError(f"Invalid JSON for destinations: {e}")

    def _perform_action(self, _=None) -> None:
        """Perform the update policy action."""
        client = self._get_policy_client()

        add_users_groups = self._parse_identifiers(self.params.add_users_and_groups)
        remove_users_groups = self._parse_identifiers(self.params.remove_users_and_groups)
        add_sources = self._parse_identifiers(self.params.add_sources)
        remove_sources = self._parse_identifiers(self.params.remove_sources)
        add_destinations = self._parse_destinations(self.params.add_destinations)
        remove_destinations = self._parse_destinations(self.params.remove_destinations)

        client.update_policy(
            policy_id=self.params.policy_id,
            enabled=self.params.enabled,
            add_users_and_groups=add_users_groups,
            remove_users_and_groups=remove_users_groups,
            add_sources=add_sources,
            remove_sources=remove_sources,
            add_destinations=add_destinations,
            remove_destinations=remove_destinations,
        )

        self.json_results = {
            "policy_id": self.params.policy_id,
            "status": "updated",
        }

        self.output_message = SUCCESS_MESSAGE.format(policy_id=self.params.policy_id)


def main() -> None:
    """Main entry point for the Update Policy action."""
    UpdatePolicy().run()


if __name__ == "__main__":
    main()
