from __future__ import annotations
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    DEFAULT_TRESHOLD,
    ENRICH_URL_ACTION,
    INTEGRATION_NAME,
    MIN_THRESHOLD,
    MAX_THRESHOLD,
)
from ..core.CofenseTriageManager import CofenseTriageManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ENRICH_URL_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=True,
        is_mandatory=True,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        is_mandatory=True,
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

    threshold = extract_action_param(
        siemplify,
        param_name="Risk Score Threshold",
        default_value=DEFAULT_TRESHOLD,
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )

    if threshold < MIN_THRESHOLD or threshold > MAX_THRESHOLD:
        siemplify.LOGGER.info(
            f"Threshold must be greater than {MIN_THRESHOLD} and lower than "
            f"{MAX_THRESHOLD}. We will use default value of: {DEFAULT_TRESHOLD} instead"
        )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    result_value = True
    json_results = {}
    entities_to_update = []
    failed_entities = []
    output_message = ""

    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]

    try:
        cofensetriage_manager = CofenseTriageManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
        )
        for entity in scope_entities:
            siemplify.LOGGER.info(f"Started processing entity:{entity.identifier}")
            try:
                url_object = cofensetriage_manager.enrich_url(entity.identifier)

                if not url_object.to_json():
                    siemplify.LOGGER.info(
                        f"No URL details were found for entity: {entity.identifier}"
                    )
                    failed_entities.append(entity)
                    continue

                if url_object.risk_score and int(url_object.risk_score) > threshold:
                    entity.is_suspicious = True

                json_results[entity.identifier] = url_object.to_json()
                entity.is_enriched = True
                entity.additional_properties.update(url_object.as_enrichment_data())
                entities_to_update.append(entity)

                siemplify.result.add_entity_table(
                    f"{entity.identifier}", construct_csv(url_object.to_table())
                )

            except Exception as e:
                output_message += f"Unable to enrich entity: {entity.identifier} \n"
                failed_entities.append(entity)
                siemplify.LOGGER.error(f"Failed processing entity:{entity.identifier}")
                siemplify.LOGGER.exception(e)

            siemplify.LOGGER.info(f"Finished processing entity:{entity.identifier}")

    except Exception as e:
        output_message += f"Error executing action {ENRICH_URL_ACTION}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    if len(scope_entities) == len(failed_entities):
        output_message += "No URLs were enriched."
        result_value = False

    else:
        if entities_to_update:
            siemplify.update_entities(entities_to_update)
            output_message += (
                "Successfully enriched the following URLs using {}:\n{}".format(
                    INTEGRATION_NAME,
                    "\n".join([entity.identifier for entity in entities_to_update]),
                )
            )

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
        if failed_entities:
            output_message += ("\nAction wasn't able to enrich the "
                               "following URLs using {}:\n{}").format(
                INTEGRATION_NAME,
                "\n".join([entity.identifier for entity in failed_entities]),
            )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  "
        f"result_value: {result_value}\n  "
        f"output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
