from __future__ import annotations
from collections import defaultdict
from urllib.parse import urlparse

from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes, InsightType, InsightSeverity
from soar_sdk.SiemplifyUtils import output_handler
from ..core.TruSTARManager import TruSTARManager
from ..core.consts import (
    INTEGRATION_NAME,
    GET_RELATED_REPORTS,
    DEFAULT_MAX_REPORTS,
    MAX_REPORTS,
    MIN_REPORTS,
    LIST_ENCLAVES,
    INSIGHT_HTML_TEMPLATE,
    RELATED_REPORTS_CSV_TABLE_TITLE,
    NOT_ASSIGNED,
    REPORT_BODY_INSIGHT,
)
from ..core.datamodels import ReportDetails
from ..core.exceptions import TruSTARMissingEnclaveException
from ..core.utils import load_csv_to_list


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {GET_RELATED_REPORTS}"
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

    enclave_filter = extract_action_param(
        siemplify, param_name="Enclave Filter", is_mandatory=False, print_value=True
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=True,
    )
    include_report_body_in_insight = extract_action_param(
        siemplify,
        param_name="Include Report Body In Insight",
        input_type=bool,
        is_mandatory=False,
        print_value=True,
        default_value=False,
    )
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = False
    status = EXECUTION_STATE_COMPLETED
    supported_entities = []

    failed_enclaves = []
    found_enclaves_ids = []
    json_results = []

    insights = []
    csv_tables = defaultdict(list)

    try:
        max_reports_to_return = extract_action_param(
            siemplify,
            param_name="Max Reports To Return",
            input_type=int,
            is_mandatory=False,
            print_value=True,
            default_value=DEFAULT_MAX_REPORTS,
        )

        if (max_reports_to_return > MAX_REPORTS) or (
            max_reports_to_return < MIN_REPORTS
        ):
            siemplify.LOGGER.info(
                f'"Max Reports To Return" parameter not in range of {MIN_REPORTS} to {MAX_REPORTS}. Using value of: {MAX_REPORTS}'
            )
            max_reports_to_return = MAX_REPORTS

        enclave_filter_list = (
            load_csv_to_list(enclave_filter, "Enclave Filter") if enclave_filter else []
        )
        manager = TruSTARManager(
            api_root=api_root,
            api_key=api_key,
            api_secret=api_secret,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.URL:
                domain = (
                    urlparse(entity.identifier).netloc
                    or urlparse(entity.identifier).path
                )
                supported_entities.append(domain)
                continue
            supported_entities.append(entity.identifier)

        if supported_entities:
            enclaves = manager.list_enclaves()
            siemplify.LOGGER.info(f"Listed {len(enclaves)} available enclaves")
            enclaves_names_to_ids = {enclave.name: enclave.id for enclave in enclaves}

            for enclave in enclave_filter_list:
                if enclave not in enclaves_names_to_ids:
                    failed_enclaves.append(enclave)
                else:
                    found_enclaves_ids.append(enclaves_names_to_ids.get(enclave, ""))

            if failed_enclaves:
                raise TruSTARMissingEnclaveException(
                    'Error execution action "{}". Reason: the following enclaves were not found:\n  {}\n\nPlease check the spelling or '
                    'use the action "{}" to find the valid enclaves.'
                    "".format(
                        GET_RELATED_REPORTS, "\n  ".join(failed_enclaves), LIST_ENCLAVES
                    )
                )
            if found_enclaves_ids:
                siemplify.LOGGER.info(
                    f"Searching related reports for enclave ids of: {', '.join(found_enclaves_ids)}"
                )
            else:
                siemplify.LOGGER.info(
                    "Searching related reports for all available enclaves"
                )
            reports = manager.get_correlated_reports(
                indicators=[entity.identifier for entity in siemplify.target_entities],
                enclave_ids=found_enclaves_ids,
                limit=max_reports_to_return,
            )[:max_reports_to_return]
            siemplify.LOGGER.info(f"Found {len(reports)} related reports")
            for report in reports:
                siemplify.LOGGER.info(f"Processing report with id: {report.id}")
                try:
                    siemplify.LOGGER.info(f"Fetching report details")
                    report_details = manager.get_report_details(report_id=report.id)
                    report_json_result = report_details.as_json()
                    try:
                        siemplify.LOGGER.info(f"Fetching report tags")
                        report_tags = manager.get_report_tags(report_id=report.id)
                        report_json_result["tags"] = [
                            report_tag.as_json() for report_tag in report_tags
                        ]
                        csv_tables[RELATED_REPORTS_CSV_TABLE_TITLE].extend(
                            [
                                {
                                    "Title": report_details.title,
                                    "Tags": ", ".join(
                                        [tag.name for tag in report_tags]
                                    ),
                                }
                            ]
                        )
                    except Exception as error:
                        siemplify.LOGGER.error(
                            f"Failed to get report tags. Error is: {error}"
                        )
                        report_tags = []
                    json_results.append(report_json_result)
                    if create_insight and isinstance(report_details, ReportDetails):
                        insights.append(
                            INSIGHT_HTML_TEMPLATE.format(
                                title=report_details.title,
                                created=report_details.created_date_formatted,
                                updated=report_details.updated_date_formatted,
                                submission_status=report_details.submission_status,
                                tags=(
                                    ", ".join([report.name for report in report_tags])
                                    if report_tags
                                    else NOT_ASSIGNED
                                ),
                                link=report_details.html_report_link,
                                report_body=(
                                    REPORT_BODY_INSIGHT.format(
                                        report_body=report_details.report_body_as_insight
                                    )
                                    if include_report_body_in_insight
                                    else ""
                                ),
                            )
                        )
                except Exception as error:
                    siemplify.LOGGER.error(
                        f"Failed to get report details. Error is: {error}"
                    )
                siemplify.LOGGER.info(f"Finished processing report")
        else:
            siemplify.LOGGER.info(f"No siemplify entities were provided for enrichment")
            reports = []

        if reports:
            siemplify.result.add_result_json(json_results)
            for table_title, rows in csv_tables.items():
                siemplify.result.add_data_table(
                    title=table_title, data_table=construct_csv(rows)
                )
            if create_insight and insights:
                siemplify.create_case_insight(
                    triggered_by=INTEGRATION_NAME,
                    title="Related Reports" if len(reports) > 1 else "Related Report",
                    content="".join(insights),
                    entity_identifier="",
                    severity=InsightSeverity.INFO,
                    insight_type=InsightType.General,
                )
            result_value = True
            output_message = f"Successfully returned related reports for the provided entities in {INTEGRATION_NAME}"
        else:
            output_message = f"No related reports were found for the provided entities in {INTEGRATION_NAME}"

    except Exception as error:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error execution action "{GET_RELATED_REPORTS}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
