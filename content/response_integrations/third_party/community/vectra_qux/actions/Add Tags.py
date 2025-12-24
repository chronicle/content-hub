from __future__ import annotations

import json

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import construct_csv, extract_action_param, extract_configuration_param

from ..core.constants import (
    ADD_TAGS_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    ENTITY_ID,
    ENTITY_TYPE,
    INTEGRATION_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import validate_integer
from ..core.VectraQUXExceptions import (
    InvalidIntegerException,
    ItemNotFoundException,
    VectraQUXException,
)
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_TAGS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameter
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    tags = extract_action_param(
        siemplify,
        param_name="Tags",
        input_type=str,
        is_mandatory=True,
    )
    entity_ids = extract_action_param(
        siemplify,
        param_name="Entity IDs",
        input_type=str,
        is_mandatory=True,
    )
    entity_type = extract_action_param(
        siemplify,
        param_name=ENTITY_TYPE,
        input_type=str,
        is_mandatory=True,
    ).lower()

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    # Creating list of tags and remove duplicate tags
    new_tags = list({tag.strip() for tag in tags.split(",") if tag.strip()})

    try:
        # Creating list of entity ids and remove duplicate entity ids
        entities = list(
            {
                str(validate_integer(entity_id.strip(), field_name="Entity IDs"))
                for entity_id in entity_ids.split(",")
                if entity_id.strip()
            },
        )

        vectra_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # Store the entity Ids if not able to add tags
        failure_ids = []
        # Store the json response for each entity
        result_table = []
        # Store the entity Ids for which tag added Successfully
        success_ids = []

        for entity_id in entities:
            try:
                # Fetching Existing Tags for the Entity
                entity_tags = vectra_manager.get_entity_tags(
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                if entity_tags is None:
                    raise ItemNotFoundException(
                        f"{entity_type} with ID {entity_id} was not found",
                    )

                # Adding new tags only if they are not already exist
                updated_tags = list(set(entity_tags + new_tags))

                # Updating the tags
                response = vectra_manager.update_tags(
                    entity_type,
                    entity_id,
                    updated_tags,
                )
                success_ids.append(entity_id)
                result_table.append(
                    {
                        ENTITY_ID: entity_id,
                        ENTITY_TYPE: entity_type,
                        "Status": response.get("status"),
                        "Tags": response.get("tags"),
                    },
                )

                # Logging
                siemplify.LOGGER.info(f"Successfully Added Tags to {entity_id}")

            except ItemNotFoundException as e:
                siemplify.LOGGER.error(f"{entity_type}-{entity_id} - {e}")
                result_table.append(
                    {
                        ENTITY_ID: entity_id,
                        ENTITY_TYPE: entity_type,
                        "Status": "failed",
                        "Tags": None,
                    },
                )
                failure_ids.append(entity_id)

            except VectraQUXException as e:
                raise VectraQUXException(e)
            except Exception as e:
                siemplify.LOGGER.error(f"Unexpected error for {entity_id}: {e}")
                result_table.append(
                    {
                        ENTITY_ID: entity_id,
                        ENTITY_TYPE: entity_type,
                        "Status": "failed",
                        "Tags": None,
                    },
                )
                failure_ids.append(entity_id)

        if success_ids:
            output_message = f'Successfully added tag(s) to {entity_type}(s): "{", ".join(success_ids)}".'
            if failure_ids:
                output_message += f' Failed to add tag(s) to {entity_type}(s): "{", ".join(failure_ids)}". Check logs for more details.'
            siemplify.result.add_result_json(json.dumps(result_table))
            siemplify.result.add_data_table(
                title="Tag Update Status",
                data_table=construct_csv(result_table),
            )
        else:
            output_message = (
                f'Failed to add tag(s) to {entity_type}(s): "{", ".join(failure_ids)}"'
            )
            status = EXECUTION_STATE_FAILED
            result_value = RESULT_VALUE_FALSE

    except InvalidIntegerException as e:
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
    except VectraQUXException as e:
        output_message = f"VectraQUXExceptions Occured: {e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ADD_TAGS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"is_success: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
