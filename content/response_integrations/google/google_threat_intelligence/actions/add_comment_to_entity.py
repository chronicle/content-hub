from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import ADD_COMMENT_TO_ENTITY_SCRIPT_NAME, INTEGRATION_DISPLAY_NAME
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
]

SUCCESS_MESSAGE = ""
ERROR_MESSAGE = f"Error executing action {INTEGRATION_DISPLAY_NAME}."


class AddCommentToEntity(BaseAction):
    def __init__(self, script_name: str) -> None:
        super().__init__(script_name)
        self.output_message = SUCCESS_MESSAGE
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.comment = extract_action_param(
            self.soar_action,
            param_name="Comment",
            is_mandatory=True,
            print_value=True,
        )

    def _perform_action(self, _=None) -> None:
        self.api_client.test_connectivity()
        successful_entities = []
        failed_entities = []

        for entity in self.soar_action.target_entities:
            identifier = get_entity_original_identifier(entity)
            if entity.entity_type in SUPPORTED_ENTITIES:
                try:
                    self.logger.info(f"Started processing entity: {identifier}")
                    self.api_client.add_comment_to_entity(entity, self.params.comment)
                    successful_entities.append(identifier)
                    self.json_results.update({identifier: {"Status": "Done"}})
                except GoogleThreatIntelligenceExceptions as e:
                    failed_entities.append(identifier)
                    self.json_results.update({identifier: {"Status": "Not done"}})
                    self.logger.error(f"An error occurred on entity {identifier}")
                    self.logger.exception(e)

        if successful_entities:
            self.json_results = convert_dict_to_json_result_dict(self.json_results)
            self.output_message += (
                f"Successfully added comments to the following "
                f"entities in {INTEGRATION_DISPLAY_NAME}: \n"
                f" {', '.join(successful_entities)} \n"
            )
            if failed_entities:
                self.output_message += (
                    f"Action wasn't able to add comments to the following "
                    f"entities in {INTEGRATION_DISPLAY_NAME}:"
                    f" \n {', '.join(failed_entities)} \n"
                )
        else:
            self.result_value = False
            self.output_message = (
                "No comments were added to the provided entities"
                f" in {INTEGRATION_DISPLAY_NAME}."
            )


def main() -> None:
    AddCommentToEntity(ADD_COMMENT_TO_ENTITY_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
