# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import json
import sys
import time
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import DomainEntityInfo, EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param, extract_action_param
from ..core.UrlScanManager import UrlScanManager
from ..core.UrlScanParser import UrlScanParser
from ..core.UtilsManager import get_entity_original_identifier, get_screenshot_content_base64
from ..core.constants import (
    INTEGRATION_NAME,
    URL_CHECK_ACTION_NAME,
    VISIBILITY_MAPPER,
    REPORT_LINK_TITLE,
    SCREENSHOT_TITLE,
    DEFAULT_THRESHOLD,
    ATTACHMENT_FILE_NAME,
)
from ..core.exceptions import UrlDnsScanError
from soar_sdk.Siemplify import InsightSeverity, InsightType


SUPPORTED_ENTITY_TYPES: list[str] = [
    EntityTypes.URL,
    EntityTypes.ADDRESS,
    EntityTypes.DOMAIN,
]
ENTITIES_REQUIRING_HTTP: list[str] = [EntityTypes.ADDRESS, EntityTypes.DOMAIN]


def start_operation(siemplify, manager, suitable_entities):
    visibility = extract_action_param(
        siemplify,
        param_name="Visibility",
        print_value=True,
        default_value=VISIBILITY_MAPPER["public"],
    )

    failed_entities, successful_entities, dns_failed_entities, result_value = (
        [],
        [],
        [],
        {},
    )
    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = {"in_progress": {}, "completed": {}, "failed": [], "dns_failed": []}

    for entity in suitable_entities:
        try:
            url_to_submit: str = _prepare_url_for_submission(entity)

            siemplify.LOGGER.info(f"Started submitting entity: {url_to_submit}")

            submit_scan_id = manager.submit_url_for_scan(
                url=url_to_submit,
                visibility=VISIBILITY_MAPPER[visibility],
            )

            result_value["in_progress"][get_entity_original_identifier(entity)] = submit_scan_id
            successful_entities.append(get_entity_original_identifier(entity))
            # Stop action not to reach limit of requests
            pause_action_execution()

            siemplify.LOGGER.info(
                f"Finish submitting entity: {get_entity_original_identifier(entity)}"
            )

        except UrlDnsScanError as err:
            dns_failed_entities.append(get_entity_original_identifier(entity))
            result_value["dns_failed"].append(get_entity_original_identifier(entity))
            siemplify.LOGGER.error(
                f"An error occurred on entity {get_entity_original_identifier(entity)}"
            )
            siemplify.LOGGER.exception(err)
        except Exception as err:
            failed_entities.append(get_entity_original_identifier(entity))
            result_value["failed"].append(get_entity_original_identifier(entity))
            siemplify.LOGGER.error(
                f"An error occurred on entity {get_entity_original_identifier(entity)}"
            )
            siemplify.LOGGER.exception(err)

    if successful_entities:
        output_message += f"Successfully submitted the following URLs for scan: \n {', '.join(successful_entities)} \n"
        result_value = json.dumps(result_value)

    if failed_entities:
        output_message += f"Action wasn’t able to submitted the following URLs for scan: \n {', '.join(failed_entities)} \n"

    if not successful_entities:
        if failed_entities:
            output_message = f"Action wasn’t able to scan the following URLs using {INTEGRATION_NAME}: \n {', '.join(failed_entities)} \n"

        if dns_failed_entities:
            output_message += f"The following entities: {', '.join(dns_failed_entities)} cannot be scanned using {INTEGRATION_NAME}."

        if not failed_entities and not dns_failed_entities:
            output_message = "No entities were scanned."

        result_value = False
        status = EXECUTION_STATE_COMPLETED

    return output_message, result_value, status


def _prepare_url_for_submission(entity: DomainEntityInfo) -> str:
    """Prepare a URL for scanning based on entity type.
    Ensures the URL is properly prefixed with HTTP/HTTPS if required.
    Args:
        entity (DomainEntityInfo): The entity to prepare.

    Returns:
        str: The prepared URL.
    """
    url: str = get_entity_original_identifier(entity)

    if entity.entity_type in ENTITIES_REQUIRING_HTTP:
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"

    return url


def query_operation_status(siemplify, manager, scan_report, suitable_entities):
    completed_entities = {}

    for entity, scan_id in scan_report["in_progress"].items():
        try:
            url_report = manager.get_url_scan_report(scan_id=scan_id)
            if url_report:
                completed_entities[entity] = url_report.to_json()
            # Stop action not to reach limit of requests
            pause_action_execution()
        except Exception as err:
            scan_report["failed"].append(entity)
            siemplify.LOGGER.error(f"An error occurred when checking status for url {entity}")
            siemplify.LOGGER.exception(err)

    for key in completed_entities.keys():
        scan_report["in_progress"].pop(key)
    # Update completed entities with completed_entities dict including json_result
    scan_report["completed"].update(completed_entities)

    if scan_report["in_progress"]:
        status = EXECUTION_STATE_INPROGRESS
        result_value = json.dumps(scan_report)
        output_message = f"Waiting for results for the following entities: \n {', '.join(scan_report['in_progress'].keys())} \n"
    else:
        output_message, result_value, status = finish_operation(
            siemplify=siemplify,
            manager=manager,
            suitable_entities=suitable_entities,
            completed_entities=scan_report["completed"],
            failed_entities=scan_report["failed"],
            dns_failed_entities=scan_report["dns_failed"],
        )

    return output_message, result_value, status


