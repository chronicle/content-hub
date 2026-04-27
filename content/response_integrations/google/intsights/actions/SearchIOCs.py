from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.IntsightsManager import IntsightsManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED

from ..core.consts import SEARCH_IOCS_ACTION, INTEGRATION_NAME, SEVERITY_VALUES
from TIPCommon import extract_configuration_param
from ..core.utils import get_entity_original_identifier


def get_flat_values(data):
    temp_data = {}
    for key, value in data.items():
        if not isinstance(value, dict) and not isinstance(value, list):
            temp_data[key] = value

    return temp_data


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SEARCH_IOCS_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    account_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Account ID",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        print_value=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = True
    enriched_entities, json_results = [], {}

    try:
        intsights_manager = IntsightsManager(
            server_address=api_root,
            account_id=account_id,
            api_key=api_key,
            api_login=False,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in siemplify.target_entities:
            entity_identifier = get_entity_original_identifier(entity)
            try:
                iocs_data = intsights_manager.search_iocs(entity_identifier)

                if iocs_data:
                    siemplify.result.add_entity_json(
                        entity_identifier, iocs_data.to_json()
                    )
                    json_results[entity_identifier] = iocs_data.to_json()
                    enrichment_data = iocs_data.to_enrichment_data(INTEGRATION_NAME)
                    entity.additional_properties.update(enrichment_data)
                    entity.is_enriched = True

                    if iocs_data.severity in SEVERITY_VALUES:
                        entity.is_suspicious = True
                        siemplify.add_entity_insight(
                            entity,
                            f"{entity_identifier} was found suspicious",
                            triggered_by=INTEGRATION_NAME,
                        )

                    enriched_entities.append(entity)
            except Exception as e:
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity_identifier}.\n {e}."
                )
                siemplify.LOGGER.exception(e)

        if enriched_entities:
            entities_names = [
                get_entity_original_identifier(entity) for entity in enriched_entities
            ]
            output_message = f"IOCs were found for the following entities:\n {', '.join(entities_names)}"

            siemplify.update_entities(enriched_entities)

        else:
            output_message = "No IOCs were found."
            result_value = False

    except Exception as e:
        output_message = f"Error executing action {SEARCH_IOCS_ACTION}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
