from __future__ import annotations

import base64
import os

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DOWNLOAD_PCAP_SCRIPT_NAME,
    INTEGRATION_NAME,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
)
from ..core.UtilsManager import save_attachment, validate_integer
from ..core.VectraQUXExceptions import (
    FileNotFoundException,
    InvalidIntegerException,
    ItemNotFoundException,
    VectraQUXException,
)
from ..core.VectraQUXManager import VectraQUXManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_PCAP_SCRIPT_NAME

    siemplify.LOGGER.info("----------- Main - Param Init ---------")

    # Configuration Parameters
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
    )

    # Action Parameters
    detection_id = extract_action_param(
        siemplify,
        param_name="Detection ID",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started ------------")

    status = EXECUTION_STATE_COMPLETED
    result_value = RESULT_VALUE_TRUE

    try:
        filepath = os.path.dirname(os.path.abspath(__file__))
        vectra_qux_manager = VectraQUXManager(
            api_root,
            api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        detection_id = validate_integer(detection_id, field_name="Detection ID")

        file_content, filename = vectra_qux_manager.download_pcap(detection_id)

        # Save attachment to given path
        local_path = save_attachment(path=filepath, name=filename, content=file_content)
        siemplify.LOGGER.info(f"The Local path is: {local_path}")

        siemplify.result.add_attachment(
            "PCAP file",
            filename,
            base64.b64encode(file_content).decode(),
        )

        output_message = (
            f"Got the file: {filename} for the detection ID {detection_id}."
        )

    except InvalidIntegerException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"{e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except FileNotFoundException as e:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to download file for the detection ID {detection_id}. Error - {e}"
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except ItemNotFoundException as e:
        status = EXECUTION_STATE_FAILED
        output_message = f"File not found for detection ID - {detection_id}. Please provide valid detection ID. Error - {e}"
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except VectraQUXException as e:
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to get detail of the detection ID {detection_id}. Error: {e}"
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            DOWNLOAD_PCAP_SCRIPT_NAME,
            e,
        )
        result_value = RESULT_VALUE_FALSE
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"status: {status}")
    siemplify.LOGGER.info(f"result_value: {result_value}")
    siemplify.LOGGER.info(f"output_message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
