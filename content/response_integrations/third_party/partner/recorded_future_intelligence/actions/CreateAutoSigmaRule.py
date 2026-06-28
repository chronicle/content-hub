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
from psengine.malware_intel import AutoSigmaFetchJobError, AutoSigmaJobCreationError, AutoSigmaMgr
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

    job_name = extract_action_param(
        siemplify,
        param_name="Job Name",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    query = extract_action_param(
        siemplify,
        param_name="Query",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    start_date = extract_action_param(
        siemplify,
        param_name="Start Date",
        input_type=str,
        is_mandatory=True,
        print_value=True,
    )
    end_date = extract_action_param(
        siemplify,
        param_name="End Date",
        input_type=str,
        is_mandatory=False,
        print_value=True,
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
        siemplify.LOGGER.info("Initializing psengine AutoSigmaMgr")
        auto_sigma_mgr = AutoSigmaMgr()
        siemplify.LOGGER.info("Creating new auto Sigma job")
        create_resp = auto_sigma_mgr.create_rule_job(
            name=job_name,
            query=query,
            start_date=start_date,
            end_date=end_date,
        )
        siemplify.LOGGER.info("Fetching auto Sigma job, waiting for completion")
        fetch_resp = auto_sigma_mgr.fetch_rule_job_result(
            job_id=create_resp.job_id,
            wait_until_finished=True,
        )
        data = fetch_resp.json()
        siemplify.result.add_result_json(data)
        output_message += f"Successfully created new Auto Sigma Rule: {fetch_resp.job_id}."

    except ValidationError as err:
        output_message = f"Error with Auto Sigma Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Auto Sigma Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AutoSigmaJobCreationError as err:
        output_message = f"Error creating Auto Sigma job in Recorded Future: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AutoSigmaFetchJobError as err:
        output_message = f"Error fetching Auto Sigma job result from Recorded Future: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as err:
        output_message = f"Error executing Create Auto Sigma Rule action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
