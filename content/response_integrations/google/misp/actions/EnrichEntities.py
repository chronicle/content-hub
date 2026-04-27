from __future__ import annotations
from ..core.MISPManager import MISPManager
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_unixtime_to_datetime
from TIPCommon import extract_action_param, extract_configuration_param
from ..core.constants import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES_SCRIPT_NAME,
    ATTRIBUTES_LIMIT_DEFAULT,
    LAST,
    THREAT_LEVEL,
    LOW,
    ATTRIBUTE_INSIGHT_NAME,
    DATA_ATTRIBUTE_ENRICHMENT_PREFIX,
    ATTRIBUTE_TABLE_NAME,
)
from ..core.exceptions import MISPNotAcceptableParamError
from ..core.utils import (
    get_entity_original_identifier,
    string_to_multi_value,
    adjust_categories,
)

SUPPORTED_ENTITY_TYPES = [
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.DOMAIN,
    EntityTypes.USER,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_ENTITIES_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Root"
    )
    api_token = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Api Key"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        default_value=False,
        input_type=bool,
    )
    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    categories = adjust_categories(
        string_to_multi_value(
            extract_action_param(siemplify, param_name="Categories", print_value=True)
        )
    )
    filtering_condition = extract_action_param(
        siemplify,
        param_name="Filtering condition",
        print_value=True,
        default_value=LAST,
    )
    create_insights = extract_action_param(
        siemplify,
        param_name="Create Insights",
        default_value=True,
        print_value=True,
        input_type=bool,
    )
    threshold = extract_action_param(
        siemplify,
        param_name="Threat Level Threshold",
        print_value=True,
        default_value=str(THREAT_LEVEL[LOW]),
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    json_result = {}
    successful_entities, failed_entities, marked_as_suspicious = [], [], []

    try:
        manager = MISPManager(api_root, api_token, use_ssl, ca_certificate)

        limit = extract_action_param(
            siemplify,
            param_name="Number of attributes to return",
            print_value=True,
            input_type=int,
            default_value=ATTRIBUTES_LIMIT_DEFAULT,
        )

        if limit is not None and limit < 0:
            raise Exception(
                '"Number of attributes to return" parameter is non positive. This parameter needs to be positive.'
            )

        if threshold.lower() not in map(
            str, tuple(THREAT_LEVEL.keys()) + tuple(THREAT_LEVEL.values())
        ):
            raise MISPNotAcceptableParamError(
                "Threat Level",
                acceptable_strings=THREAT_LEVEL.keys(),
                acceptable_numbers=THREAT_LEVEL.values(),
            )
        threshold = int(
            THREAT_LEVEL[threshold.lower()] if not threshold.isdigit() else threshold
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)

            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                attributes = manager.get_attributes(
                    attribute_names=[entity_identifier], categories=categories
                )
                attributes = sorted(
                    attributes, key=lambda attribute: attribute.timestamp
                )
                if attributes:
                    main_attribute = (
                        attributes[0] if filtering_condition == LAST else attributes[-1]
                    )
                    event = manager.get_event_by_id(main_attribute.event_id)

                    siemplify.LOGGER.info(f"Enriching entity {entity_identifier}")
                    # Enrich the entity with event data
                    entity.additional_properties.update(event.to_enrichment_data())
                    # Enrich the entity with attribute data
                    entity.additional_properties.update(
                        main_attribute.to_enrichment_data(
                            use_prefix=True,
                            method="get_attribute_enrichment_data",
                            prefix=DATA_ATTRIBUTE_ENRICHMENT_PREFIX,
                        )
                    )

                    if main_attribute.comment and create_insights:
                        siemplify.LOGGER.info(
                            f"Adding attribute comment insight for entity {entity_identifier}"
                        )
                        siemplify.add_entity_insight(
                            entity,
                            ATTRIBUTE_INSIGHT_NAME.format(main_attribute.comment),
                            triggered_by="MISP",
                        )
                    # Add case wall table for entity
                    siemplify.result.add_entity_table(
                        ATTRIBUTE_TABLE_NAME.format(entity_identifier),
                        main_attribute.to_attributes_enrich_csv(),
                    )

                    if int(event.threat_level_id) <= int(threshold):
                        siemplify.LOGGER.info(
                            f"Threat level is {threshold}. Marking entity {entity_identifier} as suspicious."
                        )
                        entity.is_suspicious = True
                        marked_as_suspicious.append(entity_identifier)

                    successful_entities.append(entity)
                    entity.is_enriched = True

                    event.attributes = attributes
                    entity_json_result = event.to_json()  # original raw_data post

                    if limit is not None:
                        entity_json_result["Attribute"] = entity_json_result.get(
                            "Attribute"
                        )[:limit]

                    json_result[entity_identifier] = {"Event": entity_json_result}

                else:
                    failed_entities.append(entity)
                siemplify.LOGGER.info(f"Finish processing entity: {entity_identifier}")
            except Exception as err:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}.\n{err}."
                )
                siemplify.LOGGER.exception(err)
                failed_entities.append(entity)

        if json_result:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_result)
            )

        if successful_entities:
            siemplify.update_entities(successful_entities)
            output_message = (
                "Successfully enriched the following entities using {}:\n{}\n".format(
                    INTEGRATION_NAME,
                    "\n".join(
                        [
                            get_entity_original_identifier(entity)
                            for entity in successful_entities
                        ]
                    ),
                )
            )
            if failed_entities:
                output_message += "Action wasn’t able to enrich the following entities using {}:\n{}\n".format(
                    INTEGRATION_NAME,
                    "\n".join(
                        [
                            get_entity_original_identifier(entity)
                            for entity in failed_entities
                        ]
                    ),
                )
            if marked_as_suspicious:
                output_message += "The following attributes were marked as suspicious using {}:\n{}\n".format(
                    INTEGRATION_NAME, "\n".join(marked_as_suspicious)
                )
        else:
            result_value = False
            output_message = f"No entities were enriched in {INTEGRATION_NAME}"

    except Exception as e:
        output_message = (
            f"Error executing action {ENRICH_ENTITIES_SCRIPT_NAME}. Reason: {e}"
        )
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
