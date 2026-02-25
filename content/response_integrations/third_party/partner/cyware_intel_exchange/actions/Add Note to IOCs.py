from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    ADD_NOTE_TO_IOC_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    NO_ENTITIES_ERROR,
    NO_VALID_IOC_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import get_entities, get_integration_params


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_NOTE_TO_IOC_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: list = []

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        ioc_values = get_entities(siemplify)
        note = siemplify.extract_action_param("Note", print_value=False, is_mandatory=True)
        note_type = siemplify.extract_action_param("Note Type", print_value=True, is_mandatory=True)
        is_json_str = siemplify.extract_action_param(
            "Is the Note in Json format", print_value=True, default_value="false"
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if not ioc_values:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        is_json = is_json_str.lower() == "true"

        if is_json:
            parsed_note = json.loads(note)
            note = json.dumps(parsed_note)

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )

        siemplify.LOGGER.info("Fetching indicator IDs from provided name via bulk IOC lookup.")
        ioc_lookup = cyware_manager.lookup_iocs(ioc_values)
        missing_iocs = [value for value in ioc_values if value not in ioc_lookup]
        if missing_iocs:
            siemplify.LOGGER.info(
                f"Indicator(s) not found on Cyware Intel Exchange and will be skipped: "
                f"{', '.join(missing_iocs)}"
            )
        valid_iocs = [value for value in ioc_values if value in ioc_lookup]

        if not valid_iocs:
            output_message = NO_VALID_IOC_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        indicator_responses = []
        successful_indicators = []
        failed_indicators = []

        for indicator_value in valid_iocs:
            indicator_id = ioc_lookup[indicator_value]

            try:
                response = cyware_manager.add_note_to_indicator(
                    object_id=indicator_id, text=note, note_type=note_type, is_json=is_json
                )

                indicator_responses.append({
                    "indicator": indicator_value,
                    "indicator_id": indicator_id,
                    "response": response or {},
                })

                if response:
                    note_id = response.get("id", "N/A")
                    successful_indicators.append({
                        "indicator": indicator_value,
                        "indicator_id": indicator_id,
                        "note_id": note_id,
                    })
                    siemplify.LOGGER.info(
                        f"Successfully added note to IOC '{indicator_value}' (ID: {indicator_id}). "
                        f"Note ID: {note_id}"
                    )
                else:
                    failed_indicators.append(indicator_value)
                    siemplify.LOGGER.warning(
                        f"Add note API returned empty response for IOC '{indicator_value}' "
                        f"(ID: {indicator_id})."
                    )

            except Exception as inner_error:
                failed_indicators.append(indicator_value)
                siemplify.LOGGER.error(
                    f"Failed to Add Note to IOCs '{indicator_value}' (ID: {indicator_id}). "
                    f"Error: {inner_error}"
                )
                siemplify.LOGGER.exception(inner_error)

        if indicator_responses:
            json_results = indicator_responses

        if successful_indicators:
            output_message = (
                f"Successfully added notes to {len(successful_indicators)} IOC(s). "
                f"Skipped {len(missing_iocs)} IOC(s) since they are not found on "
                f"Cyware Intel Exchange"
            )
            if failed_indicators:
                output_message += (
                    f" Failed to add notes to {len(failed_indicators)} IOC(s): "
                    f"{', '.join(failed_indicators)}."
                )
            result_value = RESULT_VALUE_TRUE
        else:
            output_message = "Failed to add note to any IOC."
            if failed_indicators:
                output_message += f" Affected IOC(s): {', '.join(failed_indicators)}."
            result_value = RESULT_VALUE_FALSE
            status = EXECUTION_STATE_FAILED

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except json.JSONDecodeError:
        output_message = "Note is marked as JSON but is not valid JSON. Enter valid JSON."
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ADD_NOTE_TO_IOC_SCRIPT_NAME, e)
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
