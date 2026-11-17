from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import DataTable
from TIPCommon.transformation import construct_csv

from ..core.base_action import RubrikAction, validate_uuid_param
from ..core.constants import GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME
from ..core.violation_datamodels import DSPMViolationDetails

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class GetDSPMViolationDetails(RubrikAction):
    """Retrieve the details of a single DSPM violation by its ID."""

    graphql_error_prefix = "API error during Get DSPM Violation Details"

    def __init__(self) -> None:
        super().__init__(GET_DSPM_VIOLATION_DETAILS_SCRIPT_NAME)

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.violation_id = self._extract_string_param("Violation ID", is_mandatory=True)

    def _validate_params(self) -> None:
        self.params.violation_id = validate_uuid_param(self.params.violation_id, "Violation ID")

    def _perform_action(self, _: object = None) -> None:
        violation_id: str = self.params.violation_id
        data: SingleJson = self.api_client.get_dspm_violation_details(violation_id)
        self.json_results = [data]
        details_model = DSPMViolationDetails(data.get("policyViolation", {}))

        self.data_tables.append(
            DataTable(
                title="DSPM Violation Details",
                data_table=construct_csv([details_model.to_csv()]),
            )
        )
        self.output_message = (
            f"Successfully retrieved DSPM violation details for ID: {violation_id}. "
            f"Snapshot ID: {details_model.snapshot_id}. "
            f"Platform: {details_model.platform}. "
            f"Object Type: {details_model.object_type}."
        )


def main() -> None:
    GetDSPMViolationDetails().run()


if __name__ == "__main__":
    main()
