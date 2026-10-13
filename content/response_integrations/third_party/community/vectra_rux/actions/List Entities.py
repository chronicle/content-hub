from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    LIST_ENTITIES_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    URL_API_VERSION,
)
from ..core.UtilsManager import extract_fields, get_integration_params, validate_limit_param, validate_integer, process_action_parameter
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


def remove_api_version_from_url(entity):
    """Updates all URLs in the given entity by removing the API version substring.

    Args:
        entity (dict): A dictionary representing an entity with `detection_set` and `url` fields.

    Returns:
        entity (dict): The updated `entity` dictionary with URLs processed.

    """
    if entity.get("detection_set"):
        entity["detection_set"] = [
            url.replace(URL_API_VERSION, "") for url in entity.get("detection_set")
        ]
    if entity.get("url"):
        entity["url"] = entity.get("url").replace(URL_API_VERSION, "")
    return entity


@output_handler
def main():
    """List entities based on the query parameters.

    :param api_root: The base URL of the Vectra API
    :param client_id: The client ID to use for authentication
    :param client_secret: The client secret to use for authentication
    :param entity_type: The type of entity to retrieve
    :param limit: The number of results to retrieve
    :param order_by: The field to order the results by
    :param fields: The fields to include in the results
    :param name: The name of the entity to retrieve
    :param state: The state of the entity to retrieve
    :param last_timestamp_gte: The last detection timestamp to retrieve
    :param last_timestamp_lte: The last detection timestamp to exclude
    :param tags: The tags to include in the results
    :param note_modified_timestamp_gte: The note modified timestamp to retrieve

    :return: A JSON object containing the results of the query
    """
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameter
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Action Parameters
    entity_type = siemplify.extract_action_param(
        param_name="Entity Type",
        input_type=str,
        is_mandatory=True,
    ).lower()

    order_by = siemplify.extract_action_param(
        param_name="Order By",
        input_type=str,
        is_mandatory=False,
    )

    fields = siemplify.extract_action_param(
        param_name="Fields",
        input_type=str,
        is_mandatory=False,
    )

    name = siemplify.extract_action_param(
        param_name="Name",
        input_type=str,
        is_mandatory=False,
    )

    state = siemplify.extract_action_param(
        param_name="State",
        input_type=str,
        is_mandatory=False,
    )

    last_detection_timestamp_gte = siemplify.extract_action_param(
        param_name="Last Detection Timestamp GTE",
        input_type=str,
        is_mandatory=False,
    )

    last_detection_timestamp_lte = siemplify.extract_action_param(
        param_name="Last Detection Timestamp LTE",
        input_type=str,
        is_mandatory=False,
    )

    tags = siemplify.extract_action_param(
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
    )

    note_modified_timestamp_gte = siemplify.extract_action_param(
        param_name="Note Modified Timestamp GTE",
        input_type=str,
        is_mandatory=False,
    )

    is_prioritized = siemplify.extract_action_param(
        param_name="Prioritized",
        input_type=str,
        is_mandatory=False,
    )

    limit = siemplify.extract_action_param(
        param_name="Limit",
        input_type=str,
        is_mandatory=False,
    )

    order = siemplify.extract_action_param(
        param_name="Order",
        input_type=str,
        is_mandatory=False,
    )
    field = ",".join(json.loads(fields))
    if order == "Descending" and order_by and order_by != "None":
        order_by = "-" + order_by

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        limit = validate_integer(
            validate_limit_param(limit),
            zero_allowed=True,
            field_name="Limit",
        )
        state = state.lower() if state and state != "None" else None
        is_prioritized = is_prioritized.lower() if is_prioritized and is_prioritized != "None" else None
        tags = process_action_parameter(tags)
        if tags:
            tags = ",".join(tags)

        name = name.strip() if name else None
        last_detection_timestamp_gte = last_detection_timestamp_gte.strip() if last_detection_timestamp_gte else None
        last_detection_timestamp_lte = last_detection_timestamp_lte.strip() if last_detection_timestamp_lte else None
        note_modified_timestamp_gte = note_modified_timestamp_gte.strip() if note_modified_timestamp_gte else None

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )
        entities = vectra_manager.list_entities(
            entity_type=entity_type,
            limit=limit,
            ordering=order_by,
            fields=field,
            name=name,
            state=state,
            last_detection_timestamp_gte=last_detection_timestamp_gte,
            last_detection_timestamp_lte=last_detection_timestamp_lte,
            tags=tags,
            note_modified_timestamp_gte=note_modified_timestamp_gte,
            is_prioritized=is_prioritized,
        )

        if not entities:
            output_message = "No entities were found for the given parameters"
        else:
            output_message = (
                f"Successfully retrieved the details for {len(entities)} entities"
            )

            mendatory_fields = [
                "id",
                "type",
                "name",
                "severity",
                "state",
                "urgency_score",
                "attack_rating",
                "last_detection_timestamp",
                "last_modified_timestamp",
            ]

            if entity_type == "host":
                mendatory_fields.append("ip")
            entity_table = []
            for entity in entities:
                entity = remove_api_version_from_url(entity)
                entity_table.append(extract_fields(entity, mendatory_fields))

            siemplify.result.add_data_table(
                title="List Of Entities",
                data_table=construct_csv(entity_table),
            )

        siemplify.result.add_result_json(json.dumps(entities, indent=4))

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = f"{e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraRUXException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(
            f"{e}, while performing action {LIST_ENTITIES_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_ENTITIES_SCRIPT_NAME,
            e,
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("-----------------  Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
