from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core import datamodels
from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_IOC_DETAILS_BY_ENRICHING_ENTITIES_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    NO_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.cyware_exceptions import (
    CywareException,
    InvalidFormatException,
    InvalidIntegerException,
)
from ..core.utils import get_entities, get_entities_object, get_integration_params


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_IOC_DETAILS_BY_ENRICHING_ENTITIES_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: dict = {}

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        enrichment_data_str = siemplify.extract_action_param(
            "Enrichment Data", print_value=True, default_value="False"
        )
        relation_data_str = siemplify.extract_action_param(
            "Relation Data", print_value=True, default_value="False"
        )
        fields_str = siemplify.extract_action_param("Fields", print_value=True)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        ioc_values = get_entities(siemplify)
        fields = None
        if fields_str and fields_str.strip():
            normalized_fields = [part.strip() for part in fields_str.split(",") if part.strip()]
            if normalized_fields:
                fields = ",".join(normalized_fields)

        if not ioc_values:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        enrichment_data = enrichment_data_str.lower() == "true"
        relation_data = relation_data_str.lower() == "true"

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )

        response = cyware_manager.get_ioc_details(
            ioc_values=ioc_values,
            enrichment_data=enrichment_data,
            relation_data=relation_data,
            fields=fields,
        )

        results = response.get("results", [])

        if results:
            json_results = response
            ioc_details = [datamodels.IOCDetails(ioc) for ioc in results]
            csv_output = [ioc_detail.to_csv() for ioc_detail in ioc_details]

            # Limit table rows for display
            if len(csv_output) > MAX_TABLE_RECORDS:
                csv_output = csv_output[:MAX_TABLE_RECORDS]
                output_message = (
                    f"Successfully retrieved details for {len(results)} IOCs. "
                    f"Showing first {MAX_TABLE_RECORDS} records in table."
                )
            else:
                output_message = f"Successfully retrieved details for {len(results)} IOCs."

            siemplify.result.add_data_table("IOC Details", construct_csv(csv_output), "CTIX")
            siemplify.LOGGER.info(f"Retrieved {len(results)} IOC details")
            result_value = RESULT_VALUE_TRUE

            # Get all entities and create IOC values set for filtering
            entities_object = get_entities_object(siemplify)
            siemplify.LOGGER.info(f"Found {len(entities_object)} entities")

            # Create set of IOC values from results for efficient lookup
            ioc_values_set = {ioc.get("name", "").lower() for ioc in results if ioc.get("name")}

            # Filter entities to keep only those present in results
            filtered_entities = [
                entity for entity in entities_object if entity.identifier.lower() in ioc_values_set
            ]
            siemplify.LOGGER.info(
                f"Filtered to {len(filtered_entities)} entities present in results"
            )

            # Create entity map and successful entities list
            entity_map = {entity.identifier.lower(): entity for entity in filtered_entities}
            successful_entities = []

            # Enrich entities using IOCDetails datamodel
            for ioc_detail in ioc_details:
                ioc_value = (
                    ioc_detail.name
                    if ioc_detail.name and ioc_detail.name != "N/A"
                    else ioc_detail.raw_data.get("value", "")
                )
                if ioc_value:
                    entity = entity_map.get(ioc_value.lower())
                    if entity:
                        # Use datamodel for enrichment
                        entity.additional_properties.update(ioc_detail.enrich_data())
                        entity.is_enriched = True
                        successful_entities.append(entity)
                        siemplify.LOGGER.info(f"Successfully enriched entity: {entity.identifier}")

            # Update entities in Siemplify
            if successful_entities:
                siemplify.update_entities(successful_entities)
                siemplify.LOGGER.info(f"Updated {len(successful_entities)} entities")

        else:
            output_message = "No IOC details found."
            result_value = RESULT_VALUE_TRUE

    except InvalidIntegerException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except InvalidFormatException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            GET_IOC_DETAILS_BY_ENRICHING_ENTITIES_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
