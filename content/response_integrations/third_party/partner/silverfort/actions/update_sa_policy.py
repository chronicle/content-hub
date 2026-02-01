"""Update Service Account Policy action for Silverfort integration."""

from __future__ import annotations

import json

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import UPDATE_SA_POLICY_SCRIPT_NAME, SAPolicyRiskLevel, SAProtocol
from ..core.data_models import AllowedEndpoint
from ..core.exceptions import SilverfortInvalidParameterError

SUCCESS_MESSAGE: str = "Successfully updated service account policy for GUID: {guid}"
ERROR_MESSAGE: str = "Failed to update service account policy!"


class UpdateSAPolicy(SilverfortAction):
    """Action to update service account policy in Silverfort."""

    def __init__(self) -> None:
        """Initialize the Update SA Policy action."""
        super().__init__(UPDATE_SA_POLICY_SCRIPT_NAME)
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
        self.params.enabled = extract_action_param(
            self.soar_action,
            param_name="Enabled",
            input_type=bool,
            print_value=True,
        )
        self.params.block = extract_action_param(
            self.soar_action,
            param_name="Block",
            input_type=bool,
            print_value=True,
        )
        self.params.send_to_siem = extract_action_param(
            self.soar_action,
            param_name="Send to SIEM",
            input_type=bool,
            print_value=True,
        )
        self.params.risk_level = extract_action_param(
            self.soar_action,
            param_name="Risk Level",
            print_value=True,
        )
        self.params.allow_all_sources = extract_action_param(
            self.soar_action,
            param_name="Allow All Sources",
            input_type=bool,
            print_value=True,
        )
        self.params.allow_all_destinations = extract_action_param(
            self.soar_action,
            param_name="Allow All Destinations",
            input_type=bool,
            print_value=True,
        )
        self.params.protocols = extract_action_param(
            self.soar_action,
            param_name="Protocols",
            print_value=True,
        )
        self.params.add_allowed_sources = extract_action_param(
            self.soar_action,
            param_name="Add Allowed Sources",
            print_value=True,
        )
        self.params.remove_allowed_sources = extract_action_param(
            self.soar_action,
            param_name="Remove Allowed Sources",
            print_value=True,
        )
        self.params.add_allowed_destinations = extract_action_param(
            self.soar_action,
            param_name="Add Allowed Destinations",
            print_value=True,
        )
        self.params.remove_allowed_destinations = extract_action_param(
            self.soar_action,
            param_name="Remove Allowed Destinations",
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        if self.params.risk_level:
            valid_levels = [level.value for level in SAPolicyRiskLevel]
            if self.params.risk_level.lower() not in valid_levels:
                raise SilverfortInvalidParameterError(
                    f"Invalid risk level: {self.params.risk_level}. "
                    f"Valid values are: {', '.join(valid_levels)}"
                )

        if self.params.protocols:
            protocols = [p.strip() for p in self.params.protocols.split(",")]
            valid_protocols = [p.value for p in SAProtocol]
            invalid = [p for p in protocols if p not in valid_protocols]
            if invalid:
                raise SilverfortInvalidParameterError(
                    f"Invalid protocols: {invalid}. Valid values are: {', '.join(valid_protocols)}"
                )

    def _parse_endpoints(self, endpoints_json: str | None) -> list[AllowedEndpoint] | None:
        """Parse JSON string of endpoints into AllowedEndpoint objects.

        Args:
            endpoints_json: JSON string like [{"key": "10.0.0.1", "key_type": "ip"}]

        Returns:
            List of AllowedEndpoint objects or None.
        """
        if not endpoints_json:
            return None

        try:
            endpoints_data = json.loads(endpoints_json)
            if not isinstance(endpoints_data, list):
                raise SilverfortInvalidParameterError(
                    "Endpoints must be a JSON array of objects with 'key' and 'key_type' fields."
                )
            return [
                AllowedEndpoint(key=ep["key"], key_type=ep["key_type"]) for ep in endpoints_data
            ]
        except json.JSONDecodeError as e:
            raise SilverfortInvalidParameterError(f"Invalid JSON for endpoints: {e}")
        except KeyError as e:
            raise SilverfortInvalidParameterError(
                f"Missing required field in endpoint: {e}. "
                "Each endpoint must have 'key' and 'key_type' fields."
            )

    def _perform_action(self, _=None) -> None:
        """Perform the update service account policy action."""
        client = self._get_service_account_client()

        # Parse protocols
        protocols = None
        if self.params.protocols:
            protocols = [p.strip() for p in self.params.protocols.split(",")]

        # Parse endpoints
        add_sources = self._parse_endpoints(self.params.add_allowed_sources)
        remove_sources = self._parse_endpoints(self.params.remove_allowed_sources)
        add_destinations = self._parse_endpoints(self.params.add_allowed_destinations)
        remove_destinations = self._parse_endpoints(self.params.remove_allowed_destinations)

        client.update_service_account_policy(
            guid=self.params.guid,
            enabled=self.params.enabled,
            block=self.params.block,
            send_to_siem=self.params.send_to_siem,
            risk_level=self.params.risk_level.lower() if self.params.risk_level else None,
            allow_all_sources=self.params.allow_all_sources,
            allow_all_destinations=self.params.allow_all_destinations,
            protocols=protocols,
            add_allowed_sources=add_sources,
            remove_allowed_sources=remove_sources,
            add_allowed_destinations=add_destinations,
            remove_allowed_destinations=remove_destinations,
        )

        self.json_results = {
            "guid": self.params.guid,
            "status": "updated",
        }

        self.output_message = SUCCESS_MESSAGE.format(guid=self.params.guid)


def main() -> None:
    """Main entry point for the Update SA Policy action."""
    UpdateSAPolicy().run()


if __name__ == "__main__":
    main()
