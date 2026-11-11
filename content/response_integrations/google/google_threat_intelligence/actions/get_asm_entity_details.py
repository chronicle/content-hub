from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import GET_ASM_ENTITY_DETAILS_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon import validation
from TIPCommon.extraction import extract_action_param
from TIPCommon.transformation import convert_list_to_comma_string

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {GET_ASM_ENTITY_DETAILS_SCRIPT_NAME}."


class GetASMEntityDetails(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.entity_ids = extract_action_param(
            self.soar_action,
            param_name="Entity ID",
            is_mandatory=True,
            print_value=True,
        )

    def _validate_params(self) -> None:
        validator = validation.ParameterValidator(self.soar_action)

        self.params.entity_ids = validator.validate_csv(
            param_name="Entity ID",
            csv_string=self.params.entity_ids,
            print_value=False,
        )

        unique_entity_ids = []
        seen = set()

        for entity_id in self.params.entity_ids:
            if entity_id not in seen:
                seen.add(entity_id)
                unique_entity_ids.append(entity_id)

        self.params.entity_ids = unique_entity_ids

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()

        not_found_entity_ids = []
        entities_details = {}
        for entity_id in self.params.entity_ids:
            try:
                entities_details[entity_id] = self.api_client.get_asm_entity_by_id(
                    entity_id
                )
            except GoogleThreatIntelligenceExceptions as e:
                self.logger.error(
                    f"Failed to fetch details for {entity_id}. Error is {e}"
                )
                not_found_entity_ids.append(entity_id)

        if not entities_details:
            raise GoogleThreatIntelligenceExceptions(
                f"None of the provided entities were valid "
                f"or found in {INTEGRATION_DISPLAY_NAME}."
            )

        entity_details_csv = convert_list_to_comma_string(
            list(entities_details.keys()), delimiter=",\n"
        )

        self.output_message = (
            f"Successfully returned details for the following entities using "
            f"information from {INTEGRATION_DISPLAY_NAME}: {entity_details_csv}"
        )

        if not_found_entity_ids:
            not_found_entity_ids_csv = convert_list_to_comma_string(
                not_found_entity_ids, delimiter=",\n"
            )
            self.output_message += (
                f"\n\nAction wasn’t able to return details for the following entities "
                f"using information from "
                f"{INTEGRATION_DISPLAY_NAME}: {not_found_entity_ids_csv}"
            )

        self.logger.info("Adding Entity details to JSON results")
        json_results = {
            entity_id: entity_details.raw_data
            for entity_id, entity_details in entities_details.items()
        }
        self.json_results = convert_dict_to_json_result_dict(json_results)


def main() -> None:
    GetASMEntityDetails(GET_ASM_ENTITY_DETAILS_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