def finish_operation(
    siemplify,
    manager,
    suitable_entities,
    completed_entities,
    failed_entities,
    dns_failed_entities,
):
    threshold = extract_action_param(
        siemplify,
        param_name="Threshold",
        print_value=True,
        input_type=int,
        default_value=DEFAULT_THRESHOLD,
    )
    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        print_value=True,
        input_type=bool,
        default_value=True,
    )
    only_suspicious_insight = extract_action_param(
        siemplify,
        param_name="Only Suspicious Insight",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    add_screenshot_to_insight = extract_action_param(
        siemplify,
        param_name="Add Screenshot To Insight",
        print_value=True,
        input_type=bool,
        default_value=False,
    )

    parser = UrlScanParser()

    output_message = ""
    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    suspicious_entities = []
    json_results = {}

    for entity in suitable_entities:
        if get_entity_original_identifier(entity) in completed_entities.keys():
            entity_result = parser.build_url_object(
                completed_entities[get_entity_original_identifier(entity)]
            )
            json_results[get_entity_original_identifier(entity)] = entity_result.to_shorten_json()

            if int(entity_result.score) >= threshold:
                entity.is_suspicious = True
                suspicious_entities.append(get_entity_original_identifier(entity))

            entity.additional_properties.update(entity_result.to_enrichment())

            entity.is_enriched = True
            successful_entities.append(entity)
            if entity_result.result_link:
                siemplify.result.add_link(
                    REPORT_LINK_TITLE.format(get_entity_original_identifier(entity)),
                    entity_result.result_link,
                )

            try:
                if entity_result.screenshot_url:
                    screenshot_content = manager.get_screenshot_content(
                        url=entity_result.screenshot_url
                    )
                    base64_screenshot = get_screenshot_content_base64(screenshot_content)
                    siemplify.result.add_attachment(
                        title=SCREENSHOT_TITLE.format(get_entity_original_identifier(entity)),
                        filename=ATTACHMENT_FILE_NAME.format(entity_result.uuid),
                        file_contents=base64_screenshot.decode(),
                    )

            except Exception as e:
                siemplify.LOGGER.info(
                    f"Screenshot for entity {get_entity_original_identifier(entity)} is not available. Reason: {e}."
                )
                add_screenshot_to_insight = False

            screenshot = None
            if add_screenshot_to_insight:
                screenshot = base64_screenshot

            if create_insight:
                if only_suspicious_insight:
                    if int(entity_result.score) >= threshold:
                        siemplify.create_case_insight(
                            triggered_by=INTEGRATION_NAME,
                            title="URL Details",
                            content=entity_result.as_url_insight(screenshot_to_add=screenshot),
                            entity_identifier=get_entity_original_identifier(entity),
                            severity=InsightSeverity.INFO,
                            insight_type=InsightType.Entity,
                        )
                else:
                    siemplify.create_case_insight(
                        triggered_by=INTEGRATION_NAME,
                        title="URL Details",
                        content=entity_result.as_url_insight(screenshot_to_add=screenshot),
                        entity_identifier=get_entity_original_identifier(entity),
                        severity=InsightSeverity.INFO,
                        insight_type=InsightType.Entity,
                    )

    if successful_entities:
        output_message += f"Following entities were scanned by {INTEGRATION_NAME}: \n {', '.join([get_entity_original_identifier(entity) for entity in successful_entities])} \n"
        siemplify.update_entities(successful_entities)

    if suspicious_entities:
        output_message += f"Following entities were found suspicious by {INTEGRATION_NAME}: \n {', '.join(suspicious_entities)} \n"

    if failed_entities:
        output_message += f"Action wasn’t able to scan the following URLs using {INTEGRATION_NAME}: \n {', '.join(failed_entities)} \n"

    if dns_failed_entities:
        output_message += f"The following entities: {', '.join(dns_failed_entities)} cannot be scanned using {INTEGRATION_NAME}."

    if not successful_entities:
        output_message = "No entities were scanned."
        result_value = False

    if json_results:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    return output_message, result_value, status


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = URL_CHECK_ACTION_NAME
    mode = "Main" if is_first_run else "Get Report"
    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
        is_mandatory=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = False
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITY_TYPES
    ]

    try:
        manager = UrlScanManager(
            api_key=api_key, verify_ssl=verify_ssl, force_check_connectivity=True
        )

        if is_first_run:
            output_message, result_value, status = start_operation(
                siemplify, manager=manager, suitable_entities=suitable_entities
            )
        if status == EXECUTION_STATE_INPROGRESS:
            scan_report = (
                result_value
                if result_value
                else extract_action_param(
                    siemplify, param_name="additional_data", default_value="{}"
                )
            )
            output_message, result_value, status = query_operation_status(
                siemplify=siemplify,
                manager=manager,
                scan_report=json.loads(scan_report),
                suitable_entities=suitable_entities,
            )

    except Exception as err:
        output_message = f"General error performing action {URL_CHECK_ACTION_NAME} Reason: {err}"
        result_value = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )

    siemplify.end(output_message, result_value, status)


def pause_action_execution():
    """
    The most efficient approach would be to wait at least 10 seconds before starting to poll, and then only polling
    2-second intervals with an eventual upper timeout in case the scan does not return.
    https://urlscan.io/about-api/#submission
    """
    time.sleep(2)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
