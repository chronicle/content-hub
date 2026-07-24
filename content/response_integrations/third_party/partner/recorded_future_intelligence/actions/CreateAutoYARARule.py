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
from psengine.malware_intel import AutoYaraFetchJobError, AutoYaraJobCreationError, AutoYaraMgr
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
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
        is_mandatory=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    is_success = True
    output_message = ""
    status = EXECUTION_STATE_COMPLETED

    try:
        hashes = [
            hash_.identifier
            for hash_ in siemplify.target_entities
            if hash_.entity_type == EntityTypes.FILEHASH
        ]
        siemplify.LOGGER.info("Initializing psengine configuration")
        Config.init(
            client_verify_ssl=verify_ssl,
            rf_token=api_key,
            app_id=f"ps-google-soar/{version}",
        )
        siemplify.LOGGER.info("Initializing psengine AutoYaraMgr")
        auto_yara_mgr = AutoYaraMgr()
        siemplify.LOGGER.info("Creating new auto YARA job")
        create_resp = auto_yara_mgr.create_rule_job(
            hashes=hashes,
            name=job_name,
            query=query,
        )
        siemplify.LOGGER.info("Fetching auto YARA job, waiting for completion")
        fetch_resp = auto_yara_mgr.fetch_rule_job_result(
            job_id=create_resp.job_id,
            wait_until_finished=True,
        )
        data = fetch_resp.json()
        siemplify.result.add_result_json(data)
        output_message += f"Successfully created new Auto Yara Rule: {fetch_resp.job.job_id}."

    except ValidationError as err:
        output_message = f"Error with Auto YARA Manager parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValueError as err:
        output_message = f"Error creating Auto YARA Manager: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AutoYaraJobCreationError as err:
        output_message = f"Error creating Auto YARA job in Recorded Future: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AutoYaraFetchJobError as err:
        output_message = f"Error fetching Auto YARA job result from Recorded Future: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as err:
        output_message = f"Error executing Create Auto YARA Rule action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
