from __future__ import annotations

from greynoise.exceptions import RateLimitError, RequestFailure
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    INTEGRATION_NAME,
    IP_TIMELINE_LOOKUP_SCRIPT_NAME,
    NO_IP_ENTITIES_ERROR,
    NO_TIMELINE_DATA_ERROR,
    RESULT_VALUE_TRUE,
    RESULT_VALUE_FALSE,
    COMMON_ACTION_ERROR_MESSAGE,
)
from ..core.utils import (
    get_integration_params,
    get_ip_entities,
    generate_timeline_insight,
    validate_integer_param,
)
from ..core.datamodels import IPTimelineResult
from ..core.greynoise_exceptions import (
    InvalidIntegerException,
    InvalidGranularityException,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = IP_TIMELINE_LOOKUP_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configuration Parameters
    api_key = get_integration_params(siemplify)

    # Action Parameters
    days = siemplify.extract_action_param(
        "Days", print_value=True, default_value="30", input_type=str
    )
    field = siemplify.extract_action_param(
        "Field", print_value=True, default_value="classification"
    )
    granularity = siemplify.extract_action_param(
        "Granularity", print_value=True, default_value="1d"
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE
    output_message = ""
    successful_entities = []
    failed_entities = []
    json_results = []

    try:
        # Validate integer parameters
        days = validate_integer_param(days, "Days", zero_allowed=False, allow_negative=False)

        # Initialize GreyNoise manager
        greynoise_manager = APIManager(api_key, siemplify=siemplify)

        # Get IP entities
        ip_entities = get_ip_entities(siemplify)

        if not ip_entities:
            output_message = NO_IP_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            siemplify.LOGGER.info(output_message)
            siemplify.result.add_result_json(json_results)
            siemplify.end(output_message, result_value, status)
            return

        siemplify.LOGGER.info(f"Found {len(ip_entities)} IP entities to process")

        # Process each IP entity
        for entity in ip_entities:
            ip_address = entity.identifier
            siemplify.LOGGER.info(f"Processing IP: {ip_address}")

            try:
                # Perform Timeline lookup
                timeline_response = greynoise_manager.ip_timeline(
                    ip_address, days=days, field=field, granularity=granularity
                )

                if timeline_response:
                    # Create Timeline result model
                    timeline_result = IPTimelineResult(timeline_response)

                    # Add enrichment data to entity using datamodel
                    entity.additional_properties.update(timeline_result.get_enrichment_data())

                    entity.is_enriched = True
                    successful_entities.append(entity)
                    json_results.append(timeline_response)

                    # Create Insight
                    insight_html = generate_timeline_insight(timeline_response, ip_address)
                    if insight_html:
                        siemplify.add_entity_insight(
                            entity, insight_html, triggered_by=INTEGRATION_NAME
                        )

                    siemplify.LOGGER.info(f"Successfully processed IP: {ip_address}")
                else:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(NO_TIMELINE_DATA_ERROR.format(ip_address))

            except RequestFailure as e:
                # API request failed
                output_message = f"Failed to connect to the GreyNoise server: {str(e)}"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"API request failed for {ip_address}: {str(e)}")
                continue

            except Exception as e:
                # General error
                output_message = COMMON_ACTION_ERROR_MESSAGE.format(IP_TIMELINE_LOOKUP_SCRIPT_NAME, e)
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Error processing {ip_address}: {str(e)}")
                continue

        # Prepare output message
        if successful_entities:
            entities_names = ", ".join([entity.identifier for entity in successful_entities])
            output_message += (
                f"\nSuccessfully processed {len(successful_entities)} IP(s): {entities_names}"
            )
            siemplify.update_entities(successful_entities)
            if failed_entities:
                entities_names = ", ".join([entity.identifier for entity in failed_entities])
                output_message += (
                    f"\nFailed to process {len(failed_entities)} IP(s): {entities_names}"
                )
        else:
            entities_names = ", ".join([entity.identifier for entity in failed_entities])
            output_message += f"\nFailed to process all {len(failed_entities)} IP(s): {entities_names}"
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except InvalidIntegerException as e:
        output_message = f"Invalid parameter value: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except InvalidGranularityException as e:
        output_message = f"Invalid parameter value: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RateLimitError as e:
        output_message = f"Rate limit reached: {str(e)}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(IP_TIMELINE_LOOKUP_SCRIPT_NAME, e)
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
