from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    output_handler,
    add_prefix_to_dict_keys,
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
)
from TIPCommon import (
    extract_configuration_param,
    dict_to_flat,
    flat_dict_to_csv,
)
from ..core.AlienVaultTIManager import AlienVaultTIManager

# Consts
INTEGRATION_NAME = "AlienVaultTI"
SCRIPT_NAME = "Enriches Entities"
ADDRESS = EntityTypes.ADDRESS
FILEHASH = EntityTypes.FILEHASH
URL = EntityTypes.URL
HOSTNAME = EntityTypes.HOSTNAME


# Enrich target entity with alienvault info and add csv table to entity
def enrich_entity(report, entity, siemplify):
    country = report.get("geo").get("country_code") if report.get("geo") else None
    flat_report = dict_to_flat(report)
    csv_output = flat_dict_to_csv(flat_report)
    flat_report = add_prefix_to_dict_keys(flat_report, "AlienVault")
    siemplify.result.add_entity_table(entity.identifier, csv_output)
    entity.additional_properties.update(flat_report)
    entity.additional_properties["Country"] = country
    entity.is_enriched = True
    return True


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
        input_type=str,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    entities_to_enrich = []
    failed_entities = []
    not_found_entities = []
    json_result = {}

    try:
        alienvault = AlienVaultTIManager(api_key, siemplify.LOGGER)

        for entity in siemplify.target_entities:
            try:
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        "Timed out. execution deadline "
                        f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                        "has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                if entity.entity_type == ADDRESS and not entity.is_internal:
                    ip_info = alienvault.enrich_ip(entity.identifier)
                    if ip_info:
                        siemplify.LOGGER.info(f"Results found for {entity.identifier}")
                        json_result[entity.identifier] = ip_info
                        enrich_entity(ip_info, entity, siemplify)
                        entities_to_enrich.append(entity)
                    else:
                        siemplify.LOGGER.info(
                            f"No results found for {entity.identifier}"
                        )
                        not_found_entities.append(entity)

                elif entity.entity_type == FILEHASH:
                    hash_info = alienvault.enrich_hash(entity.identifier)
                    if hash_info:
                        siemplify.LOGGER.info(f"Results found for {entity.identifier}")
                        json_result[entity.identifier] = hash_info
                        enrich_entity(hash_info, entity, siemplify)
                        entities_to_enrich.append(entity)
                    else:
                        siemplify.LOGGER.info(
                            f"No results found for {entity.identifier}"
                        )
                        not_found_entities.append(entity)

                elif entity.entity_type == URL:
                    url_info = alienvault.enrich_url(entity.identifier)
                    if url_info:
                        siemplify.LOGGER.info(f"Results found for {entity.identifier}")
                        json_result[entity.identifier] = url_info
                        enrich_entity(url_info, entity, siemplify)
                        entities_to_enrich.append(entity)
                    else:
                        siemplify.LOGGER.info(
                            f"No results found for {entity.identifier}"
                        )
                        not_found_entities.append(entity)

                elif entity.entity_type == HOSTNAME and not entity.is_internal:
                    host_info = alienvault.enrich_host(entity.identifier)
                    if host_info:
                        siemplify.LOGGER.info(f"Results found for {entity.identifier}")
                        json_result[entity.identifier] = host_info
                        enrich_entity(host_info, entity, siemplify)
                        entities_to_enrich.append(entity)
                    else:
                        siemplify.LOGGER.info(
                            f"No results found for {entity.identifier}"
                        )
                        not_found_entities.append(entity)

                else:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is either internal "
                        "or of not supported type."
                    )

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity)
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{e}."
                )
                siemplify.LOGGER.exception(e)

        if entities_to_enrich:
            output_message = (
                "Following entities were enriched by AlienVault.\n   {}".format(
                    "\n   ".join([entity.identifier for entity in entities_to_enrich])
                )
            )

            siemplify.update_entities(entities_to_enrich)
            result_value = True

        else:
            output_message = "No entities were enriched."
            result_value = False

        if not_found_entities:
            output_message += (
                "\n\nCould not find results for the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in not_found_entities])
                )
            )

        if failed_entities:
            output_message += (
                "\n\nAn error occurred on the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error occurred while running action {SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"An error occurred while running action. Error: {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
