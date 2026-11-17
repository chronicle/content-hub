from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import DataTable
from TIPCommon.transformation import construct_csv

from ..core.base_action import RubrikAction, validate_uuid_param
from ..core.constants import (
    DEFAULT_FILE_LIST_MAX_RESULTS,
    ERROR_CREATION_DATE_ORDER,
    ERROR_LAST_ACCESS_DATE_ORDER,
    ERROR_LAST_SCAN_DATE_ORDER,
    ERROR_LAST_UPDATED_DATE_ORDER,
    GET_VIOLATION_FILE_LIST_SCRIPT_NAME,
    MAX_FILES,
    MAX_TABLE_RECORDS,
)
from ..core.validators import (
    parse_connection,
    parse_file_access_via_param,
    parse_file_exposure_param,
    parse_file_risk_level_param,
    parse_file_sort_by_param,
    parse_sort_order_param,
    validate_date_ranges,
    validate_max_results,
    validate_optional_uuid,
)
from ..core.violation_datamodels import FileEntry
from ..core.violations_api import Page, SortSpec, ViolationFileListFilter

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

# (start parameter, end parameter, error when end is not after start), in the order of
# ViolationFileListFilter's last_access / last_updated / creation / last_scan fields.
DATE_RANGE_PARAMS: tuple[tuple[str, str, str], ...] = (
    ("Last Access Start Date", "Last Access End Date", ERROR_LAST_ACCESS_DATE_ORDER),
    ("Last Updated Start Date", "Last Updated End Date", ERROR_LAST_UPDATED_DATE_ORDER),
    ("Creation Start Date", "Creation End Date", ERROR_CREATION_DATE_ORDER),
    ("Last Scan Start Date", "Last Scan End Date", ERROR_LAST_SCAN_DATE_ORDER),
)
DEFAULT_SORT_BY: str = "HITS"
DEFAULT_SORT_ORDER: str = "DESC"
TABLE_TITLE: str = "Violation Files"
NO_RESULTS_MESSAGE: str = "No files found matching the applied filters."
SHA1_NOTE: str = (
    "Note: SHA1 hash is not returned by this action. For NTFS quarantine "
    "flows, SHA1 must be resolved via Defender ATP Advanced Hunting query."
)


class GetViolationFileList(RubrikAction):
    """Retrieve a paginated list of files involved in a DSPM violation."""

    graphql_error_prefix = "API error during Get Violation File List"

    def __init__(self) -> None:
        super().__init__(GET_VIOLATION_FILE_LIST_SCRIPT_NAME)
        self.json_results: list[SingleJson] = []

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.object_id = self._extract_string_param("Object ID", is_mandatory=True)
        self.params.violation_id = self._extract_string_param("Violation ID")
        self.params.snapshot_id = self._extract_string_param("Snapshot ID", is_mandatory=True)
        self.params.file_name_filter = self._extract_string_param("File Name Filter")
        self.params.max_results = self._extract_string_param("Max Results")
        self.params.next_page_token = self._extract_string_param("Next Page Token")
        self.params.raw_dates = {
            name: self._extract_string_param(name) for start, end, _ in DATE_RANGE_PARAMS for name in (start, end)
        }

    def _validate_params(self) -> None:
        soar_action = self.soar_action
        file_filter = ViolationFileListFilter(
            snappable_fid=self.params.object_id,
            snapshot_fid=self.params.snapshot_id,
            filename_filter=self.params.file_name_filter or None,
            risk_levels=parse_file_risk_level_param(soar_action),
            exposures=parse_file_exposure_param(soar_action),
            access_via=parse_file_access_via_param(soar_action),
            sort=SortSpec(
                sort_by=parse_file_sort_by_param(soar_action, default=DEFAULT_SORT_BY),
                sort_order=parse_sort_order_param(soar_action, default=DEFAULT_SORT_ORDER),
            ),
        )
        file_filter.snappable_fid = validate_uuid_param(file_filter.snappable_fid, "Object ID")
        file_filter.snapshot_fid = validate_uuid_param(file_filter.snapshot_fid, "Snapshot ID")
        # Violation ID is optional: validated only when given, omitted from the filter otherwise.
        self.params.violation_id = validate_optional_uuid(self.params.violation_id, "Violation ID")
        file_filter.violation_id = self.params.violation_id or None
        (
            file_filter.last_access,
            file_filter.last_updated,
            file_filter.creation,
            file_filter.last_scan,
        ) = validate_date_ranges(self.params.raw_dates, DATE_RANGE_PARAMS)
        self.params.file_filter = file_filter
        self.params.page = Page(
            first=validate_max_results(
                self.params.max_results,
                default=DEFAULT_FILE_LIST_MAX_RESULTS,
                max_allowed=MAX_FILES,
            ),
            after_cursor=self.params.next_page_token or None,
        )

    def _perform_action(self, _: object = None) -> None:
        data: SingleJson = self.api_client.get_violation_file_list(self.params.file_filter, self.params.page)
        policy_obj: SingleJson = data.get("policyObj") or {}
        nodes, next_cursor = parse_connection(policy_obj.get("fileResultConnection") or {})
        if not nodes:
            # Keep an empty JSON result, as before, so playbooks can always read it.
            self.soar_action.result.add_result_json([])
            self.output_message = NO_RESULTS_MESSAGE
            return

        self.json_results = nodes
        table_rows = [FileEntry(node).to_csv() for node in nodes][:MAX_TABLE_RECORDS]
        self.data_tables.append(DataTable(title=TABLE_TITLE, data_table=construct_csv(table_rows)))
        violation_suffix = (
            f" for violation ID: {self.params.violation_id}" if self.params.violation_id else ""
        )
        self.output_message = f"Successfully retrieved {len(nodes)} file(s){violation_suffix}."
        if next_cursor:
            self.output_message += f" Use Next Page Token '{next_cursor}' to retrieve the next page."
        self.logger.info(SHA1_NOTE)


def main() -> None:
    GetViolationFileList().run()


if __name__ == "__main__":
    main()
