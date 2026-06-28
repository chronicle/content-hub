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
from palo_alto_cortex_xdr.core.exceptions import XDRMissingParametersException
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED, EXECUTION_STATE_COMPLETED

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.constants import INTEGRATION_NAME, UPDATE_INCIDENT_ACTION_SCRIPT_NAME


ID_NOT_FOUND = "incident not found"
SELECT_ONE = "Select One"


def main():
    # Configuration.
    siemplify = SiemplifyAction()
    siemplify.script_name = UPDATE_INCIDENT_ACTION_SCRIPT_NAME

    siemplify.LOGGER.info("================= Main - Param Init =================")
    incident_id = siemplify.parameters.get("Incident ID")
    assigned_user = siemplify.parameters.get("Assigned User Name")
    severity = siemplify.parameters.get("Severity")
    incident_status = siemplify.parameters.get("Status")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    xdr_manager = create_api_client(siemplify)
    err_msg_prefix = (
        f"Error executing action {UPDATE_INCIDENT_ACTION_SCRIPT_NAME}. Reason:"
    )

    try:
        if not assigned_user and incident_status == severity == SELECT_ONE:
            raise XDRMissingParametersException(
                'At least of the "Assigned User Name", "Severity" or "Status"'
                "parameters should have a provided value."
            )
        xdr_manager.update_an_incident(
            incident_id,
            assigned_user=assigned_user,
            severity=None if severity == SELECT_ONE else severity,
            status=None if incident_status == SELECT_ONE else incident_status,
        )
        output_message = (
            "Successfully updated one or more fields of incident with ID: "
            f"{incident_id}"
        )
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED
    except XDRMissingParametersException as e:
        siemplify.LOGGER.error(e)
        output_message = f"{err_msg_prefix} {e}"
        result_value = "false"
        status = EXECUTION_STATE_FAILED
    except Exception as e:
        error_string = str(e).lower()
        if ID_NOT_FOUND in error_string:
            output_message = (
                f"{err_msg_prefix} incidents with ID {incident_id} wasn't found in "
                f"{INTEGRATION_NAME}, please check the spelling."
            )
        else:
            siemplify.LOGGER.error(f"Failed to update incident: {incident_id}")
            siemplify.LOGGER.exception(e)
            output_message = f"{err_msg_prefix} {e}"
        result_value = "false"
        status = EXECUTION_STATE_FAILED
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
