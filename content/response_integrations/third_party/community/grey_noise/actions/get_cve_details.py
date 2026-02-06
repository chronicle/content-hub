from __future__ import annotations

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    INTEGRATION_NAME,
    GET_CVE_DETAILS_SCRIPT_NAME,
    NO_CVE_ENTITIES_ERROR,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import (
    get_integration_params,
    get_cve_entities,
    validate_cve_format,
    generate_cve_insight,
)
from ..core.datamodels import CVEResult


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CVE_DETAILS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key = get_integration_params(siemplify)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    successful_entities = []
    failed_entities = []
    not_found_entities = []
    json_results = []

    try:
        # Initialize GreyNoise manager
        greynoise_manager = APIManager(api_key, siemplify=siemplify)

        # Get CVE entities
        cve_entities = get_cve_entities(siemplify)

        if not cve_entities:
            output_message = NO_CVE_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(json_results)
            siemplify.end(output_message, result_value, status)
            return

        siemplify.LOGGER.info(f"Found {len(cve_entities)} CVE entities to process")

        # Process each CVE entity
        for entity in cve_entities:
            cve_id = entity.identifier.upper()
            siemplify.LOGGER.info(f"Processing CVE: {cve_id}")

            try:
                # Validate CVE format
                validate_cve_format(cve_id)

                # Perform CVE lookup
                cve_response = greynoise_manager.cve_lookup(cve_id)
                if cve_response and isinstance(cve_response, dict):
                    # Create CVE result model for better data handling
                    cve_result = CVEResult(cve_response)

                    # Add enrichment data to entity using datamodel
                    entity.additional_properties.update(cve_result.get_enrichment_data())

                    entity.is_enriched = True
                    successful_entities.append(entity)
                    json_results.append(cve_response)

                    # Create Insight
                    insight_html = generate_cve_insight(cve_response, cve_id)
                    if insight_html:
                        siemplify.add_entity_insight(
                            entity, insight_html, triggered_by=INTEGRATION_NAME
                        )

                    siemplify.LOGGER.info(f"Successfully processed CVE: {cve_id}")
                else:
                    not_found_entities.append(entity)
                    siemplify.LOGGER.info(f"No data found for CVE: {cve_id}")

            except ValueError as e:
                # CVE format validation error
                output_message = f"Invalid parameter value: {e}."
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Invalid parameter value: {str(e)}")
                continue

            except RequestFailure as e:
                # API request failed
                output_message = f"Failed to connect to the GreyNoise server: {str(e)}"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"API request failed for {cve_id}: {str(e)}")
                continue

            except Exception as e:
                # General error
                output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_CVE_DETAILS_SCRIPT_NAME, e)
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Error processing {cve_id}: {str(e)}")
                continue

        # Prepare output message
        if successful_entities:
            entities_names = ", ".join([entity.identifier for entity in successful_entities])
            output_message += (
                f"\nSuccessfully processed {len(successful_entities)} CVE(s): {entities_names}"
            )
            siemplify.update_entities(successful_entities)

        if not_found_entities:
            entities_names = ", ".join(
                [entity.identifier for entity in not_found_entities]
            )
            output_message += (
                f"\nNot found in GreyNoise dataset: {len(not_found_entities)} CVE(s): {entities_names}"
            )

        if failed_entities:
            entities_names = ", ".join(
                [entity.identifier for entity in failed_entities]
            )
            output_message += (
                f"\nFailed to process {len(failed_entities)} CVE(s): {entities_names}"
            )

        if not successful_entities and not not_found_entities:
            output_message = f"Failed to process all {len(failed_entities)} CVE(s): {entities_names}"
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except RateLimitError as e:
        output_message = f"Rate limit reached: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_CVE_DETAILS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json_results)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
