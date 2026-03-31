############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from psengine.config import Config
from psengine.detection import DetectionMgr, DetectionRuleFetchError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_key = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="ApiKey",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    doc_id = extract_action_param(
        siemplify,
        param_name="Rule ID",
        input_type=str,
        print_value=True,
        is_mandatory=True,
    )

    is_success = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""

    try:
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine DetectionMgr")
        detection_mgr = DetectionMgr()
        siemplify.LOGGER.info(f"Fetching Detection Rule: {doc_id}")
        fetch_detection_resp = detection_mgr.fetch(doc_id=doc_id)
        data = fetch_detection_resp.json() if fetch_detection_resp else {}
        siemplify.result.add_result_json(data)
        output_message = f"Successfully ran Fetch Detection Rule action. Found {len(data)} rule(s)."

    except ValidationError as err:
        output_message = f"Invalid parameters for Fetch Detection Rule action {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Detection Rule Manager {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except DetectionRuleFetchError as err:
        output_message = f"Error calling Detection Rule API {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = "General error performing Fetch Detection Rule action"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("\n----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.LOGGER.info(f"Result: {is_success}")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
