from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    ADD_ALLOWED_IOCS_SCRIPT_NAME,
    COMMON_ACTION_ERROR_MESSAGE,
    NO_ENTITIES_ERROR,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import get_entities, get_integration_params


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ALLOWED_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: dict = {}

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        ioc_type = siemplify.extract_action_param("IOC Type", print_value=True, is_mandatory=True)
        reason = siemplify.extract_action_param("Reason", print_value=True, is_mandatory=True)
        entities = get_entities(siemplify)
        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        if not entities:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        cyware_manager = APIManager(
            base_url.strip(),
            access_id,
            secret_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        response = cyware_manager.add_allowed_iocs(
            ioc_type=ioc_type, values=entities, reason=reason
        )

        if response:
            json_results = response
            details = response.get("details", {})
            new_created = details.get("new_created", [])
            already_exists = details.get("already_exists", [])
            invalid = details.get("invalid", [])

            output_message = f"Successfully processed {len(entities)} indicators. "
            output_message += (
                f"New: {len(new_created)}, Already exists: {len(already_exists)}, "
                f"Invalid: {len(invalid)}."
            )
            result_value = RESULT_VALUE_TRUE
            siemplify.LOGGER.info(f"Add IOCs to Allowlist response: {json.dumps(response)}")
        else:
            output_message = "Failed to Add IOCs to Allowlist."

    except CywareException as e:
        output_message = str(e)
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(ADD_ALLOWED_IOCS_SCRIPT_NAME, e)
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.result.add_result_json(json_results)
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
