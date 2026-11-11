from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    INTEGRATION_DISPLAY_NAME,
    MAX_SEARCH_ENTITIES_LIMIT,
    SEARCH_ASM_ENTITIES_SCRIPT_NAME,
)
from soar_sdk.SiemplifyUtils import unix_now
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import is_empty_string_or_none

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {SEARCH_ASM_ENTITIES_SCRIPT_NAME}."


class SearchASMEntities(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.project_name = extract_action_param(
            self.soar_action,
            param_name="Project Name",
            print_value=True,
        )
        self.params.entity_names = extract_action_param(
            self.soar_action,
            param_name="Entity Name",
            print_value=True,
        )
        self.params.vuln_count_gte = extract_action_param(
            self.soar_action,
            param_name="Minimum Vulnerabilities Count",
            print_value=True,
        )
        self.params.issue_count_gte = extract_action_param(
            self.soar_action,
            param_name="Minimum Issues Count",
            print_value=True,
        )
        self.params.tags = extract_action_param(
            self.soar_action,
            param_name="Tags",
            print_value=True,
        )
        self.params.max_entities_to_return = extract_action_param(
            self.soar_action,
            param_name="Max Entities To Return",
            is_mandatory=True,
            default_value="50",
            print_value=True,
        )
        self.params.critical_or_high = extract_action_param(
            self.soar_action,
            param_name="Critical or High Issue",
            print_value=True,
            input_type=bool,
        )
        self.params.action_start_time = unix_now()

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

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
        if not is_empty_string_or_none(self.params.max_entities_to_return):
            self.params.max_entities_to_return = validator.validate_positive(
                param_name="Max Entities To Return",
                value=self.params.max_entities_to_return,
                print_value=False,
            )
            self.params.max_entities_to_return = validator.validate_upper_limit(
                param_name="Max Entities To Return",
                value=self.params.max_entities_to_return,
                limit=MAX_SEARCH_ENTITIES_LIMIT,
            )
        if not is_empty_string_or_none(self.params.vuln_count_gte):
            self.params.vuln_count_gte = validator.validate_positive(
                param_name="Minimum Vulnerabilities Count",
                value=self.params.vuln_count_gte,
                print_value=False,
            )
        if not is_empty_string_or_none(self.params.issue_count_gte):
            self.params.issue_count_gte = validator.validate_positive(
                param_name="Minimum Issues Count",
                value=self.params.issue_count_gte,
                print_value=False,
            )

    def _perform_action(self, _=None) -> None:
        self.api_client.set_project_id(self.params.project_name)

        entities = self.api_client.search_asm_entities(
            entity_name=self.params.entity_names,
            tags=self.params.tags,
            critical_or_high=self.params.critical_or_high,
            limit=self.params.max_entities_to_return,
            script_starting_time=self.params.action_start_time,
            execution_deadline=self.soar_action.execution_deadline_unix_time_ms,
            vuln_count_gte=self.params.vuln_count_gte,
            issue_count_gte=self.params.issue_count_gte,
        )
        if entities:
            self.output_message = (
                f"Successfully returned entities based on the provided criteria "
                f"in {INTEGRATION_DISPLAY_NAME}."
            )
            self.logger.info("Adding entities to JSON results")
            self.json_results = [entity.raw_data for entity in entities]

        else:
            self.output_message = (
                f"No entities were found based on the provided criteria"
                f"in {INTEGRATION_DISPLAY_NAME}."
            )


def main() -> None:
    SearchASMEntities(SEARCH_ASM_ENTITIES_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
