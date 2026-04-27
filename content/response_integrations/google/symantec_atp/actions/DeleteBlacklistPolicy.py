# coding=utf-8
from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.SymantecATPManager import (
    SymantecATPManager,
    SymantecATPBlacklistPolicyNotFoundError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes

# =====================================
#             CONSTANTS               #
# =====================================
SCRIPT_NAME = "SymantecATP_Delete Blacklist Policy"
INTEGRATION_NAME = "SymantecATP"
SUPPORTED_ENTITY_TYPES = [EntityTypes.URL, EntityTypes.FILEHASH, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    output_message = ""
    is_success = "true"
    successfully_deleted_entities = []
    not_found_entities = []
    status = EXECUTION_STATE_COMPLETED
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Integration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    target_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        atp_manager = SymantecATPManager(api_root, client_id, client_secret, verify_ssl)

        for entity in target_entities:
            try:
                atp_manager.delete_blacklist_policy_by_identifier(
                    entity.identifier, SCRIPT_NAME
                )
                successfully_deleted_entities.append(entity)
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

            except SymantecATPBlacklistPolicyNotFoundError as e:
                not_found_entities.append(entity)
                siemplify.LOGGER.info(
                    f"Blacklist policy for entity {entity.identifier} was not found."
                )

            except Exception as e:
                raise e

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        output_message += f"Error executing action Delete BlackList Policy. Reason: {e}"
        is_success = "false"

    if successfully_deleted_entities:
        entities_names = [entity.identifier for entity in successfully_deleted_entities]
        output_message += "Successfully deleted the following entities from Symantec ATP blacklist policy: \n{}\n".format(
            "\n".join(entities_names)
        )
    else:
        # None of the processed entities were found in ATP
        output_message += "No policies were deleted."
        is_success = "false"

    if not_found_entities and successfully_deleted_entities:
        entities_names = [entity.identifier for entity in not_found_entities]
        output_message += "The following entities were not found in the Symantec ATP blacklist policies: \n{}\n".format(
            "\n".join(entities_names)
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
