from __future__ import annotations

from ..core.base_action import RubrikAction, validate_uuid_param
from ..core.constants import STATUS_ENUM_MAP, UPDATE_VIOLATION_STATUS_SCRIPT_NAME
from ..core.rubrik_exceptions import InvalidValueException

VALID_STATUS_LABELS: list[str] = list(STATUS_ENUM_MAP.keys())


class UpdateViolationStatus(RubrikAction):
    graphql_error_prefix = "Failed to update violation status"

    def __init__(self) -> None:
        super().__init__(UPDATE_VIOLATION_STATUS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.violation_id = self._extract_string_param("Violation ID", is_mandatory=True)
        self.params.new_status_label = self._extract_string_param("New Status", is_mandatory=True)

    def _validate_params(self) -> None:
        self.params.violation_id = validate_uuid_param(self.params.violation_id, "Violation ID")
        self.params.new_status = validate_new_status(self.params.new_status_label)

    def _perform_action(self, _: object = None) -> None:
        violation_id: str = self.params.violation_id
        # bulkUpdatePolicyViolations is shared across DSPM and IR violation types —
        # RSC's mutation only cares about policyViolationIds + newPolicyViolationStatus,
        # so this single action works for a violation ID from either source.
        self.api_client.update_violation_status(
            violation_ids=[violation_id],
            new_status=self.params.new_status,
        )

        self.output_message = (
            f"Violation status updated to '{self.params.new_status_label}' "
            f"for violation ID: {violation_id}."
        )
        self.logger.info(self.output_message)


def validate_new_status(new_status_label: str | None) -> str:
    """Validate & map the New Status parameter per the Update Violation Status spec.

    Args:
        new_status_label: Raw New Status label, e.g. "In Progress".

    Returns:
        The matching RSC policy violation status enum value.

    Raises:
        InvalidValueException: With the exact wording required by the action's
            case wall output message contract.
    """
    if not new_status_label or not new_status_label.strip():
        raise InvalidValueException(f"New Status is required. Valid values: {VALID_STATUS_LABELS}")

    new_status_label = new_status_label.strip()
    if new_status_label not in STATUS_ENUM_MAP:
        raise InvalidValueException(
            f"Invalid value '{new_status_label}' for parameter 'New Status'. "
            f"Valid values: {VALID_STATUS_LABELS}"
        )

    return STATUS_ENUM_MAP[new_status_label]


def main() -> None:
    UpdateViolationStatus().run()


if __name__ == "__main__":
    main()
