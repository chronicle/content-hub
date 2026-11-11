from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    EXECUTE_IOC_SEARCH_SCRIPT_NAME,
    INTEGRATION_DISPLAY_NAME,
    LIMIT_DEFAULT_VALUE,
    MAX_IOC_SEARCH_LIMIT,
)
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none

SUCCESS_MESSAGE = (
    f"Successfully found results for the provided query in {INTEGRATION_DISPLAY_NAME}."
)
ERROR_MESSAGE = f"Error executing action {EXECUTE_IOC_SEARCH_SCRIPT_NAME}."
NO_RESULT_MESSAGE = (
    f"No results were found for the provided query in {INTEGRATION_DISPLAY_NAME}."
)


class ExecuteIocSearch(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = NO_RESULT_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = False
        self.json_results = []

    def _extract_action_parameters(self) -> None:
        self.params.search_query = extract_action_param(
            self.soar_action,
            param_name="Search Query",
            is_mandatory=True,
            print_value=True,
        )
        self.params.max_results_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Results To Return",
            is_mandatory=False,
            print_value=True,
            default_value=str(LIMIT_DEFAULT_VALUE),
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        if not is_empty_string_or_none(self.params.max_results_to_return):
            self.params.max_results_to_return = validator.validate_positive(
                param_name="Max Results To Return",
                value=self.params.max_results_to_return,
                print_value=False,
            )

            self.params.max_results_to_return = validator.validate_upper_limit(
                param_name="Max Results To Return",
                value=self.params.max_results_to_return,
                limit=MAX_IOC_SEARCH_LIMIT,
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()

        results = self.api_client.search_iocs(
            self.params.search_query,
            self.params.max_results_to_return,
        )

        self.output_message = NO_RESULT_MESSAGE
        self.result_value = False
        self.json_results = []

        if results:
            self.output_message = SUCCESS_MESSAGE
            self.result_value = True
            self.logger.info("Adding query results to JSON results")
            self.json_results = [result.to_json_shorten() for result in results]


def main() -> None:
    ExecuteIocSearch(EXECUTE_IOC_SEARCH_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
