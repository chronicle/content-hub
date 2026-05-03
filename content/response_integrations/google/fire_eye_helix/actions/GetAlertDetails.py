# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.FireEyeHelixConstants import (
    PROVIDER_NAME,
    GET_ALERT_DETAILS_SCRIPT_NAME,
    NOTES_LIMIT,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
from ..core.FireEyeHelixManager import FireEyeHelixManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.FireEyeHelixExceptions import FireEyeHelixNotFoundAlertException

TABLE_HEADER = "Notes"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_ALERT_DETAILS_SCRIPT_NAME
    result_value = False
    status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Configurations
    api_root = extract_configuration_param(
        siemplify, provider_name=PROVIDER_NAME, param_name="API Root", is_mandatory=True
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
    )

    # Parameters
    alert_id = extract_action_param(
        siemplify, param_name="Alert ID", is_mandatory=True, print_value=True
    )
    limit = extract_action_param(
        siemplify,
        param_name="Max Notes To Return",
        default_value=NOTES_LIMIT,
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        manager = FireEyeHelixManager(
            api_root=api_root,
            api_token=api_token,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        alert = manager.get_alert_details(alert_id=alert_id)

        if alert:
            output_message = f"Successfully returned information about the alert with ID {alert_id} from {PROVIDER_NAME}."
            siemplify.result.add_result_json(alert.to_json())
            result_value = True
            if alert.notes:
                siemplify.result.add_data_table(
                    title=TABLE_HEADER,
                    data_table=construct_csv(
                        [note.to_csv() for note in alert.notes[:limit]]
                    ),
                )
        else:
            output_message = (
                "Action wasn’t able to return information about the alert with ID {0} from {1}. Reason: "
                "Alert with ID {0} wasn't found".format(alert_id, PROVIDER_NAME)
            )

    except FireEyeHelixNotFoundAlertException:
        output_message = (
            "Action wasn’t able to return information about the alert with ID {0} from {1}. Reason: "
            "Alert with ID {0} wasn't found".format(alert_id, PROVIDER_NAME)
        )

    except Exception as e:
        output_message = f'Error executing action "Get Alert Details". Reason: {e}'
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
