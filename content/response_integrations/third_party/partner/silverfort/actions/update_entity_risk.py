"""Update Entity Risk action for Silverfort integration."""

from __future__ import annotations

from TIPCommon.extraction import extract_action_param  # type: ignore[import-not-found]

from ..core.base_action import SilverfortAction
from ..core.constants import UPDATE_ENTITY_RISK_SCRIPT_NAME, RiskSeverity, RiskType
from ..core.data_models import RiskUpdate
from ..core.exceptions import SilverfortInvalidParameterError

SUCCESS_MESSAGE: str = "Successfully updated risk for: {user_principal_name}"
ERROR_MESSAGE: str = "Failed to update entity risk!"


class UpdateEntityRisk(SilverfortAction):
    """Action to update risk information for a user entity."""

    def __init__(self) -> None:
        """Initialize the Update Entity Risk action."""
        super().__init__(UPDATE_ENTITY_RISK_SCRIPT_NAME)
        self.output_message: str = ""
        self.error_output_message: str = ERROR_MESSAGE

    def _extract_action_parameters(self) -> None:
        """Extract action parameters."""
        self.params.user_principal_name = extract_action_param(
            self.soar_action,
            param_name="User Principal Name",
            is_mandatory=True,
            print_value=True,
        )
        self.params.risk_type = extract_action_param(
            self.soar_action,
            param_name="Risk Type",
            is_mandatory=True,
            print_value=True,
        )
        self.params.severity = extract_action_param(
            self.soar_action,
            param_name="Severity",
            is_mandatory=True,
            print_value=True,
        )
        self.params.valid_for = extract_action_param(
            self.soar_action,
            param_name="Valid For Hours",
            is_mandatory=True,
            input_type=int,
            print_value=True,
        )
        self.params.description = extract_action_param(
            self.soar_action,
            param_name="Description",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        """Validate action parameters."""
        # Validate risk type
        valid_risk_types = [rt.value for rt in RiskType]
        if self.params.risk_type.lower() not in valid_risk_types:
            raise SilverfortInvalidParameterError(
                f"Invalid risk type: {self.params.risk_type}. "
                f"Valid values are: {', '.join(valid_risk_types)}"
            )

        # Validate severity
        valid_severities = [s.value for s in RiskSeverity]
        if self.params.severity.lower() not in valid_severities:
            raise SilverfortInvalidParameterError(
                f"Invalid severity: {self.params.severity}. "
                f"Valid values are: {', '.join(valid_severities)}"
            )

        # Validate valid_for
        if self.params.valid_for <= 0:
            raise SilverfortInvalidParameterError("'Valid For Hours' must be a positive integer.")

    def _perform_action(self, _=None) -> None:
        """Perform the update entity risk action."""
        client = self._get_risk_client()

        risk_update = RiskUpdate(
            severity=self.params.severity.lower(),
            valid_for=self.params.valid_for,
            description=self.params.description,
        )

        risks = {self.params.risk_type.lower(): risk_update}

        client.update_entity_risk(
            user_principal_name=self.params.user_principal_name,
            risks=risks,
        )

        self.json_results = {
            "user_principal_name": self.params.user_principal_name,
            "risk_type": self.params.risk_type,
            "severity": self.params.severity,
            "valid_for": self.params.valid_for,
            "description": self.params.description,
            "status": "updated",
        }

        self.output_message = SUCCESS_MESSAGE.format(
            user_principal_name=self.params.user_principal_name
        )


def main() -> None:
    """Main entry point for the Update Entity Risk action."""
    UpdateEntityRisk().run()


if __name__ == "__main__":
    main()
