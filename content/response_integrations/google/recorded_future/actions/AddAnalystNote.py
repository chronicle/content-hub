from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.RecordedFutureManager import RecordedFutureManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.constants import PROVIDER_NAME, ADD_ANALYST_NOTE_SCRIPT_NAME, TOPIC_MAP
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import RecordedFutureUnauthorizedError
from ..core.UtilsManager import (
    get_entity_original_identifier,
    get_recorded_future_id,
    get_recorded_future_document_id,
)

SUITABLE_ENTITY_TYPES = [
    EntityTypes.HOSTNAME,
    EntityTypes.CVE,
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ANALYST_NOTE_SCRIPT_NAME

    api_url = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiUrl"
    )
    api_key = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="ApiKey"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    note_title = extract_action_param(
        siemplify, param_name="Note Title", is_mandatory=True
    )
    note_text = extract_action_param(
        siemplify, param_name="Note Text", is_mandatory=True
    )
    note_source = extract_action_param(
        siemplify, param_name="Note Source", is_mandatory=True
    )
    topic = extract_action_param(
        siemplify, param_name="Topic", default_value=TOPIC_MAP["None"]
    )
    enrich_entity = extract_action_param(
        siemplify, param_name="Enrich Entity?", default_value=True, input_type=bool
    )

    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUITABLE_ENTITY_TYPES
    ]
    entities_should_enrich = [
        entity for entity in suitable_entities if not get_recorded_future_id(entity)
    ]
    enriched_entities = [
        entity for entity in suitable_entities if get_recorded_future_id(entity)
    ]
    enriched_entity_ids = [
        get_recorded_future_id(entity)
        for entity in suitable_entities
        if get_recorded_future_id(entity)
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, recorded_future_ids = [], [], []

    try:
        manager = RecordedFutureManager(
            api_url=api_url, api_key=api_key, verify_ssl=verify_ssl
        )
        entity_common_objects = manager.get_ioc_related_entity_objects(
            entities_should_enrich
        )

        for entity in entities_should_enrich:

            if entity_common_objects.get(get_entity_original_identifier(entity)):
                successful_entities.append(entity)
                recorded_future_ids.append(
                    entity_common_objects.get(
                        get_entity_original_identifier(entity)
                    ).entity_id
                )
                if enrich_entity:
                    entity.additional_properties.update(
                        entity_common_objects.get(
                            get_entity_original_identifier(entity)
                        ).to_enrichment_data()
                    )
            else:
                failed_entities.append(entity)

        successful_entities += enriched_entities
        recorded_future_ids += enriched_entity_ids

        if successful_entities:
            entity_analyst_object = manager.get_analyst_notes(
                ids=recorded_future_ids,
                title=note_title,
                text=note_text,
                topic=TOPIC_MAP[topic],
                source=note_source,
            )

            for entity in successful_entities:
                siemplify.LOGGER.info(
                    f"\n\nStarted processing entity: {get_entity_original_identifier(entity)}"
                )

                document_id = entity_analyst_object.document_id

                if get_recorded_future_document_id(entity):
                    document_id += ", " + get_recorded_future_document_id(entity)

                entity.additional_properties.update(
                    entity_analyst_object.to_enrichment_data(document_id=document_id)
                )
                entity.is_enriched = True
                siemplify.LOGGER.info(
                    f"Finished processing entity: {get_entity_original_identifier(entity)}"
                )

            siemplify.update_entities(successful_entities)
            output_message += (
                "\nSuccessfully published analyst note for the following entities in Recorded Future: "
                "\n {0}".format(
                    "\n ".join(
                        [
                            get_entity_original_identifier(entity)
                            for entity in successful_entities
                        ]
                    )
                )
            )

        if failed_entities:
            output_message += (
                "\nFollowing entities do not exist in Recorded Future: \n {0}".format(
                    "\n ".join(
                        [
                            get_entity_original_identifier(entity)
                            for entity in failed_entities
                        ]
                    )
                )
            )

        if not successful_entities:
            output_message = (
                "\nRecorded Future couldn’t find any of the entities provided in the “Enrich IOC”, "
                "and thus, couldn’t publish the analyst note."
            )
            status = EXECUTION_STATE_FAILED
            result_value = False

    except Exception as err:
        output_message = (
            f"Error executing action {ADD_ANALYST_NOTE_SCRIPT_NAME}. Reason: {err}"
        )
        if isinstance(err, RecordedFutureUnauthorizedError):
            output_message = (
                "Unauthorized - please check your API token and try again. {}"
            )
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
