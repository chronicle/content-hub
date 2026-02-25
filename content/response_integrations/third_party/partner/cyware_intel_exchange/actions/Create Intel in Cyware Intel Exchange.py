from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    CREATE_INTEL_IN_CTIX_SCRIPT_NAME,
    NO_ENTITIES_ERROR,
    QUICK_INTEL_STATUS_FAILURE_STATUSES,
    QUICK_INTEL_STATUS_MAX_ATTEMPTS,
    QUICK_INTEL_STATUS_POLL_INTERVAL,
    QUICK_INTEL_STATUS_SUCCESS_STATUSES,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import (
    get_entities,
    get_integration_params,
    string_to_list,
    validate_integer_param
)


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = CREATE_INTEL_IN_CTIX_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: list = []

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        ioc_values = get_entities(siemplify)
        ioc_type = siemplify.extract_action_param("IOC Type", print_value=True, is_mandatory=True)
        title = siemplify.extract_action_param("Title", print_value=True, is_mandatory=True)
        tlp = siemplify.extract_action_param("TLP", print_value=True)
        metadata_confidence_score = siemplify.extract_action_param(
            "Metadata Confidence Score", print_value=True
        )
        tags = siemplify.extract_action_param("Tags", print_value=True)
        valid_until = siemplify.extract_action_param("Deprecates After", print_value=True)
        description = siemplify.extract_action_param("Description", print_value=True)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if description:
            description = description.strip()
            if len(description) > 1000:
                output_message = "Description must not exceed 1000 characters."
                result_value = RESULT_VALUE_FALSE
                status = EXECUTION_STATE_FAILED
                return

        if not ioc_values:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        if len(title.strip()) > 100:
            output_message = "Title must not exceed 100 characters."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED
            return

        tags_list = string_to_list(tags, strip_quotes=True, param_name="Tags") if tags else []

        confidence = None
        if metadata_confidence_score:
            confidence = validate_integer_param(
                metadata_confidence_score,
                "Metadata Confidence Score",
                zero_allowed=True,
                max_value=100,
            )

        resolved_tlp = (tlp or "NONE").upper()

        valid_until_value = None
        if valid_until and valid_until.strip():
            valid_until_days = validate_integer_param(
                valid_until.strip(),
                "Deprecates After",
                zero_allowed=False,
                max_value=1000,
            )
            valid_until_value = str(valid_until_days)

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )
        indicator_results: List[Dict[str, Any]] = []
        failed_indicators: List[Dict[str, str]] = []

        for indicator_value in ioc_values:
            metadata_payload: Dict[str, Any] = {
                "tlp": resolved_tlp,
                "default_marking_definition": resolved_tlp,
                "tags": tags_list,
                "is_apply_all": True,
            }

            if confidence is not None:
                metadata_payload["confidence"] = confidence
            if description:
                metadata_payload["description"] = description
            if valid_until_value:
                metadata_payload["valid_until"] = valid_until_value

            body: Dict[str, Any] = {
                "context": "QUICK_ADD_INTEL_FLOW",
                "metadata": metadata_payload,
                "indicators": {
                    ioc_type: indicator_value,
                },
                "title": title.strip(),
                "create_intel_feed": True,
            }
            if valid_until_value:
                body["valid_until"] = valid_until_value

            siemplify.LOGGER.info(
                f"Prepared intel creation body for '{indicator_value}': {json.dumps(body)}"
            )

            try:
                creation_response = cyware_manager.create_intel(body)

                if not creation_response:
                    raise CywareException(
                        f"Failed to create intel in CTIX for IOC '{indicator_value}'."
                    )

                task_id = creation_response.get("task_id")
                siemplify.LOGGER.info(
                    f"Intel created successfully for '{indicator_value}'. Task ID: {task_id}"
                )

                status_response = None
                if task_id:
                    attempt = 0
                    while True:
                        attempt += 1
                        siemplify.LOGGER.info(
                            f"Checking quick intel status for '{indicator_value}' "
                            f"(Attempt {attempt}/{QUICK_INTEL_STATUS_MAX_ATTEMPTS})."
                        )
                        status_response = cyware_manager.get_quick_intel_status(task_id)
                        report_status = (status_response.get("report_status") or "").upper()

                        if report_status in QUICK_INTEL_STATUS_SUCCESS_STATUSES:
                            break
                        if report_status in QUICK_INTEL_STATUS_FAILURE_STATUSES:
                            raise CywareException(
                                f"Quick intel processing failed for '{indicator_value}' "
                                f"with status '{report_status}'."
                            )
                        if attempt >= QUICK_INTEL_STATUS_MAX_ATTEMPTS:
                            raise CywareException(
                                f"Timed out while waiting for quick intel report to complete "
                                f"for '{indicator_value}'."
                            )
                        time.sleep(QUICK_INTEL_STATUS_POLL_INTERVAL)
                else:
                    siemplify.LOGGER.warning(
                        f"Task ID missing in creation response for '{indicator_value}'. "
                        f"Skipping status check."
                    )

                indicator_results.append({
                    "indicator": indicator_value,
                    "creation_response": creation_response,
                    "status_response": status_response,
                })

            except Exception as inner_error:
                failed_indicators.append({"indicator": indicator_value, "error": str(inner_error)})
                siemplify.LOGGER.error(f"Failed to process IOC '{indicator_value}': {inner_error}")
                siemplify.LOGGER.exception(inner_error)

        if indicator_results:
            json_results = indicator_results

        success_count = len(indicator_results)
        failure_count = len(failed_indicators)

        if success_count:
            output_message = f"Successfully created intel in CTIX for {success_count} IOC(s)."
            if failure_count:
                failed_values = ", ".join(
                    f"{failure.get('indicator', 'N/A')} "
                    f"(Reason: {failure.get('error', 'Unknown error')})"
                    for failure in failed_indicators
                )
                output_message += (
                    f" Failed to create intel for {failure_count} IOC(s): {failed_values}."
                )
            result_value = RESULT_VALUE_TRUE
        else:
            output_message = "Failed to create intel in CTIX for all provided IOCs."
            if failure_count:
                failed_values = ", ".join(
                    f"{failure.get('indicator', 'N/A')} "
                    f"(Reason: {failure.get('error', 'Unknown error')})"
                    for failure in failed_indicators
                )
                output_message += f" Affected IOC(s): {failed_values}."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(CREATE_INTEL_IN_CTIX_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
