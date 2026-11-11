from __future__ import annotations

from datetime import UTC, datetime

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    ASM_ISSUE_SEVERITY_MAPPING,
    ASM_ISSUE_STATUS_MAPPING,
    CUSTOM_TIME,
    INTEGRATION_DISPLAY_NAME,
    MAX_SEARCH_ISSUES_LIMIT,
    SEARCH_ASM_ISSUES_SCRIPT_NAME,
    TIME_INTERVALS,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {SEARCH_ASM_ISSUES_SCRIPT_NAME}."


class SearchASMIssues(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = []

    def _extract_action_parameters(self) -> None:
        self.params.project_name = extract_action_param(
            self.soar_action,
            param_name="Project Name",
            print_value=True,
        )
        self.params.issue_ids = extract_action_param(
            self.soar_action,
            param_name="Issue ID",
            print_value=True,
        )
        self.params.entity_ids = extract_action_param(
            self.soar_action,
            param_name="Entity ID",
            print_value=True,
        )
        self.params.entity_names = extract_action_param(
            self.soar_action,
            param_name="Entity Name",
            print_value=True,
        )
        self.params.time_parameter = extract_action_param(
            self.soar_action,
            param_name="Time Parameter",
            print_value=True,
        )
        self.params.time_frame = extract_action_param(
            self.soar_action,
            param_name="Time Frame",
            print_value=True,
        )
        self.params.start_time = extract_action_param(
            self.soar_action,
            param_name="Start Time",
            print_value=True,
        )
        self.params.end_time = extract_action_param(
            self.soar_action,
            param_name="End Time",
            print_value=True,
        )
        self.params.lowest_severity = extract_action_param(
            self.soar_action,
            param_name="Lowest Severity To Return",
            print_value=True,
        )
        self.params.status = extract_action_param(
            self.soar_action,
            param_name="Status",
            print_value=True,
        )
        self.params.tags = extract_action_param(
            self.soar_action,
            param_name="Tags",
            print_value=True,
        )
        self.params.max_issues_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Issues To Return",
            is_mandatory=True,
            default_value="50",
            print_value=True,
        )
        self.params.lowest_severity = ASM_ISSUE_SEVERITY_MAPPING.get(
            self.params.lowest_severity.lower(), None
        )
        self.params.status = ASM_ISSUE_STATUS_MAPPING.get(self.params.status)
        self.params.action_start_time = unix_now()
        self.params.issue_ids = (
            self.params.issue_ids.lower()
            if (self.params.issue_ids)
            else self.params.issue_ids
        )
        self.params.entity_ids = (
            self.params.entity_ids.lower()
            if (self.params.entity_ids)
            else self.params.entity_ids
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.issue_ids = validator.validate_csv(
            param_name="Issue ID",
            csv_string=self.params.issue_ids,
            print_value=False,
        )
        self.params.entity_ids = validator.validate_csv(
            param_name="Entity ID",
            csv_string=self.params.entity_ids,
            print_value=False,
        )
        self.params.entity_names = validator.validate_csv(
            param_name="Entity Name",
            csv_string=self.params.entity_names,
            print_value=False,
        )
        self.params.tags = validator.validate_csv(
            param_name="Tags",
            csv_string=self.params.tags,
            print_value=False,
        )
        self.params.time_frame = validator.validate_ddl(
            "Time Frame",
            self.params.time_frame,
            [*TIME_INTERVALS, CUSTOM_TIME],
            print_value=True,
        )
        if not is_empty_string_or_none(self.params.max_issues_to_return):
            self.params.max_issues_to_return = validator.validate_positive(
                param_name="Max Issues To Return",
                value=self.params.max_issues_to_return,
                print_value=False,
            )
            self.params.max_issues_to_return = validator.validate_upper_limit(
                param_name="Max Issues To Return",
                value=self.params.max_issues_to_return,
                limit=MAX_SEARCH_ISSUES_LIMIT,
            )

        if self.params.time_frame == CUSTOM_TIME:
            self._validate_dates()
        else:
            timedelta = TIME_INTERVALS[self.params.time_frame]
            self.params.start_time = datetime.now() - timedelta
            self.params.end_time = datetime.now(UTC).isoformat()

    def _validate_dates(self):
        if self.params.start_time is None:
            raise GoogleThreatIntelligenceExceptions(
                "Missing value for parameter 'Start Time' this value is mandatory"
                " when 'Custom' is selected for parameter 'Time Frame'."
            )
        self.params.start_time = self._parse_isoformat(
            self.params.start_time, "start time"
        )
        self.params.end_time = (
            self._parse_isoformat(self.params.end_time, "end time")
            if self.params.end_time
            else datetime.now(UTC).isoformat()
        )

        if self.params.start_time >= self.params.end_time:
            raise GoogleThreatIntelligenceExceptions(
                "Invalid parameters provided: 'Start Time' "
                "should be less than 'End Time'."
            )
        if self.params.start_time > datetime.now(UTC).isoformat():
            raise GoogleThreatIntelligenceExceptions(
                "Invalid parameters provided: 'Start Time' "
                "cannot be greater than the current time."
            )

    def _parse_isoformat(self, time_str, label):
        """Helper method to parse and validate ISO format timestamps."""
        try:
            return datetime.fromisoformat(time_str).isoformat()
        except ValueError as error:
            raise GoogleThreatIntelligenceExceptions(
                f"Invalid ISO format for {label}: {time_str}"
            ) from error

    def _perform_action(self, _=None) -> None:
        self.api_client.set_project_id(self.params.project_name)

        issues = self.api_client.search_issues(
            lowest_severity=self.params.lowest_severity,
            limit=self.params.max_issues_to_return,
            script_starting_time=self.params.action_start_time,
            execution_deadline=self.soar_action.execution_deadline_unix_time_ms,
            entity_name=self.params.entity_names,
            issue_ids=self.params.issue_ids,
            entity_ids=self.params.entity_ids,
            tags=self.params.tags,
            time_parameter=self.params.time_parameter,
            start_time=self.params.start_time,
            end_time=self.params.end_time,
            status=self.params.status,
        )
        if issues:
            self.output_message = (
                f"Successfully returned issues based on the provided criteria "
                f"in {INTEGRATION_DISPLAY_NAME}."
            )
            self.json_results = [issue.raw_data for issue in issues]

        else:
            self.output_message = (
                f"No issues were found based on the provided criteria "
                f"in {INTEGRATION_DISPLAY_NAME}."
            )


def main() -> None:
    SearchASMIssues(SEARCH_ASM_ISSUES_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
