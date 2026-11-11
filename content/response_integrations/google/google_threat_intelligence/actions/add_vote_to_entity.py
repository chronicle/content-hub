from __future__ import annotations

from google_threat_intelligence.core.base_action import BaseAction
from google_threat_intelligence.core.constants import (
    ADD_VOTE_TO_ENTITY_SCRIPT_NAME,
    CASE_INSENSITIVE_ENTITIES,
    INTEGRATION_DISPLAY_NAME,
)
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from TIPCommon.extraction import extract_action_param
from TIPCommon.utils import get_entity_original_identifier
from TIPCommon.validation import ParameterValidator

SUPPORTED_ENTITIES = [
    EntityTypes.ADDRESS,
    EntityTypes.FILEHASH,
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.DOMAIN,
]

ERROR_MESSAGE = f"Error executing action {ADD_VOTE_TO_ENTITY_SCRIPT_NAME}."


class AddVoteToEntity(BaseAction):
    def __init__(self, name) -> None:
        super().__init__(name)
        self.output_message = ""
        self.error_output_message = ERROR_MESSAGE
        self.result_value = True
        self.json_results = {}

    def _extract_action_parameters(self) -> None:
        self.params.vote = extract_action_param(
            self.soar_action,
            param_name="Vote",
            print_value=False,
            default_value="Malicious",
        )

    def _validate_params(self) -> None:
        validator = ParameterValidator(self.soar_action)
        validator.validate_ddl("Vote", self.params.vote, ["Malicious", "Harmless"])

    def _perform_action(self, _=None):
        successful_entities = []
        failed_entities = []

        self.api_client.test_connectivity()

        for entity in self.soar_action.target_entities:
            identifier = (
                entity.identifier.lower()
                if entity.entity_type in CASE_INSENSITIVE_ENTITIES
                else get_entity_original_identifier(entity)
            )
            if entity.entity_type in SUPPORTED_ENTITIES:
                try:
                    self.logger.info(f"Started processing entity: {identifier}")
                    self.api_client.add_vote_to_entity(entity, self.params.vote)

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
                f"Successfully added votes to the following "
                f"entities in {INTEGRATION_DISPLAY_NAME}: "
                f"\n {', '.join(successful_entities)} \n"
            )
            if failed_entities:
                self.output_message += (
                    f"Action wasn't able to add votes to the following "
                    f"entities in {INTEGRATION_DISPLAY_NAME}:"
                    f" \n {', '.join(failed_entities)} \n"
                )
        else:
            self.result_value = False
            self.output_message = (
                f"No votes were added to the provided "
                f"entities in {INTEGRATION_DISPLAY_NAME}."
            )


def main() -> None:
    AddVoteToEntity(ADD_VOTE_TO_ENTITY_SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
