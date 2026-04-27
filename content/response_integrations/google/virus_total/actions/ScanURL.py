from __future__ import annotations
import json
import sys

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
    output_handler,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.VirusTotal import (
    VirusTotalManager,
    URL_TYPE,
    ScanStatus,
    ENTITY_TASK_ID_KEY,
    ENTITY_REPORT_KEY,
    ENTITY_STATUS_KEY,
    VirusTotalInvalidAPIKeyManagerError,
    VirusTotalLimitManagerError,
)

VT_PREFIX = "VT"
SCRIPT_NAME = "VirusTotal - ScanURL"
IDENTIFIER = "VirusTotal"

NO_PERMALINK = "No permalink found in results."


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"
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

    #  INIT ACTION PARAMETERS:
    rescan_after_days = extract_action_param(
        siemplify,
        param_name="Rescan after days",
        is_mandatory=False,
        input_type=int,
        default_value=None,
    )

    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=3,
    )

    output_message = ""
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")

    try:
        manager = VirusTotalManager(api_key, verify_ssl)

        if is_first_run:
            try:
                entities_handle = start_operation(siemplify, manager, rescan_after_days)

                if entities_handle:
                    status = EXECUTION_STATE_INPROGRESS
                    result_value = json.dumps(entities_handle)
                    output_message += "The following entities were submitted for analysis in VirusTotal:\n{}".format(
                        "\n".join(list(entities_handle.keys()))
                    )
                else:
                    result_value = "false"
                    output_message += "No URL entities were found in current scope."

            except VirusTotalInvalidAPIKeyManagerError as e:
                # Invalid key was passed - terminate action
                siemplify.LOGGER.error(
                    "Invalid API key was provided. Access is forbidden."
                )
                status = EXECUTION_STATE_FAILED
                result_value = "false"
                output_message = "Invalid API key was provided. Access is forbidden."

        else:
            entities_handle = json.loads(siemplify.parameters["additional_data"])
            query_output_message, result_value, status = query_operation_status(
                siemplify, manager, threshold, entities_handle
            )
            output_message += query_output_message

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message += f"\nGeneral error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


def start_operation(siemplify, manager, rescan_after_days):
    """
    Main ScanURL action
    :param siemplify: SiemplifyAction object
    :param manager: VirusTotal object
    :param rescan_after_days: action init param
    :return: {entities}
    """
    url_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == EntityTypes.URL
    ]
    entities_handle = {}

    for entity in url_entities:
        try:
            # Search a file url in virusTotal
            entities_handle.update(
                manager.define_resource_status(
                    get_entity_original_identifier(entity), URL_TYPE, rescan_after_days
                )
            )

        except VirusTotalInvalidAPIKeyManagerError:
            # Invalid API key provided - raise
            raise

        except VirusTotalLimitManagerError:
            siemplify.LOGGER.info(f"API limit reached for entity {entity.identifier}")
            entity_handle = {
                entity.identifier: {
                    ENTITY_REPORT_KEY: {},
                    ENTITY_TASK_ID_KEY: None,
                    ENTITY_STATUS_KEY: ScanStatus.LIMIT_REACHED,
                }
            }
            entities_handle.update(entity_handle)

        except Exception as e:
            siemplify.LOGGER.error(
                f"An error occurred on entity {get_entity_original_identifier(entity)}"
            )
            siemplify.LOGGER.exception(e)
            entity_handle = {
                get_entity_original_identifier(entity): {
                    ENTITY_REPORT_KEY: {},
                    ENTITY_TASK_ID_KEY: None,
                    ENTITY_STATUS_KEY: ScanStatus.FAILED,
                }
            }
            entities_handle.update(entity_handle)
    if not url_entities:
        siemplify.LOGGER.info("No URL entities were found in current scope.\n")
    return entities_handle


