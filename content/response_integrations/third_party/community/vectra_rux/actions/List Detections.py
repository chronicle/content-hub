from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    LIST_DETECTIONS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    URL_API_VERSION,
)
from ..core.UtilsManager import (
    extract_fields, 
    get_integration_params, 
    validate_limit_param, 
    validate_integer, 
    process_action_parameter,
)
from ..core.VectraRUXExceptions import InvalidIntegerException, VectraRUXException
from ..core.VectraRUXManager import VectraRUXManager


def remove_api_version_from_url(detection):
    """Updates all URLs in the given detection by removing the API version substring.

    Args:
        detection (dict): A dictionary of detections.

    Returns:
        entity (dict): The updated `detection` dictionary with URLs processed.

    """
    if detection.get("url"):
        detection["url"] = detection.get("url").replace(URL_API_VERSION, "")
    if detection.get("detection_url"):
        detection["detection_url"] = detection.get("detection_url").replace(
            URL_API_VERSION,
            "",
        )
    if detection["src_account"]:
        detection["src_account"]["url"] = detection["src_account"]["url"].replace(
            URL_API_VERSION,
            "",
        )
    elif detection["src_host"]:
        detection["src_host"]["url"] = detection["src_host"]["url"].replace(
            URL_API_VERSION,
            "",
        )
    return detection


def get_src_fields(response):
    result = {}
    if response.get("src_account"):
        result["src_account_name"] = response.get("src_account").get("name")

    if response.get("src_host"):
        result["src_host_name"] = response.get("src_host").get("name")
        result["src_host_ip"] = response.get("src_host").get("ip")

    return result


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
    siemplify.script_name = LIST_DETECTIONS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameter
    api_root, client_id, client_secret = get_integration_params(siemplify)

    # Action Parameters
    order_by = siemplify.extract_action_param(
        param_name="Order By",
        input_type=str,
        is_mandatory=False,
    )
    state = siemplify.extract_action_param(
        param_name="State",
        input_type=str,
        is_mandatory=False,
    )
    detection_type = siemplify.extract_action_param(
        param_name="Detection Type",
        input_type=str,
        is_mandatory=False,
    )
    detection_category = siemplify.extract_action_param(
        param_name="Detection Category",
        input_type=str,
        is_mandatory=False,
    )
    threat_gte = siemplify.extract_action_param(
        param_name="Threat GTE",
        input_type=str,
        is_mandatory=False,
    )
    certainty_gte = siemplify.extract_action_param(
        param_name="Certainty GTE",
        input_type=str,
        is_mandatory=False,
    )
    last_timestamp_gte = siemplify.extract_action_param(
        param_name="Last Timestamp GTE",
        input_type=str,
        is_mandatory=False,
    )
    last_timestamp_lte = siemplify.extract_action_param(
        param_name="Last Timestamp LTE",
        input_type=str,
        is_mandatory=False,
    )
    tags = siemplify.extract_action_param(
        param_name="Tags",
        input_type=str,
        is_mandatory=False,
    )
    is_targeting_key_asset = siemplify.extract_action_param(
        param_name="Is Targeting Key Asset",
        input_type=str,
        is_mandatory=False,
    )
    note_modified_timestamp_gte = siemplify.extract_action_param(
        param_name="Note Modified Timestamp GTE",
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
    entity_type = siemplify.extract_action_param(
        param_name="Entity Type",
        input_type=str,
        is_mandatory=False,
    )
    entity_id = siemplify.extract_action_param(
        param_name="Entity ID",
        input_type=str,
        is_mandatory=False,
    )
    if order_by:
        order_by = order_by.replace("_score", "")
    if order == "Descending" and order_by and order_by != "None":
        order_by = "-" + order_by

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if threat_gte:
            threat_gte = validate_integer(
                threat_gte,
                zero_allowed=True,
                field_name="Threat GTE",
            )
            
        if certainty_gte:
            certainty_gte = validate_integer(
                certainty_gte,
                zero_allowed=True,
                field_name="Certainty GTE",
            )
            
        if entity_id:
            entity_id = validate_integer(entity_id, field_name="Entity ID")

        limit = validate_integer(
            validate_limit_param(limit),
            zero_allowed=True,
            field_name="Limit",
        )
        state = state.lower() if state and state != "None" else None
        is_targeting_key_asset = (
            is_targeting_key_asset.lower() if is_targeting_key_asset and is_targeting_key_asset != "None" else None
        )
        detection_category = (
            detection_category.split()[0].lower() if detection_category and detection_category != "None" else None
        )
        entity_type = entity_type.lower() if entity_type and entity_type != "None" else None
        tags = process_action_parameter(tags)
        if tags:
            tags = ",".join(tags)

        detection_type = detection_type.strip() if detection_type else None
        last_timestamp_gte = last_timestamp_gte.strip() if last_timestamp_gte else None
        last_timestamp_lte = last_timestamp_lte.strip() if last_timestamp_lte else None
        note_modified_timestamp_gte = note_modified_timestamp_gte.strip() if note_modified_timestamp_gte else None

        vectra_manager = VectraRUXManager(
            api_root,
            client_id,
            client_secret,
            siemplify=siemplify,
        )
        detections = vectra_manager.list_detections(
            limit=limit,
            type=entity_type,
            entity_id=entity_id,
            ordering=order_by,
            state=state,
            threat_gte=threat_gte,
            certainty_gte=certainty_gte,
            detection_type=detection_type,
            detection_category=detection_category,
            tags=tags,
            is_targeting_key_asset=is_targeting_key_asset,
            last_timestamp_gte=last_timestamp_gte,
            last_timestamp_lte=last_timestamp_lte,
            note_modified_timestamp_gte=note_modified_timestamp_gte,
        )

        if not detections:
            output_message = "No detections were found for the provided parameters"
        else:
            output_message = (
                f"Successfully retrieved the details for {len(detections)} detections"
            )

            mendatory_fields = [
                "id",
                "detection_type",
                "detection_category",
                "first_timestamp",
                "last_timestamp",
                "state",
            ]

            detection_table = []
            for detection in detections:
                detection = remove_api_version_from_url(detection)
                detection_table.append(
                    {
                        **extract_fields(detection, mendatory_fields),
                        **get_src_fields(detection),
                    },
                )

            siemplify.result.add_data_table(
                title="List Of Detections",
                data_table=construct_csv(detection_table),
            )

        siemplify.result.add_result_json(json.dumps(detections, indent=4))
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
            f"{e}, while performing action {LIST_DETECTIONS_SCRIPT_NAME}",
        )
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = RESULT_VALUE_FALSE
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            LIST_DETECTIONS_SCRIPT_NAME,
            e,
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
