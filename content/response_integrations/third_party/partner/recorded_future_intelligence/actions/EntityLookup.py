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
from psengine.entity_match import EntityMatchMgr, MatchApiError
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
    entity_id = extract_action_param(
        siemplify,
        param_name="Entity ID",
        input_type=str,
        print_value=True,
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
        siemplify.LOGGER.info("Initializing psengine EntityMatchMgr")
        entity_match_mgr = EntityMatchMgr()
        siemplify.LOGGER.info("Fetching entity from Recorded Future")
        entity_lookup_resp = entity_match_mgr.lookup(id_=entity_id)

        if entity_lookup_resp is not None:
            data = entity_lookup_resp.json()
            output_message = "Successfully ran Entity Lookup action. Matched Entity ID."
        else:
            data = {}
            output_message = "Successfully ran Entity Lookup action. Did not match Entity ID."
        siemplify.result.add_result_json(data)

    except ValidationError as err:
        output_message = f"Invalid parameters for Entity Lookup action {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Entity Match Manager {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except MatchApiError as err:
        output_message = f"Error calling Entity Match API {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        output_message = "General error performing Entity Lookup action"
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
