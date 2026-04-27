from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.IBossManager import IBossManager
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    add_prefix_to_dict,
)
from ..core.constants import (
    REMOVE_URL_FROM_POLICY_BLOCK_LIST_SCRIPT_NAME,
    INTEGRATION_NAME,
    POLICY_BLOCKED_ENRICHMENT_NAME,
    ENRICHMENT_PREFIX,
)
from ..core.exceptions import ListIsNotBlockListException
from ..core.UtilsManager import strip_scheme


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_URL_FROM_POLICY_BLOCK_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration
    cloud_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Cloud API Root",
        is_mandatory=True,
    )
    account_api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account API Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    category_id = extract_action_param(
        siemplify, param_name="Category ID", is_mandatory=True, print_value=True
    )
    start_port = extract_action_param(
        siemplify, param_name="Start Port", input_type=int, print_value=True
    )
    end_port = extract_action_param(
        siemplify, param_name="End Port", input_type=int, print_value=True
    )
    is_strip_scheme = extract_action_param(
        siemplify, param_name="Strip Scheme", input_type=bool, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    enriched_entities = []
    output_message = ""
    failed_entities = []
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
        or entity.entity_type == EntityTypes.HOSTNAME
    ]
    try:
        manager = IBossManager(
            cloud_api_root,
            account_api_root,
            username,
            password,
            verify_ssl,
            siemplify.LOGGER,
        )
        manager.validate_if_block_list(category_id)

        for entity in suitable_entities:
            try:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {entity.identifier}"
                )

                url = (
                    strip_scheme(entity.identifier)
                    if is_strip_scheme
                    else entity.identifier
                )

                manager.remove_url_from_policy_block_list(
                    url.lower(), category_id, start_port, end_port
                )
                enriched_entities.append(entity)
                entity.additional_properties.update(
                    add_prefix_to_dict(
                        {POLICY_BLOCKED_ENRICHMENT_NAME: "False"}, ENRICHMENT_PREFIX
                    )
                )
                entity.is_enriched = True
                siemplify.LOGGER.info(
                    f"Successfully removed the following entity:  \n {entity.identifier}"
                )
            except Exception as e:
                failed_entities.append(entity.identifier)
                if entity.identifier not in enriched_entities:
                    siemplify.LOGGER.error(
                        f"Action was not able to remove the following entity:  \n {entity.identifier}"
                    )
                else:
                    siemplify.LOGGER.error(
                        "Failed to add enrichment field "
                        f"{POLICY_BLOCKED_ENRICHMENT_NAME} to entity: "
                        f"{entity.identifier}"
                    )
                siemplify.LOGGER.exception(e)
            siemplify.LOGGER.info(f"Finished processing entity: {entity.identifier}")

        if failed_entities:
            output_message += (
                "Action was not able to remove the following entities from the "
                "category with ID {}: \n{}\n"
            ).format(
                category_id, "\n".join(failed_entities)
            )

        if enriched_entities:
            output_message += (
                "Successfully removed the following entities from the iBoss category "
                "with ID {} \n{}\n"
            ).format(
                category_id,
                "\n".join([entity.identifier for entity in enriched_entities]),
            )
            siemplify.update_entities(enriched_entities)

        else:
            output_message = (
                "No entities were removed from the iBoss category with ID "
                f"{category_id}."
            )
            siemplify.LOGGER.info(output_message)
            result_value = False

    except ListIsNotBlockListException:
        output_message = (
            f"Category with ID {category_id} is not associated with a Block list."
        )
        siemplify.LOGGER.info(output_message)
        result_value = False
    except Exception as e:
        output_message = (
            "Error executing action "
            f"'{REMOVE_URL_FROM_POLICY_BLOCK_LIST_SCRIPT_NAME}'. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
