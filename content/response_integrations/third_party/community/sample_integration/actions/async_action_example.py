from __future__ import annotations

import json
from typing import TYPE_CHECKING

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import get_case_overview_details
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.validation import ParameterValidator

from ..core.base_action import SampleAction
from ..core.constants import ASYNC_ACTION_EXAMPLE_SCRIPT_NAME

if TYPE_CHECKING:
    from collections.abc import Iterable

    from TIPCommon.data_models import CaseDetails
    from TIPCommon.types import SingleJson


DEFAULT_CASE_TAG_TO_WAIT_FOR: str = "Async"

SUCCESS_MESSAGE: str = 'The following cases have tag "{tag}": {case_ids}'
PENDING_MESSAGE: str = 'Action is waiting for the cases "{case_ids}" to have a tag {tag}...'
TIMEOUT_ERROR_MESSAGE: str = (
    "Action ran into a timeout during execution. Please increase the timeout in IDE."
)


class AsyncActionExample(SampleAction):
    def __init__(self) -> None:
        super().__init__(ASYNC_ACTION_EXAMPLE_SCRIPT_NAME)
        self.output_message: str = ""
        self.result_value: bool = False
        self.error_output_message: str = (
            f'Error executing action "{ASYNC_ACTION_EXAMPLE_SCRIPT_NAME}".'
        )
        self.cases_with_tag: set[int] = set()
        self.waiting_cases: set[int] = set()

    def _is_approaching_async_timeout(self) -> bool:
        """Determine whether the action approaches asynchronous timeout."""
        return is_approaching_action_timeout(
            self.soar_action.async_total_duration_deadline,
        )

    def _extract_action_parameters(self) -> None:
        self.params.case_ids = extract_action_param(
            self.soar_action,
            param_name="Case IDs",
            print_value=True,
        )
        self.params.case_tag_to_wait_for = extract_action_param(
            self.soar_action,
            param_name="Case Tag To Wait For",
            is_mandatory=True,
            default_value=DEFAULT_CASE_TAG_TO_WAIT_FOR,
            print_value=True,
        )
        self.params.additional_data = json.loads(
            extract_action_param(
                siemplify=self.soar_action,
                param_name="additional_data",
                default_value="{}",
            ),
        )

    def _validate_params(self) -> None:
        # If no case IDs provided, use the current case ID
        if not self.params.case_ids:
            self.logger.info(
                f"no Case IDs provided, defaulting to Case ID {self.soar_action.case_id}"
            )
            self.params.case_ids = [self.soar_action.case_id]
            return

        validator: ParameterValidator = ParameterValidator(self.soar_action)
        self.params.case_ids = validator.validate_csv(
            param_name="Case IDs",
            csv_string=self.params.case_ids,
        )

    def _check_case_tags(self, case_ids: list[str], tag: str) -> dict[int, bool]:
        """Check if the specified cases have the specified tag.

        Args:
            case_ids: List of case IDs to check
            tag: Tag to check for

        Returns:
            Dictionary with case IDs as keys and boolean values indicating
            if they have the tag
        """
        result: dict[int, bool] = {}

        for case_id in case_ids:
            self.logger.info(f"Fetching Case {case_id} data from Server")
            case_details: CaseDetails = get_case_overview_details(
                self.soar_action,
                case_id,
            )
            result[case_id] = any(
                (isinstance(case_tag, dict) and case_tag.get("displayName") == tag)
                or (isinstance(case_tag, str) and case_tag == tag)
                for case_tag in case_details.tags
            )
        return result

    def _first_run(self) -> None:
        self._process_cases(self.params.case_ids)

    def _consecutive_run(self) -> None:
        self.cases_with_tag.update(self.params.additional_data.get("cases_with_tag", []))
        cases_to_process: SingleJson = self.params.additional_data.get("waiting_cases", [])
        self._process_cases(cases_to_process)

    def _process_cases(self, case_ids: Iterable[int]):
        self.logger.info("Starting to process cases tags")
        case_tags_status: dict[int, bool] = self._check_case_tags(
            case_ids,
            self.params.case_tag_to_wait_for,
        )
        for case_id, status in case_tags_status.items():
            if status:
                self.logger.info(
                    f"Case {case_id} has '{self.params.case_tag_to_wait_for}' attached"
                )
                self.cases_with_tag.add(case_id)
                continue
            self.logger.info(
                f"Case {case_id} doesn't have case tag '{self.params.case_tag_to_wait_for}'"
            )
            self.waiting_cases.add(case_id)

    def _perform_action(self, _=None) -> None:
        if self._is_approaching_async_timeout():
            self.logger.info("Action is approaching async timeout, and will exit gracefully")
            raise TimeoutError(TIMEOUT_ERROR_MESSAGE)

        if self.is_first_run:
            self.logger.info("First Async action iteration")
            self._first_run()
        else:
            self.logger.info("This is consecutive action iteration")
            self._consecutive_run()

        self.json_results = [
            {"case_id": case_id, "tags": [self.params.case_tag_to_wait_for]}
            for case_id in self.cases_with_tag
        ]

    def _is_all_cases_done(self) -> bool:
        return self.cases_with_tag == set(self.params.case_ids)

    def _finalize_action_on_success(self) -> None:
        if self._is_all_cases_done():
            self.logger.info("All required cases were found with the desired case tag")
            self.execution_state = ExecutionState.COMPLETED
            self.result_value = True
            self.output_message = SUCCESS_MESSAGE.format(
                tag=self.params.case_tag_to_wait_for,
                case_ids=", ".join(self.cases_with_tag),
            )
            return

        self.logger.info(
            "Not all cases have the required case tag attached. "
            f"Cases missing the tag: {repr(self.waiting_cases)}"
        )
        self.logger.info(
            "The action will continue its execution on the cases missing the tags in "
            "the next iteration."
        )
        self.output_message = PENDING_MESSAGE.format(
            case_ids=", ".join(self.waiting_cases),
            tag=self.params.case_tag_to_wait_for,
        )
        self.execution_state = ExecutionState.IN_PROGRESS
        self.result_value = json.dumps({
            "cases_with_tag": list(self.cases_with_tag),
            "waiting_cases": list(self.waiting_cases),
        })


def main() -> None:
    AsyncActionExample().run()


if __name__ == "__main__":
    main()
