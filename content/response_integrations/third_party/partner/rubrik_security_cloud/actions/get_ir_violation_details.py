from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import DataTable
from TIPCommon.transformation import construct_csv

from ..core.base_action import RubrikAction, validate_uuid_param
from ..core.constants import GET_IR_VIOLATION_DETAILS_SCRIPT_NAME
from ..core.validators import map_ir_policy_types
from ..core.violation_datamodels import IRViolationDetails

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GetIRViolationDetails(RubrikAction):
    """Retrieve the details of a single IR violation by its ID."""

    graphql_error_prefix = "API error during Get IR Violation Details"

    def __init__(self) -> None:
        super().__init__(GET_IR_VIOLATION_DETAILS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.violation_id = self._extract_string_param("Violation ID", is_mandatory=True)
        # Non-mandatory so an unselected value falls back to the default policy types.
        self.params.policy_types = self._extract_string_param("Policy Types")

    def _validate_params(self) -> None:
        self.params.policy_types = map_ir_policy_types(self.params.policy_types)
        self.params.violation_id = validate_uuid_param(self.params.violation_id, "Violation ID")

    def _perform_action(self, _: object = None) -> None:
        violation_id: str = self.params.violation_id
        data: SingleJson = self.api_client.get_ir_violation_details(
            violation_id, self.params.policy_types
        )
        self.json_results = [data]
        details_model = IRViolationDetails(data.get("policyViolation", {}))

        self.data_tables.append(
            DataTable(
                title="IR Violation Details",
                data_table=construct_csv([details_model.to_csv()]),
            )
        )
        self._add_remediation_comment(details_model.manual_remediation)

        self.output_message = (
            f"Successfully retrieved IR violation details for ID: {violation_id}. "
            f"Identity: {details_model.display_name or 'N/A'} "
            f"({details_model.user_principal_name or 'N/A'})."
        )
        # The identity (display name / UPN) stays in the case wall message only;
        # the log line omits it so no PII is written to the logs.
        self.logger.info(f"Successfully retrieved IR violation details for ID: {violation_id}.")

    def _add_remediation_comment(self, manual_remediation: str | None) -> None:
        """Add the RSC manual remediation guidance to the case wall, if any."""
        if not manual_remediation:
            return
        self.soar_action.add_comment(f"RSC IR Remediation Guidance:\n{manual_remediation}")
        self.logger.info("Added manual remediation process as case comment.")


def main() -> None:
    GetIRViolationDetails().run()


if __name__ == "__main__":
    main()
