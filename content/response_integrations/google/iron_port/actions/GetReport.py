from __future__ import annotations
import datetime

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from ..core.IronportManagerAPI import IronportManagerAPI
from ..core.IronportConstants import INTEGRATION_NAME, SCRIPT_GET_REPORT, ENTITY_TYPES_MAPPING
from ..core.IronportExceptions import IronportAsyncOSReportException, IronportManagerException


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_GET_REPORT
    output_messages = []
    success_entities = []
    failed_entities = []

    siemplify.LOGGER.info("-" * 20 + " Main - Param Init " + "-" * 20)

    server_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Server Address",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )

    port = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="AsyncOS API Port",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
        input_type=str,
        is_mandatory=True,
    )

    ca_certificate = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="CA Certificate File - parsed into Base64 String",
    )

    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    report_type = extract_action_param(
        siemplify,
        param_name="Report Type",
        print_value=True,
        input_type=str,
        is_mandatory=True,
    )

    days_backwards = extract_action_param(
        siemplify,
        param_name="Search Reports Data for Last X Days",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    limit = extract_action_param(
        siemplify,
        param_name="Max Records to Return",
        print_value=True,
        input_type=int,
        is_mandatory=True,
    )

    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_backwards)

    siemplify.LOGGER.info("-" * 20 + " Main - Started " + "-" * 20)

    try:
        ironport_manager = IronportManagerAPI(
            server_address=server_address,
            port=port,
            username=username,
            password=password,
            ca_certificate=ca_certificate,
            use_ssl=use_ssl,
            verify_ssl=verify_ssl,
        )

        entity_types = [
            entity_type
            for entity_type, mapping in ENTITY_TYPES_MAPPING.items()
            if report_type in mapping.get("report_types", [])
        ]
        siemplify.LOGGER.info(f"Action should run on entities: {entity_types}")
        entities = list(
            filter(lambda en: en.entity_type in entity_types, siemplify.target_entities)
        )

        reports = ironport_manager.get_reports(
            report_type=report_type, start_date=start_date, limit=limit
        )

        siemplify.LOGGER.info(
            f'{len(reports)} report{"s" if len(reports) != 1 else ""} {"were" if len(reports) != 1 else "was"} found'
        )

        if not entities:
            if reports:
                siemplify.result.add_data_table(
                    title=f"IronPort {report_type} report",
                    data_table=construct_csv([report.to_json() for report in reports]),
                )

            output_messages.append(
                f"Successfully executed action for IronPort {report_type} report"
            )
            is_success = True
            status = EXECUTION_STATE_COMPLETED
        else:
            for entity in entities:
                siemplify.LOGGER.info(f"Processing entity {entity.identifier}")
                fld = ENTITY_TYPES_MAPPING.get(entity.entity_type, {}).get("field", "")
                entity_identifier_lower = entity.identifier.lower()
                filtered_reports = list(
                    filter(
                        lambda r, etf = fld,
                        eil=entity_identifier_lower:getattr(r, etf, "").lower() == eil,
                        reports
                    )
                )

                if not filtered_reports:
                    failed_entities.append(entity)
                    continue

                success_entities.append(entity)
                siemplify.result.add_entity_table(
                    entity_identifier=entity.identifier,
                    data_table=construct_csv(
                        [report.to_json() for report in filtered_reports]
                    ),
                )
                entity.additional_properties.update(reports[0].to_json())
                entity.is_enriched = True

            if success_entities:
                f_ide = ", ".join([entity.identifier for entity in failed_entities])
                output_messages.append(
                    f"Action was not able to find IronPort {report_type} report data "
                    f"for the following entities: {f_ide}"
                )

                if failed_entities:
                    ide = ", ".join([entity.identifier for entity in failed_entities])
                    output_messages.append(
                        f"Action was not able to find IronPort "
                        f"{report_type} report data "
                        f"for the following entities: {ide}"
                    )
            else:
                output_messages.append("No information was found.")

            is_success = True
            status = EXECUTION_STATE_COMPLETED

    except IronportAsyncOSReportException as e:
        message = (
            f"Failed to execute action for IronPort {report_type} report. Error is {e}"
        )
        siemplify.LOGGER.error(message)
        siemplify.LOGGER.exception(e)
        output_messages.append(message)
        is_success = False
        status = EXECUTION_STATE_COMPLETED

    except (IronportManagerException, Exception) as e:
        message = f"Failed to execute action! Error is {e}"
        siemplify.LOGGER.error(message)
        siemplify.LOGGER.exception(e)
        output_messages.append(message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    output_message = "\n".join(output_messages)
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
