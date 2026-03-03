from __future__ import annotations

import json

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    NO_ENTITIES_ERROR,
    NO_VALID_IOC_ERROR,
    REMOVE_ALLOWED_IOCS_SCRIPT_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.cyware_exceptions import CywareException
from ..core.utils import get_entities, get_integration_params


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = REMOVE_ALLOWED_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    json_results: dict = {}

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        entities = get_entities(siemplify)
        if not entities:
            output_message = NO_ENTITIES_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )
        siemplify.LOGGER.info("Fetching indicator IDs from provided name via bulk IOC lookup.")
        ioc_lookup = cyware_manager.lookup_iocs(entities)
        missing_iocs = [value for value in entities if value not in ioc_lookup]
        if missing_iocs:
            siemplify.LOGGER.info(
                f"Indicator(s) not found on Cyware Intel Exchange and will be skipped: "
                f"{', '.join(missing_iocs)}"
            )
        valid_iocs = [value for value in entities if value in ioc_lookup]
        indicator_ids = [ioc_lookup[value] for value in valid_iocs]

        if not indicator_ids:
            output_message = NO_VALID_IOC_ERROR
            result_value = RESULT_VALUE_TRUE
            status = EXECUTION_STATE_COMPLETED
            return

        response = cyware_manager.remove_allowed_iocs(indicator_ids=indicator_ids)

        if response:
            json_results = response
            message = response.get("message", "")
            output_message = (
                f"Successfully removed {len(indicator_ids)} indicator(s) from allowed list. "
                f"{message}"
            )
            result_value = RESULT_VALUE_TRUE
            siemplify.LOGGER.info(f"Remove IOCs from Allowlist response: {json.dumps(response)}")
        else:
            output_message = "Failed to Remove IOCs from Allowlist."
            result_value = RESULT_VALUE_FALSE

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(REMOVE_ALLOWED_IOCS_SCRIPT_NAME, e)
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
