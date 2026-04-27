from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    get_domain_from_entity,
    flat_dict_to_csv,
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
)
from TIPCommon import extract_configuration_param
from ..core.VirusTotal import (
    VirusTotalManager,
    VirusTotalInvalidAPIKeyManagerError,
    VirusTotalLimitManagerError,
)

# Consts
DOMAIN_RESULT_URL_FORMAT = "https://www.virustotal.com/#/domain/{0}"
VT_PREFIX = "VT"
SCRIPT_NAME = "VirusTotal - GetDomainReport"
IDENTIFIER = "VirusTotal"
SCAN_REPORT = "Score Report"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = extract_configuration_param(
        siemplify, provider_name=IDENTIFIER, param_name="Api Key", input_type=str
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=IDENTIFIER,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    enriched_entities = []
    limit_entities = []
    failed_entities = []
    missing_entities = []
    result_value = "true"
    json_results = {}
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        vt = VirusTotalManager(api_key, verify_ssl)
        supported_entities = [
            entity
            for entity in siemplify.target_entities
            if entity.entity_type == EntityTypes.HOSTNAME
            or entity.entity_type == EntityTypes.USER
            or entity.entity_type == EntityTypes.URL
        ]
        if not supported_entities:
            info_message = "No HOSTNAME or USER entities were found in current scope.\n"
            siemplify.LOGGER.info(info_message)
            output_message += info_message

        for entity in supported_entities:
            # Search a domains in virus total.
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                domain_report = vt.get_domain_report(
                    get_domain_from_entity(entity).lower()
                )
                if not domain_report:
                    # If report is none, and error not raised - probably entity can't be found.
                    info_message = (
                        f"Entity {entity.identifier} was not found in VirusTotal"
                    )
                    siemplify.LOGGER.info(f"\n {info_message}")
                    missing_entities.append(entity.identifier)
                    continue

                json_results[entity.identifier] = domain_report.to_json()
                enrichment_object = domain_report.to_enrichment_data()
                # Scan flat data - update enrichment
                entity.additional_properties.update(
                    add_prefix_to_dict(enrichment_object, VT_PREFIX)
                )
                enriched_entities.append(entity)
                entity.is_enriched = True

                # Scan detections_information
                siemplify.result.add_entity_table(
                    f"{entity.identifier} {SCAN_REPORT}",
                    flat_dict_to_csv(enrichment_object),
                )

                web_link = DOMAIN_RESULT_URL_FORMAT.format(
                    get_domain_from_entity(entity)
                )
                siemplify.result.add_entity_link(
                    f"{entity.identifier} Link to web report", web_link
                )

                info_message = (
                    "The following entity was submitted and analyzed in VirusTotal: "
                    + f"{entity.identifier}"
                    + "\n \n *Check online report for full details.\n"
                )
                siemplify.LOGGER.info(f"\n{info_message}")

            except VirusTotalInvalidAPIKeyManagerError as e:
                # Invalid key was passed - terminate action
                siemplify.LOGGER.error(
                    "Invalid API key was provided. Access is forbidden."
                )
                status = EXECUTION_STATE_FAILED
                result_value = "false"
                output_message = "Invalid API key was provided. Access is forbidden."
                break

            except VirusTotalLimitManagerError as e:
                siemplify.LOGGER.error("API limit reached.")
                siemplify.LOGGER.exception(e)
                limit_entities.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{e}."
                )
                siemplify.LOGGER.exception(e)
                failed_entities.append(entity)

        if missing_entities:
            output_message += (
                "The following entities were not found in VirusTotal: \n"
                + "{}".format("\n".join(missing_entities))
            )

        if failed_entities:
            output_message += (
                "\n\nThe following entities were failed in VirusTotal: \n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

        if limit_entities:
            output_message += (
                "\n\nThe following entities were not enriched due to reaching API request limitation: \n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in limit_entities])
                )
            )

        if enriched_entities:
            siemplify.update_entities(enriched_entities)
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )
            output_message += (
                "\n\nThe following entities were submitted and analyzed in VirusTotal: \n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in enriched_entities])
                )
                + "\n \n *Check online report for full details.\n"
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    # add json
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
