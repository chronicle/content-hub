from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    convert_dict_to_json_result_dict,
    convert_unixtime_to_datetime,
    output_handler,
    unix_now,
)

from ..core.AbuseIPDB import AbuseIPDBManager

SCRIPT_NAME = "Check IP Reputation"
IDENTIFIER = "AbuseIPDB"
ABUSEIPDB_PREFIX = "AbuseIPDB_"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_key = siemplify.extract_configuration_param(siemplify, param_name="Api Key")
    verify_ssl = siemplify.extract_configuration_param(
        siemplify,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    max_days = siemplify.extract_action_param(
        "Max Age in Days",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    exclude_internal = siemplify.extract_action_param(
        "Exclude Internal Addresses",
        print_value=True,
        input_type=bool,
    )
    create_insight = siemplify.extract_action_param(
        "Create Insight",
        print_value=True,
        input_type=bool,
    )
    sus_threshold = siemplify.extract_action_param(
        "Suspicious Threshold",
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    json_results = {}
    enriched_entities = []
    limit_entities = []
    failed_entities = []
    missing_entities = []

    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "output message:\n "
        result_value = None
        failed_entities = []
        successfull_entities = []

        abuse_ipdb = AbuseIPDBManager(api_key, verify_ssl)
        max_days = abuse_ipdb.validate_max_days(max_days)

        if exclude_internal:
            address_entities = [
                entity
                for entity in siemplify.target_entities
                if entity.entity_type == EntityTypes.ADDRESS and not entity.is_internal
            ]
        else:
            address_entities = [
                entity
                for entity in siemplify.target_entities
                if entity.entity_type == EntityTypes.ADDRESS
            ]

        if not address_entities:
            info_message = "No ADDRESS entities were found in current scope.\n"
            siemplify.LOGGER.info(info_message)
            output_message += info_message

        for entity in address_entities:
            siemplify.LOGGER.info(
                f"Started processing entity: {entity.identifier}",
            )
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    "Timed out. execution deadline ({}) has passed".format(
                        convert_unixtime_to_datetime(
                            siemplify.execution_deadline_unix_time_ms,
                        ),
                    ),
                )
                status = EXECUTION_STATE_TIMEDOUT
                break
            try:
                # Look up address in AbuseIPDB
                address_report = abuse_ipdb.check_ip(entity.identifier, max_days)

                if not address_report:
                    # If report is none, and error not raised - probably entity can't be found.
                    info_message = (
                        f"Entity {entity.identifier} was not found in AbuseIPDB"
                    )
                    siemplify.LOGGER.info(f"\n {info_message}")
                    missing_entities.append(entity.identifier)
                    continue

                json_results[entity.identifier] = address_report.to_json()

                for attrib in dir(address_report):
                    if not attrib.startswith("__") and "_" not in attrib:
                        attrib_val = getattr(
                            address_report,
                            attrib,
                            f"The attribute named {attrib} does not exist",
                        )
                        entity.additional_properties[f"{ABUSEIPDB_PREFIX}{attrib}"] = (
                            str(attrib_val)
                        )

                if int(sus_threshold) > 0 and (
                    int(address_report.abuseConfidenceScore) >= int(sus_threshold)
                ):
                    entity.is_suspicious = True

                if create_insight:
                    severity = 0
                    entity_identifier = entity.identifier
                    insight_type = 1
                    triggered_by = "AbuseIPDB"
                    title = str(entity.identifier)
                    content = f""" 
                        <b>Confidence Score:</b> {address_report.abuseConfidenceScore}
                        <b>Last Reported:</b> No Reports Found.
                        <b>Country Code:</b> {address_report.countryCode}
                        <b>Domain:</b> {address_report.domain}
                        <b>Allowlisted:</b> {address_report.isAllowlisted}
                        <b>ISP:</b> {address_report.isp}
                        <b>Usage Type:</b> {address_report.usageType}
                    """
                    # If reports are found, add the additional fields.
                    if address_report.lastReportedAt is not None:
                        content = f""" 
                            <b>Confidence Score:</b> {address_report.abuseConfidenceScore}
                            <b>Last Reported:</b> {address_report.lastReportedAt}
                            <b>Total Reports:</b> {address_report.totalReports}
                            <b>Country Code:</b> {address_report.countryCode}
                            <b>Domain:</b> {address_report.domain}
                            <b>Allowlisted:</b> {address_report.isAllowlisted}
                            <b>ISP:</b> {address_report.isp}
                            <b>Usage Type:</b> {address_report.usageType}

                        """

                    siemplify.add_entity_insight(entity, content)

                entity.is_enriched = True
                enriched_entities.append(entity)

                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_results),
                )
                info_message = f"Entity {entity.identifier} was submitted and analyzed in AbuseIPDB"
                siemplify.LOGGER.info(f"\n {info_message}")
                output_message += info_message

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}",
                )
                siemplify.LOGGER.exception(e)

        result_value = len(successfull_entities)

        if failed_entities:
            output_message += "\n Failed processing entities:\n   {}".format(
                "\n   ".join(failed_entities),
            )
            status = EXECUTION_STATE_FAILED

        if missing_entities:
            output_message += (
                "\n\nThe following IPs were not found in AbuseIPDB: \n"
                + "{}".format("\n".join(missing_entities))
            )

        if limit_entities:
            output_message += (
                "\n\nThe following IPS were not analyzed due to reaching API request limitation: \n"
                + "{}".format(
                    "\n".join([entity.identifier for entity in limit_entities]),
                )
            )

        if enriched_entities:
            print("Updating entities")
            siemplify.update_entities(enriched_entities)

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        raise

        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
