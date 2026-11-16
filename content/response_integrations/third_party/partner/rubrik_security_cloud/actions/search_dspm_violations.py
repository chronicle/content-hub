from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import DataTable
from TIPCommon.transformation import construct_csv

from ..core.base_action import RubrikAction
from ..core.constants import (
    DEFAULT_MAX_RESULTS,
    ERROR_DETECTION_DATE_ORDER,
    ERROR_MAX_RESULTS_NOT_INTEGER,
    ERROR_MAX_RESULTS_TOO_HIGH,
    ERROR_MAX_RESULTS_TOO_LOW,
    ERROR_UPDATE_DATE_ORDER,
    MAX_TABLE_RECORDS,
    MAX_VIOLATIONS,
    SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME,
)
from ..core.rubrik_exceptions import InvalidIntegerException
from ..core.validators import (
    parse_connection,
    parse_dspm_category_param,
    parse_dspm_object_type_param,
    parse_dspm_severity_param,
    parse_dspm_sort_by_param,
    parse_sensitivity_level_param,
    parse_sort_order_param,
    parse_status_param,
    validate_date_ranges,
)
from ..core.violation_datamodels import DSPMViolation
from ..core.violations_api import DSPMViolationSearchFilter, Page, SortSpec

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

# (start parameter, end parameter, error when end is not after start)
DATE_RANGE_PARAMS: tuple[tuple[str, str, str], ...] = (
    ("Detection Start Date", "Detection End Date", ERROR_DETECTION_DATE_ORDER),
    ("Update Start Date", "Update End Date", ERROR_UPDATE_DATE_ORDER),
)
TABLE_TITLE: str = "DSPM Violations"
NO_RESULTS_MESSAGE: str = "No DSPM violations found matching the applied filters."


class SearchDSPMViolations(RubrikAction):
    graphql_error_prefix = "API error during Search DSPM Violations"

    def __init__(self) -> None:
        super().__init__(SEARCH_DSPM_VIOLATIONS_SCRIPT_NAME)
        self.json_results: list[SingleJson] = []

    def _extract_action_parameters(self) -> None:
        super()._extract_action_parameters()
        self.params.raw_dates = {
            name: self._extract_string_param(name) for start, end, _ in DATE_RANGE_PARAMS for name in (start, end)
        }
        self.params.max_results = self._extract_string_param("Max Results")
        self.params.next_page_token = self._extract_string_param("Next Page Token")

    def _validate_params(self) -> None:
        soar_action = self.soar_action
        search_filter = DSPMViolationSearchFilter(
            object_types=parse_dspm_object_type_param(soar_action),
            statuses=parse_status_param(soar_action),
            severities=parse_dspm_severity_param(soar_action),
            categories=parse_dspm_category_param(soar_action),
            sensitivity_levels=parse_sensitivity_level_param(soar_action),
            sort=SortSpec(
                sort_by=parse_dspm_sort_by_param(soar_action),
                sort_order=parse_sort_order_param(soar_action),
            ),
        )
        # Dates are validated after the enum parameters, matching the original error order.
        search_filter.detection_date, search_filter.update_date = validate_date_ranges(
            self.params.raw_dates, DATE_RANGE_PARAMS
        )
        self.params.search_filter = search_filter
        self.params.page = Page(
            first=validate_max_results(self.params.max_results),
            after_cursor=self.params.next_page_token or None,
        )

    def _perform_action(self, _: object = None) -> None:
        data: SingleJson = self.api_client.search_dspm_violations(self.params.search_filter, self.params.page)
        policy_violations: SingleJson = data.get("policyViolations") or {}
        nodes, next_cursor = parse_connection(policy_violations)
        if not nodes:
            # Keep an empty JSON result, as before, so playbooks can always read it.
            self.soar_action.result.add_result_json([])
            self.output_message = NO_RESULTS_MESSAGE
            return

        self.json_results = nodes
        table_rows = [DSPMViolation(node).to_csv() for node in nodes][:MAX_TABLE_RECORDS]
        self.data_tables.append(DataTable(title=TABLE_TITLE, data_table=construct_csv(table_rows)))
        self.output_message = (
            f"Successfully retrieved {len(nodes)} DSPM violation(s) "
            f"(total matching: {policy_violations.get('count', 0)})."
        )
        if next_cursor:
            self.output_message += f" Use Next Page Token '{next_cursor}' to retrieve the next page."


def validate_max_results(raw_value: str | None) -> int:
    """Validate the Max Results parameter per the Search DSPM Violations spec.

    Raises:
        InvalidIntegerException: With the exact wording required by the action's
            case wall output message contract.
    """
    if raw_value is None or not str(raw_value).strip():
        return DEFAULT_MAX_RESULTS

    raw_value = str(raw_value).strip()
    try:
        value = int(raw_value)
    except ValueError:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_NOT_INTEGER.format(raw_value))

    if value < 1:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_TOO_LOW)
    if value > MAX_VIOLATIONS:
        raise InvalidIntegerException(ERROR_MAX_RESULTS_TOO_HIGH.format(MAX_VIOLATIONS, raw_value))

    return value


def main() -> None:
    SearchDSPMViolations().run()


if __name__ == "__main__":
    main()
