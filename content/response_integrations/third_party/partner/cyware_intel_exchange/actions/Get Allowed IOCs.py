from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import construct_csv, output_handler

from ..core import datamodels
from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    GET_ALLOWED_IOCS_SCRIPT_NAME,
    MAX_TABLE_RECORDS,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE
)
from ..core.cyware_exceptions import CywareException, InvalidIntegerException
from ..core.utils import get_integration_params, validate_integer_param


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALLOWED_IOCS_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_FALSE
    results_json: dict = {}

    try:
        base_url, access_id, secret_key, verify_ssl = get_integration_params(siemplify)
        ioc_type = siemplify.extract_action_param("IOC Type", print_value=True)
        created_from_str = siemplify.extract_action_param("Created From", print_value=True)

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        created_from = (
            validate_integer_param(created_from_str, "Created From", zero_allowed=True)
            if created_from_str
            else None
        )
        cyware_manager = APIManager(
            base_url.strip(), access_id, secret_key, verify_ssl=verify_ssl, siemplify=siemplify
        )

        response = cyware_manager.get_allowed_iocs(ioc_type=ioc_type, created_from=created_from)

        results = response.get("results", [])
        total = response.get("total", 0)

        if results:
            results_json = response
            allowed_iocs = [datamodels.AllowedIOC(ioc) for ioc in results]
            csv_output = [ioc.to_csv() for ioc in allowed_iocs]

            if len(csv_output) > MAX_TABLE_RECORDS:
                csv_output = csv_output[:MAX_TABLE_RECORDS]
                output_message = (
                    f"Successfully retrieved {len(results)} allowed IOCs (Total: {total}). "
                    f"Showing first {MAX_TABLE_RECORDS} records in table."
                )
            else:
                output_message = (
                    f"Successfully retrieved {len(results)} allowed IOCs (Total: {total})."
                )

            siemplify.result.add_data_table("Allowed IOCs", construct_csv(csv_output), "CTIX")
            result_value = RESULT_VALUE_TRUE
            siemplify.LOGGER.info(f"Retrieved {len(results)} allowed IOCs")
        else:
            output_message = "No allowed IOCs found."
            result_value = RESULT_VALUE_TRUE

    except InvalidIntegerException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except CywareException as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(GET_ALLOWED_IOCS_SCRIPT_NAME, e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.result.add_result_json(results_json)
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
