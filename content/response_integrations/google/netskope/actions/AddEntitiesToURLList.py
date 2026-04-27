from __future__ import annotations

from typing import Any

from ..core.datamodels import AddEntitiesResult
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from ..core.NetskopeManagerV2 import NetskopeManagerV2, NetskopeManagerV2Error
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param

INTEGRATION_NAME: str = "Netskope"
SCRIPT_NAME: str = f"{INTEGRATION_NAME} - Add Entities to URL List"


def _get_entities_to_add(
    entities_input: str | None, siemplify: SiemplifyAction
) -> set[str]:
    """Get entities to add from input and target entities."""
    entities_to_add: set[str] = set()

    if entities_input:
        entities_to_add.update(
            e.strip() for e in entities_input.split(",") if e.strip()
        )

    for entity in siemplify.target_entities:
        if entity.entity_type in [
            EntityTypes.URL,
            EntityTypes.ADDRESS,
            EntityTypes.DOMAIN,
        ]:
            entities_to_add.add(entity.identifier)

    return entities_to_add


def _add_entities_to_list(
    manager: NetskopeManagerV2,
    url_list_name: str,
    entities_to_add: set[str],
    deploy_changes: bool,
) -> tuple[str, bool, AddEntitiesResult | None]:
    """
    Add entities to a URL list and optionally deploy changes.
    Returns (output_message, result_value, add_entities_result).
    """
    list_data: dict[str, Any] = manager.get_url_list_data(url_list_name)
    list_id: int = list_data["id"]
    list_type: str = list_data.get("data", {}).get("type", "exact")

    successful_entities, failed_entities, last_response = (
        manager.add_entities_to_url_list(list_id, list_type, list(entities_to_add))
    )

    deployed = False
    deploy_error = ""
    if deploy_changes:
        try:
            manager.deploy_url_list_changes()
            deployed = True
        except NetskopeManagerV2Error as e:
            deploy_error = str(e)

    output_message = ""
    result_value = False

    if successful_entities:
        output_message += (
            "Successfully added the following entities to the "
            f"'{url_list_name}' list in Netskope: "
            f"{', '.join(successful_entities)}. "
        )
        if not deploy_changes:
            output_message += "Changes are pending deployment.\n"
        result_value = True

    if failed_entities:
        output_message += (
            "Action wasn't able to add the following entities to the "
            f"'{url_list_name}' in Netskope: "
            f"{', '.join(failed_entities)}.\n"
        )
        result_value = result_value or bool(successful_entities)

    if not successful_entities and not failed_entities:
        output_message = (
            f"None of the provided entities were added to the URL List "
            f"{url_list_name} in Netskope."
        )
        result_value = False

    if deploy_changes:
        if deployed:
            output_message += "All pending URL list changes were deployed.\n"
        else:
            output_message += (
                f"Failed to deploy URL list changes. Reason: {deploy_error}\n"
            )

    add_entities_result = None
    if last_response and successful_entities:
        add_entities_result = AddEntitiesResult(
            added_entities=successful_entities,
            failed_entities=failed_entities,
            url_list_name=url_list_name,
            modify_by=last_response.get("modify_by", ""),
            modify_time=last_response.get("modify_time", ""),
            pending=last_response.get("pending", 0),
        )

    return output_message, result_value, add_entities_result


@output_handler
def main() -> None:
    """
    Add entities from input parameters and supported entity types
    to a specific Netskope URL list.

    Raises:
        Exception: If no entities are provided or found in target
            entities, or if API operations fail.
    """
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    result_value = False

    try:

        url_list_name = extract_action_param(
            siemplify, param_name="URL List Name", is_mandatory=True, print_value=True
        )
        entities_input = extract_action_param(
            siemplify, param_name="Entries", is_mandatory=False, print_value=True
        )
        deploy_changes = extract_action_param(
            siemplify,
            param_name="Deploy URL List Changes",
            is_mandatory=False,
            default_value=False,
            input_type=bool,
            print_value=True,
        )
        entities_to_add: set[str] = _get_entities_to_add(entities_input, siemplify)

        siemplify.LOGGER.info("Starting to perform the action")

        if not entities_to_add:
            output_message = (
                f"None of the provided entities were added to the "
                f"URL List {url_list_name} in Netskope."
            )
            result_value = False
            status = EXECUTION_STATE_COMPLETED

        else:
            manager = NetskopeManagerFactory.get_manager(siemplify, api_version="v2")
            try:
                output_message, result_value, add_entities_result = (
                    _add_entities_to_list(
                        manager, url_list_name, entities_to_add, deploy_changes
                    )
                )
                siemplify.LOGGER.info("Finished performing the action")
                if add_entities_result:
                    siemplify.result.add_result_json(add_entities_result.to_json())
                status = EXECUTION_STATE_COMPLETED

            except NetskopeManagerV2Error as e:
                if f"URL List '{url_list_name}' not found." in str(e):
                    output_message = (
                        f"Error: URL List '{url_list_name}' was not found "
                        f"in Netskope. Please check the spelling."
                    )
                else:
                    output_message = f"Error executing action. Reason: {e}"

                siemplify.LOGGER.error(output_message)
                siemplify.LOGGER.exception(e)
                status = EXECUTION_STATE_FAILED
                result_value = False
                siemplify.end(output_message, result_value, status)
                return

    except Exception as e:  # pylint: disable=broad-exception-caught
        output_message = f"Error executing action. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
