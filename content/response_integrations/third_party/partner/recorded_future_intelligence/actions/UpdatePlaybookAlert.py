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
from psengine.playbook_alerts import (
    PlaybookAlertMgr,
    PlaybookAlertUpdateError,
)
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME
from ..core.version import __version__ as version


def clean_input(input_str):
    """
    Cleans the playbook alert input values from ddl config options.
    """
    result = None if input_str == "None" else input_str
    result = result.replace(" ", "") if isinstance(result, str) else result
    return result


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

    alert_id = extract_action_param(
        siemplify,
        param_name="Playbook Alert ID",
        is_mandatory=True,
        print_value=True,
    )
    category = extract_action_param(
        siemplify,
        param_name="Playbook Alert Category",
        is_mandatory=False,
        print_value=True,
    )
    assign_to = extract_action_param(
        siemplify,
        param_name="Assign To",
        is_mandatory=False,
        print_value=True,
    )
    log_entry = extract_action_param(
        siemplify,
        param_name="Log Entry",
        is_mandatory=False,
        print_value=True,
    )
    pba_status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        print_value=True,
    )
    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        is_mandatory=False,
        print_value=True,
    )
    reopen_strategy = extract_action_param(
        siemplify,
        param_name="Reopen Strategy",
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
        siemplify.LOGGER.info("Initializing psengine PlaybookAlertMgr")
        pba_mgr = PlaybookAlertMgr()
        siemplify.LOGGER.info(f"Updating {category if category else ' '}Playbook Alert: {alert_id}")
        update_pba_resp = pba_mgr.update(
            alert=alert_id,
            priority=clean_input(priority),
            status=clean_input(pba_status),
            assignee=assign_to,
            log_entry=log_entry,
            reopen_strategy=clean_input(reopen_strategy),
        )
        siemplify.LOGGER.info(f"Playbook Alert Update response: {update_pba_resp.json()}")
        siemplify.result.add_result_json({"success": {"id": alert_id}})
        output_message += f"Successfully updated playbook alert {alert_id} in Recorded Future."

    except ValueError as err:
        output_message = f"Playbook Alert Manager ValueError: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValidationError as err:
        output_message = f"Error with Playbook Alert Manager update parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except PlaybookAlertUpdateError as err:
        output_message = f"Error updating playbook alert: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except Exception as err:
        output_message = f"Error executing Update Playbook Alert action: {err}"
        is_success = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {is_success}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
