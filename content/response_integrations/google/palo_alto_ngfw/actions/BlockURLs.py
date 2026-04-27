from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import BLOCK_URLS_SCRIPT_NAME, INTEGRATION_NAME
from ..core.exceptions import AlreadyExistsException, CategoryNotExistsException
from ..core.NGFWManager import NGFWManager


SUPPORTED_ENTITY_TYPES = [EntityTypes.URL]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = BLOCK_URLS_SCRIPT_NAME
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )
    device_name = extract_action_param(
        siemplify, param_name="Device Name", print_value=True
    )
    vsys_name = extract_action_param(
        siemplify, param_name="Vsys Name", print_value=True
    )
    policy_name = extract_action_param(
        siemplify, param_name="URL Category Name", print_value=True, is_mandatory=True
    )
    use_shared_objects = extract_action_param(
        siemplify, param_name="Use Shared Objects", print_value=True, input_type=bool
    )

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, existing_entities = [], [], []
    json_results = {"success": [], "failure": [], "already_exist": []}
    result_value = True
    suitable_entity_identifiers = [
        entity.identifier
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        if not use_shared_objects and (not device_name or not vsys_name):
            raise Exception(
                'Either "Use Shared Objects" parameter should be enabled or "Device name" '
                'and "Vsys name" to be provided.'
            )

        api = NGFWManager(
            api_root,
            username,
            password,
            siemplify.run_folder,
            siemplify.LOGGER,
            verify_ssl=verify_ssl,
        )
        if not use_shared_objects:
            current_urls = api.FindRuleBlockedUrls(device_name, vsys_name, policy_name)
            if current_urls is not None:
                existing_urls = list(current_urls)
            else:
                existing_urls = []
            for entity_identifier in suitable_entity_identifiers:

                if len(entity_identifier) > 255:
                    siemplify.LOGGER.error(
                        f"Entity: '{entity_identifier}' is longer than 255 characters."
                    )
                    failed_entities.append(entity_identifier)
                    continue

                if entity_identifier in existing_urls:
                    existing_entities.append(entity_identifier)
                else:
                    entity_identifier = entity_identifier.replace("&amp;", "&").replace(
                        "&", "&amp;"
                    )
                    try:
                        api.EditBlockedUrls(
                            deviceName=device_name,
                            vsysName=vsys_name,
                            policyName=policy_name,
                            urlsToAdd=[entity_identifier],
                        )
                        successful_entities.append(entity_identifier)
                    except Exception as err:
                        siemplify.LOGGER.error(f"Some errors occurred '{err}'")
                        siemplify.LOGGER.exception(err)
                        failed_entities.append(entity_identifier)
        else:
            for entity_identifier in suitable_entity_identifiers:
                if len(entity_identifier) > 255:
                    siemplify.LOGGER.error(
                        f"Entity: '{entity_identifier}' is longer than 255 characters."
                    )
                    failed_entities.append(entity_identifier)
                    continue

                try:
                    api.EnitityExistsInCategory(
                        category_name=policy_name, entity_identifier=entity_identifier
                    )
                    api.EditSharedUrlInCategory(
                        category_name=policy_name,
                        entity_identifier=entity_identifier,
                        action="set",
                    )

                    successful_entities.append(entity_identifier)
                except CategoryNotExistsException as err:
                    siemplify.LOGGER.error(f"Category wasn't found '{policy_name}'")
                    siemplify.LOGGER.exception(err)
                    raise Exception(
                        f'Shared category "{policy_name}" was not found in Palo Alto NGFW.'
                    )
                except AlreadyExistsException as err:
                    siemplify.LOGGER.error(
                        f"Entity already a part of group '{entity_identifier}'"
                    )
                    siemplify.LOGGER.exception(err)
                    existing_entities.append(entity_identifier)
                except Exception as err:
                    siemplify.LOGGER.error(f"Some errors occurred '{err}'")
                    siemplify.LOGGER.exception(err)
                    failed_entities.append(entity_identifier)

        if successful_entities:
            output_message = (
                "Successfully added the following URLs to the shared category '{}' in Palo "
                "Alto NGFW: {} \n".format(policy_name, ", ".join(successful_entities))
            )

            if failed_entities:
                output_message += (
                    "Action wasn't able to add the following URLs to the shared category '{}' "
                    "in Palo Alto NGFW: {}\n".format(
                        policy_name, ", ".join(failed_entities)
                    )
                )
        else:
            output_message = f"No URLs were added to the shared category '{policy_name}' in Palo Alto NGFW.\n"
            result_value = False

        if existing_entities:
            result_value = True
            output_message += (
                "The following URLs were already a part of the the shared category '{}' "
                "in Palo Alto NGFW: {}\n".format(
                    policy_name, ", ".join(existing_entities)
                )
            )

        json_results["success"] = successful_entities
        json_results["failure"] = failed_entities
        json_results["already_exist"] = existing_entities
        siemplify.result.add_result_json(json_results)

    except Exception as err:
        output_message = f'Error executing action "Block URLs". Reason: {err}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
