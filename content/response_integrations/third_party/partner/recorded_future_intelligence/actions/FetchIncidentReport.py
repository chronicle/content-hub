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
from psengine.identity.errors import IncidentReportFetchError
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

    source = extract_action_param(
        siemplify,
        param_name="Source",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    include_details = extract_action_param(
        siemplify,
        param_name="Include Details",
        input_type=bool,
        print_value=True,
        default_value=True,
        is_mandatory=False,
    )
    organization_id = extract_action_param(
        siemplify,
        param_name="Organization ID",
        input_type=str,
        print_value=True,
        default_value=None,
        is_mandatory=False,
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
        siemplify.LOGGER.info("Fetching Incident Report from Recorded Future")
        fetch_resp = identity_mgr.fetch_incident_report(
            source=source,
            include_details=include_details,
            organization_id=organization_id,
            max_results=max_results,
        )
        data = fetch_resp.json()
        siemplify.result.add_result_json(data)
        output_message += "Successfully fetched incident report from Recorded Future."

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
    except IncidentReportFetchError as err:
        output_message = f"Error fetching incident report from Recorded Future: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED

    except Exception as err:
        output_message = f"Error executing Fetch Incident Report action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
