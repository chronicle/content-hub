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
from psengine.identity import IdentityMgr
from psengine.identity.errors import IdentitySearchError
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.validation import ParameterValidator

from ..core.constants import CSV_DELIMETER, PROVIDER_NAME
from ..core.version import __version__ as version


@output_handler
def main():
    siemplify = SiemplifyAction()
    param_validator = ParameterValidator(siemplify=siemplify)

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

    names = param_validator.validate_csv(
        param_name="names",
        csv_string=extract_action_param(
            siemplify,
            param_name="Names",
            input_type=str,
            print_value=True,
            default_value=None,
            is_mandatory=True,
        ),
        delimiter=CSV_DELIMETER,
        default_value=None,
    )
    max_results = extract_action_param(
        siemplify,
        param_name="Max Results",
        input_type=int,
        print_value=True,
        default_value=10,
        is_mandatory=False,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine IdentityMgr")
        identity_mgr = IdentityMgr()
        siemplify.LOGGER.info("Searching dumps in Recorded Future")
        search_dump_resp = identity_mgr.search_dump(names=names, max_results=max_results)
        data = [dump.json() for dump in search_dump_resp]
        siemplify.result.add_result_json(data)
        output_message = (
            f"Successfully ran Search Dump action. Found {len(data)} dump(s)."
        )

    except ValidationError as err:
        output_message = f"Error with Identity Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Identity Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except IdentitySearchError as err:
        output_message = f"Error calling Identity API: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except Exception as err:
        output_message = f"Error executing Search Dump action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
