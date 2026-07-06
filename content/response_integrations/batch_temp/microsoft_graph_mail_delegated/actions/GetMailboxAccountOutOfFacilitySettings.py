from __future__ import annotations
from typing import NoReturn

from collections.abc import MutableSequence

from soar_sdk.SiemplifyDataModel import DomainEntityInfo

from TIPCommon.base.action import Action
from TIPCommon.base.action.data_models import EntityTypesEnum, ExecutionState
from TIPCommon.transformation import construct_csv
from TIPCommon.utils import is_valid_email
from ..core import action_init
from ..core import constants
from ..core import exceptions
from ..core import MicrosoftGraphMailDelegatedManager as api_manager
from ..core import MicrosoftGraphMailDelegatedParser as parser


class GetMailboxAccountOutOfFacilitySettings(Action[api_manager.ApiManager]):

    def __init__(self) -> None:
        super().__init__(
            constants.GET_MAILBOX_ACCOUNT_OUT_OF_FACILITY_SETTINGS_SCRIPT_NAME
        )
        self.result_value = True
        self.execution_state = ExecutionState.COMPLETED
        self.output_message = ""
        self.error_output_message = (
            "Error executing action "
            f'"{constants.GET_MAILBOX_ACCOUNT_OUT_OF_FACILITY_SETTINGS_SCRIPT_NAME}".'
        )
        self.user_entities = []
        self.successful_entities = []
        self.enrichment_entities = []
        self.failed_entities = []
        self.invalid_entities = []
        self.json_results = {}

    def _init_api_clients(self) -> api_manager.ApiManager:
        return action_init.create_api_client(self.soar_action)

    def _get_entity_types(self) -> MutableSequence[EntityTypesEnum]:
        """Get which entity types does the action work on"""
        supported_entities = self.user_entities = [
            entity
            for entity in self.soar_action.target_entities
            if entity.entity_type == EntityTypesEnum.USER.value
        ]
        if not supported_entities:
            raise exceptions.UserEntityNotFound(
                "Failed to execute action because no supported entity was found!"
            )

        return [EntityTypesEnum.USER]

    def _perform_action(self, entity: DomainEntityInfo) -> None:
        valid_mailbox = None
        try:
            if is_valid_email(entity.identifier):
                valid_mailbox = entity.identifier
            if not valid_mailbox:
                self.invalid_entities.append(entity.identifier)
                raise exceptions.UnableToGetValidEmailFromEntity()

            user_id = self.api_client.get_user_id(valid_mailbox)
            user_oof_settings = self.api_client.get_user_oof_settings(user_id)
            self.successful_entities.append(valid_mailbox)
            self.enrichment_entities.append(entity)
            settings = parser.build_mg_oof_settings_object(
                raw_data=user_oof_settings.raw_data
            )
            self.soar_action.result.add_data_table(
                title=f"{entity.identifier} Out of Facility Settings",
                data_table=construct_csv([settings.to_table()]),
            )
            self.json_results[entity.identifier] = user_oof_settings.to_json()
            entity.additional_properties.update(user_oof_settings.to_enrichment_data())
            entity.is_enriched = True

        except (
            exceptions.MicrosoftGraphMailManagerError,
            exceptions.UnableToGetValidEmailFromEntity,
            exceptions.UserEntityNotFound,
        ):
            self.failed_entities.append(valid_mailbox or entity.identifier)

    def _finalize_action_on_success(self) -> None:
        if self.successful_entities:
            self.soar_action.update_entities(self.enrichment_entities)
            joined_successful = "\n".join(self.successful_entities)
            self.output_message = (
                "Successfully returned OOF settings for the:\n" f"{joined_successful}"
            )

        if self.failed_entities or self.invalid_entities:
            joined_failed_invalid = "\n".join(
                self.failed_entities + self.invalid_entities
            )
            self.output_message += (
                "\n\nFailed to find the following usernames in Microsoft 365:\n"
                f"{joined_failed_invalid}"
            )
            self.result_value = False

        if not self.successful_entities:
            self.output_message = (
                "The action wasn't able to find OOF settings for:\n"
                f"{joined_failed_invalid}"
            )
            self.result_value = False
            self.execution_state = ExecutionState.FAILED


def main() -> NoReturn:
    action = GetMailboxAccountOutOfFacilitySettings()
    action.run()


if __name__ == "__main__":
    main()
