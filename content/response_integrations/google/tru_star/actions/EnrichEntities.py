from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from ..core.TruSTARManager import TruSTARManager
from ..core.consts import (
    INTEGRATION_NAME,
    ENRICH_ENTITIES,
    DEFAULT_SECURITY_LEVEL_THRESHOLD,
    ENCLAVE_FILTERS,
    SECURITY_LEVEL_MAPPING,
    REPORT_LINK,
)
from ..core.exceptions import TruSTARValidationException, TruSTARNoDataException

from ..core.utils import (
    load_csv_to_list,
    get_entity_summaries_dict,
    get_max_indicator_severity,
    convert_to_base64,
)

# Fix misalignment of MAC entity type
EntityTypes.MACADDRESS = EntityTypes.MACADDRESS.upper()


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ENRICH_ENTITIES}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
        print_value=True,
    )

    api_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret",
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=True,
        is_mandatory=True,
        print_value=True,
    )

    security_level_threshold = extract_action_param(
        siemplify,
        param_name="Security Level Threshold",
        input_type=str,
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_SECURITY_LEVEL_THRESHOLD,
    )

    enclave_filter = extract_action_param(
        siemplify,
        param_name="Enclave Filter",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    result_value = False
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    enriched_entities_identifiers = []
    enriched_entities = []
    failed_to_enrich_entities_identifiers = []
    json_results = {}
    csv_list = []

    try:
        manager = TruSTARManager(
            api_root=api_root,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
        )

        enclave_filter_list = (
            load_csv_to_list(enclave_filter, ENCLAVE_FILTERS) if enclave_filter else []
        )

        siemplify.LOGGER.info("Fetching enclaves")
        enclaves = manager.list_enclaves()
        fetched_enclaves_names = [enclave.name for enclave in enclaves]
        provided_enclaves_ids = [
            enc.id for enc in enclaves if enc.name in enclave_filter_list
        ]

        missing_enclaves = []
        for enclave_name in enclave_filter_list:
            if enclave_name not in fetched_enclaves_names:
                missing_enclaves.append(enclave_name)

        if enclave_filter_list and missing_enclaves:
            missing_enclaves_str = ", ".join(missing_enclaves)
            raise TruSTARValidationException(
                f"The following enclaves were not found: {missing_enclaves_str}. Please check the spelling or use the "
                f"action 'List Enclaves' to find the valid enclaves."
            )

        siemplify.LOGGER.info("Start processing entities")
        entities_identifiers = [
            entity.identifier.strip() for entity in siemplify.target_entities
        ]

        # Prepare the entities identifiers for the API cal. [{'value': identifier}]
        entities_identifiers_dict = [
            {"value": entity_identifier} for entity_identifier in entities_identifiers
        ]

        siemplify.LOGGER.info("Fetching indicators metadata information")
        indicators_metadata_list = manager.get_metadata_info(
            entities_identifiers_dict, provided_enclaves_ids
        )
        indicators_metadata_dict = {
            indicator.value: indicator for indicator in indicators_metadata_list
        }
        siemplify.LOGGER.info("Successfully fetched indicators metadata information")

        siemplify.LOGGER.info("Fetching indicators summary information")
        indicators_summary_list = manager.get_indicators_summary(
            entities_identifiers, provided_enclaves_ids
        )
        indicators_summary_dict = get_entity_summaries_dict(
            indicators_summary_list=indicators_summary_list
        )
        siemplify.LOGGER.info("Successfully fetched indicators summary information")

        for entity in siemplify.target_entities:
            try:
                siemplify.LOGGER.info(
                    f"Processing entity with identifier: {entity.identifier}"
                )
                indicator_entity_metadata = indicators_metadata_dict.get(
                    entity.identifier
                )

                if not indicator_entity_metadata:
                    raise TruSTARNoDataException(
                        f"No data available for entitiy: {entity.identifier}"
                    )

                # JSON handling
                json_results[entity.identifier] = indicator_entity_metadata.as_json(
                    [
                        summary.as_json()
                        for summary in indicators_summary_dict.get(
                            entity.identifier, []
                        )
                    ]
                )

                siemplify.LOGGER.info(
                    f"Enriching entity with identifier {entity.identifier}"
                )
                max_severity = get_max_indicator_severity(
                    indicators_summary_dict.get(entity.identifier, [])
                )
                entity.additional_properties.update(
                    indicator_entity_metadata.as_enrichment(max_severity)
                )
                entity.is_enriched = True
                siemplify.LOGGER.info(
                    f"Successfully enriched entity with identifier {entity.identifier}"
                )

                siemplify.LOGGER.info(
                    f"Adding insight to entity with identifier {entity.identifier}"
                )
                siemplify.add_entity_insight(
                    entity, indicator_entity_metadata.as_insight(max_severity)
                )
                siemplify.LOGGER.info(
                    f"Successfully added insight to entity with identifier {entity.identifier}"
                )

                siemplify.LOGGER.info(
                    f"Adding link to entity with identifier {entity.identifier}"
                )
                siemplify.result.add_entity_link(
                    entity.identifier,
                    REPORT_LINK.format(
                        convert_to_base64(indicator_entity_metadata.guid)
                    ),
                )
                siemplify.LOGGER.info(
                    f"Successfully added link to entity with identifier {entity.identifier}"
                )

                siemplify.LOGGER.info("Checking if the entity is suspicious")
                if max_severity and max_severity >= SECURITY_LEVEL_MAPPING.get(
                    security_level_threshold.upper(), "HIGH"
                ):
                    siemplify.LOGGER.info(
                        "Entity severity level is above the threshold and will be marked as suspicious"
                    )
                    entity.is_suspicious = True

                # CSV handling
                siemplify.result.add_entity_table(
                    entity.identifier.strip(),
                    construct_csv([indicator_entity_metadata.as_csv(max_severity)]),
                )

                enriched_entities_identifiers.append(entity.identifier)
                enriched_entities.append(entity)

            except Exception as error:
                siemplify.LOGGER.error(f"Fail to enrich entity. Reason is: {error}")
                failed_to_enrich_entities_identifiers.append(entity.identifier)

        if enriched_entities_identifiers:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            siemplify.update_entities(enriched_entities)
            result_value = True
            enriched_entities_identifiers_str = ", ".join(enriched_entities_identifiers)
            output_message += (
                f"Successfully enriched the following entities using TruSTAR:\n"
                f"{enriched_entities_identifiers_str}\n"
            )

        if failed_to_enrich_entities_identifiers:
            failed_to_enrich_entities_identifiers_str = ", ".join(
                failed_to_enrich_entities_identifiers
            )
            output_message += (
                f"Action wasn't able to enrich the following entities using TruSTAR:\n"
                f"{failed_to_enrich_entities_identifiers_str}\n"
            )

        if not enriched_entities_identifiers:
            output_message = "No entities were enriched.\n"

        status = EXECUTION_STATE_COMPLETED

    except TruSTARValidationException as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{ENRICH_ENTITIES}'. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = f"Error executing action '{ENRICH_ENTITIES}'. Reason: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