def query_operation_status(siemplify, manager, threshold, entities_handle):
    """
    Main ScanHash action
    :param siemplify: SiemplifyAction object
    :param manager: VirusTotal object
    :param threshold: action init param
    :param entities_handle: entities which should be checked
    :return: {output message, result, execution state}
    """

    output_message = ""
    missing_urls = []
    report_urls = []
    rescan_urls = []
    forbidden_urls = []
    json_results = {}
    failed_urls = []
    limit_urls = []
    entities_to_enrich = []
    is_risky = False

    for entity_identifier, entity_handle in list(entities_handle.items()):
        task_id = entity_handle.get(ENTITY_TASK_ID_KEY)
        try:
            if task_id and entity_handle.get(ENTITY_STATUS_KEY) == ScanStatus.QUEUED:
                siemplify.LOGGER.info(
                    f"Checking if task of {entity_identifier} has completed."
                )
                # check if analysis completed
                entity_report = manager.is_scan_report_ready(task_id, URL_TYPE)
                if entity_report:
                    siemplify.LOGGER.info(f"Task of {entity_identifier} has completed.")
                    # is_ready = True, fetch the report
                    entity_handle[ENTITY_STATUS_KEY] = ScanStatus.DONE
                    entity_handle[ENTITY_REPORT_KEY] = entity_report.to_json()
                else:
                    siemplify.LOGGER.info(
                        f"Task of {entity_identifier} has NOT completed yet."
                    )

        except VirusTotalLimitManagerError:
            siemplify.LOGGER.info(
                f"API limit reached while checking if task of {entity_identifier} has completed."
            )
            entity_handle[ENTITY_STATUS_KEY] = ScanStatus.LIMIT_REACHED

        except Exception as err:
            error_message = (
                f"Error Rescan {entity_identifier} with task ID {task_id}, Error: {err}"
            )
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            entity_handle[ENTITY_STATUS_KEY] = ScanStatus.FAILED

    # Flag to determine the async action status - continue, end
    queued_items = dict(
        [
            entity
            for entity in list(entities_handle.items())
            if entity[1][ENTITY_STATUS_KEY] == ScanStatus.QUEUED
        ]
    )

    if queued_items:
        siemplify.LOGGER.info(
            "Continuing...the requested items are still queued for analysis"
        )
        output_message = (
            "Continuing...the requested items are still queued for analysis"
        )
        siemplify.end(
            output_message, json.dumps(entities_handle), EXECUTION_STATE_INPROGRESS
        )

    # Action END
    else:
        siemplify.LOGGER.info("All tasks are done")
        for entity_identifier, entity_handle in list(entities_handle.items()):
            if entity_handle.get(
                ENTITY_STATUS_KEY
            ) == ScanStatus.DONE and entity_handle.get(ENTITY_REPORT_KEY):
                siemplify.LOGGER.info(f"Collecting results for {entity_identifier}.")

                if entity_handle.get(ENTITY_TASK_ID_KEY):
                    # Entity's last scan exceed the rescan days threshold - was rescan it.
                    siemplify.LOGGER.info(f"Entity {entity_identifier} was rescanned")
                    rescan_urls.append(entity_identifier)
                else:
                    report_urls.append(entity_identifier)

                # Report enrichment & data table
                json_results[entity_identifier] = entity_handle.get(ENTITY_REPORT_KEY)
                try:
                    entity = [
                        e
                        for e in siemplify.target_entities
                        if get_entity_original_identifier(e) == entity_identifier
                    ][0]

                    try:
                        comments = manager.get_comments(entity.identifier)
                    except Exception as e:
                        siemplify.LOGGER.info(
                            f"Unable to fetch comments for {entity.identifier}"
                        )
                        siemplify.LOGGER.exception(e)
                        comments = []

                    # Fetch report
                    is_risky_entity = add_siemplify_results(
                        siemplify,
                        entity,
                        manager.get_url_report(entity_handle.get(ENTITY_REPORT_KEY)),
                        threshold,
                        comments,
                    )

                    if is_risky_entity:
                        is_risky = True

                    entities_to_enrich.append(entity)
                except Exception as err:
                    error_message = f"Error on url {entity_identifier}: {err}."
                    siemplify.LOGGER.error(error_message)
                    siemplify.LOGGER.exception(err)

            elif entity_handle.get(ENTITY_STATUS_KEY) == ScanStatus.FAILED:
                failed_urls.append(entity_identifier)

            elif entity_handle.get(ENTITY_STATUS_KEY) == ScanStatus.FORBIDDEN:
                forbidden_urls.append(entity_identifier)

            elif entity_handle.get(ENTITY_STATUS_KEY) == ScanStatus.LIMIT_REACHED:
                limit_urls.append(entity_identifier)

            else:
                missing_urls.append(entity_identifier)

        if report_urls or rescan_urls:
            # Fetch report handle
            report_urls.extend(rescan_urls)
            output_message += (
                "Reports were fetched for the following urls: \n{}\n".format(
                    "\n".join(report_urls)
                )
            )

        if missing_urls:
            # Missing url handle
            output_message += (
                "\nThe following urls does not exist on VirusTotal (url was never scanned "
                "before): \n{}\n".format("\n".join(missing_urls))
            )

        if failed_urls:
            output_message += "\nThe following urls have failed: \n{}\n".format(
                "\n".join(failed_urls)
            )

        if forbidden_urls:
            output_message += (
                "\nFailed to rescan the following urls (provided API Key is for public API, "
                "but private API access is required): \n{}\n".format(
                    "\n".join(forbidden_urls)
                )
            )

        if limit_urls:
            output_message += "\nReports were not fetched for the following urls due to reaching API request limitation: \n{}\n".format(
                "\n".join(limit_urls)
            )

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

        if entities_to_enrich:
            siemplify.update_entities(entities_to_enrich)

        return output_message, is_risky, EXECUTION_STATE_COMPLETED


def add_siemplify_results(siemplify, entity, report, threshold, comments=[]):
    """
    helper function for query_operation_status
    add report to entity
    :param siemplify: SiemplifyAction object
    :param entity: entity which will be added to result
    :param report: URL object created from url call response
    :param threshold: threshold param from siemplify object
    :param comments: List of the hash's comments
    :return: {bool}
    """
    is_risky = False
    entity.additional_properties.update(
        add_prefix_to_dict(report.to_enrichment_data(), VT_PREFIX)
    )
    entity.is_enriched = True

    siemplify.result.add_entity_table(
        get_entity_original_identifier(entity), construct_csv(report.build_engine_csv())
    )

    if comments:
        comments_table = construct_csv([comment.to_csv() for comment in comments])
        siemplify.result.add_data_table(
            f"Comments to {entity.identifier}", comments_table
        )

    web_link = report.permalink if report.permalink else NO_PERMALINK
    siemplify.result.add_entity_link(get_entity_original_identifier(entity), web_link)

    positives = report.positives if report.positives else 0
    if int(threshold) <= positives:
        is_risky = True
        entity.is_suspicious = True

        insight_msg = f"VirusTotal - URL was marked as malicious by {report.positives} of {report.total} engines. Threshold set to - {threshold}"

        siemplify.add_entity_insight(entity, insight_msg, triggered_by=IDENTIFIER)

    return is_risky


def get_entity_original_identifier(entity):
    """
    helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
