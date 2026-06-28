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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.constants import RESOLVE_INCIDENT_ACTION_SCRIPT_NAME


def main():
    # Configuration.
    siemplify = SiemplifyAction()

    siemplify.script_name = RESOLVE_INCIDENT_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    xdr_manager = create_api_client(siemplify)

    # Parameters.
    incident_id = siemplify.parameters.get("Incident ID")
    comment = siemplify.parameters.get("Resolve Comment")
    incident_status = siemplify.parameters.get("Status")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        result_value = True
        status = EXECUTION_STATE_COMPLETED
        xdr_manager.update_an_incident(
            incident_id, resolve_comment=comment, status=incident_status
        )
        output_message = f"Incident: {incident_id} Successfully Resolved "
    except Exception as e:
        output_message = f"Failed to resolved incident: {e}"
        siemplify.LOGGER.error(f"Failed to resolved incident: {incident_id}")
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
