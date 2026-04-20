############################## TERMS OF USE ################################### # noqa: E266
# The following code is provided for demonstration purposes only, and should  #
# not be used without independent verification. Recorded Future makes no      #
# representations or warranties, express, implied, statutory, or otherwise,   #
# regarding this code, and provides it strictly "as-is".                      #
# Recorded Future shall not be liable for, and you assume all risk of         #
# using the foregoing.                                                        #
###############################################################################

from __future__ import annotations

from psengine.classic_alerts import AlertUpdateError, ClassicAlertMgr
from psengine.config import Config
from pydantic import ValidationError
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param

from ..core.constants import PROVIDER_NAME
from ..core.version import __version__ as version


def clean_input(input_str: str | None) -> str | None:
    """
    Cleans the classic alert input values from ddl config options.
    """
    result = None if input_str == "None" else input_str
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
        param_name="Alert ID",
        is_mandatory=True,
        print_value=True,
    )
    assign_to = extract_action_param(
        siemplify,
        param_name="Assign To",
        is_mandatory=False,
        print_value=True,
    )
    note = extract_action_param(
        siemplify,
        param_name="Note",
        is_mandatory=False,
        print_value=True,
    )
    alert_status = extract_action_param(
        siemplify,
        param_name="Status",
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
        siemplify.LOGGER.info("Initializing psengine ClassicAlertMgr")
        alert_mgr = ClassicAlertMgr()
        siemplify.LOGGER.info("Building alert update object")
        updates = {
            "id": alert_id,
            "assignee": assign_to or None,
            "note": note or None,
            "statusInPortal": clean_input(alert_status) or None,
        }
        siemplify.LOGGER.info(f"Updating Classic Alert: {alert_id}")
        update_alert_resp = alert_mgr.update(
            updates=[{k: v for k, v in updates.items() if v is not None}]
        )
        siemplify.LOGGER.info(f"Classic Alert Update response: {update_alert_resp}")

        siemplify.result.add_result_json({"success": {"id": alert_id}})
        output_message += f"Successfully updated classic alert {alert_id} in Recorded Future."

    except ValueError as err:
        output_message = f"Classic Alert Manager ValueError: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except ValidationError as err:
        output_message = f"Error with Classic Alert Manager update parameters: {err}"
        siemplify.LOGGER.error(output_message)
        is_success = False
        status = EXECUTION_STATE_FAILED
    except AlertUpdateError as err:
        output_message = f"Error updating classic alert: {err}"
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
