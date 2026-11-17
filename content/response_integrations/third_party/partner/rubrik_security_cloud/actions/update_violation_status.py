from __future__ import annotations

from ..core.base_action import RubrikAction, validate_uuid_param
from ..core.constants import UPDATE_VIOLATION_STATUS_SCRIPT_NAME
from ..core.validators import validate_new_status


class UpdateViolationStatus(RubrikAction):
    """Update the status of a DSPM or IR violation in Rubrik Security Cloud."""

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


def main() -> None:
    UpdateViolationStatus().run()


if __name__ == "__main__":
    main()
