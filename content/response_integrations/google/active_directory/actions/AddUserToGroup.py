from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    ActiveDirectoryNotFoundUserError,
    ActiveDirectoryNotFoundGroupError,
)
from ..core.utils import load_csv_to_list

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "ActiveDirectory"
SCRIPT_NAME = "ActiveDirectory - AddUserToGroup"
SUPPORTED_ENTITY_TYPES = [EntityTypes.USER]
DEFAULT_PAGE_SIZE = 25
DEFAULT_SIZE_LIMIT = 1000

ADDED_SUCCESSFULLY = "success"
ALREADY_EXISTS = "entryAlreadyExists"
INSUFFICIENT_ACCESS_RIGHTS = "insufficientAccessRights"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    result_value = False
    successful_entities = []
    failed_entities = []
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATIONS:
    server = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Server",
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Username",
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Password",
        input_type=str,
    )
    domain = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Domain",
        input_type=str,
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        is_mandatory=True,
        param_name="Use SSL",
        input_type=bool,
    )
    custom_query_fields = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Custom Query Fields",
        input_type=str,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    # INIT ACTION CONFIGURATIONS:
    group_names = extract_action_param(
        siemplify,
        param_name="Group Name",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        manager = ActiveDirectoryManager(
            server,
            domain,
            username,
            password,
            use_ssl,
            custom_query_fields,
            ca_certificate,
            siemplify.LOGGER,
        )

        group_names_list = set(load_csv_to_list(group_names, "Groups"))

        target_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type in SUPPORTED_ENTITY_TYPES
        ]

        successful_groups_entity_dict = {
            group_name: [] for group_name in group_names_list
        }
        failed_groups_entity_dict = {group_name: [] for group_name in group_names_list}
        existing_group_members = {group_name: [] for group_name in group_names_list}

        if target_entities:
            for entity in target_entities:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                not_existing_groups = []
                user_exists = True

                for group_name in group_names_list:
                    try:
                        added_to_group_result = manager.add_user_to_group(
                            entity.identifier, group_name
                        )
                        if (
                            added_to_group_result.get("description", "")
                            == ADDED_SUCCESSFULLY
                        ):
                            successful_entities.append(entity)
                            successful_groups_entity_dict[group_name].append(
                                entity.identifier
                            )
                        else:
                            if (
                                added_to_group_result.get("description", "")
                                == ALREADY_EXISTS
                            ):
                                siemplify.LOGGER.info(
                                    f"{entity.identifier} already in {group_name}"
                                )
                                successful_entities.append(entity)
                                existing_group_members[group_name].append(
                                    entity.identifier
                                )
                            elif (
                                added_to_group_result.get("description", "")
                                == INSUFFICIENT_ACCESS_RIGHTS
                            ):
                                siemplify.LOGGER.info(
                                    f"Cannot add {entity.identifier} to {group_name}. Reason is: insufficient access rights"
                                )
                                failed_groups_entity_dict[group_name].append(
                                    entity.identifier
                                )

                    except ActiveDirectoryNotFoundUserError as err:
                        output_message += f"{err}\n"
                        for _group_name in group_names_list:
                            failed_groups_entity_dict[_group_name].append(
                                entity.identifier
                            )
                            siemplify.LOGGER.error(
                                f"An error occurred when tried to add the entity {entity.identifier}"
                                f" to the group {_group_name}"
                            )
                            siemplify.LOGGER.exception(err)
                        user_exists = False

                    except ActiveDirectoryNotFoundGroupError as err:
                        output_message += f"{err}\n"
                        not_existing_groups.append(group_name)
                        failed_groups_entity_dict[group_name].append(entity.identifier)
                        siemplify.LOGGER.error(
                            f"An error occurred when tried to add the entity {entity.identifier}"
                            f" to the group {group_name}"
                        )
                        siemplify.LOGGER.exception(err)

                    if not user_exists:
                        break

                if entity not in successful_entities:
                    failed_entities.append(entity)
                if not_existing_groups:
                    group_names_list = [
                        el for el in group_names_list if el not in not_existing_groups
                    ]

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            if not successful_entities:
                result_value = False
                output_message += (
                    "No users were added to the provided groups in Active Directory."
                )

            else:
                result_value = True
                for group, user_list in successful_groups_entity_dict.items():
                    if not user_list and not existing_group_members.get(group, []):
                        output_message += f"No users were added to group '{group}' in Active Directory.\n"

                    else:
                        if user_list:
                            output_message += (
                                f"Successfully added the following users to group '{group}'"
                                f" in Active Directory:\n{', '.join(user_list)}\n"
                            )

                        _existing_group_members = existing_group_members.get(group, [])
                        if _existing_group_members:
                            output_message += (
                                f"The following users were already a part of group '{group}' in"
                                f" Active Directory:\n{', '.join(_existing_group_members)}\n"
                            )

                        _failed_groups_entity = failed_groups_entity_dict.get(group, [])
                        if _failed_groups_entity:
                            output_message += (
                                f"Action wasn’t able to add the following users to group '{group}' in"
                                f" Active Directory:\n{', '.join(_failed_groups_entity)}\n"
                            )

        else:
            output_message = "No suitable entities found.\n"

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\nstatus: {status}\nresult_value: {result_value}\noutput_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
