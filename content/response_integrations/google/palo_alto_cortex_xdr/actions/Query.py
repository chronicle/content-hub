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
from soar_sdk.SiemplifyUtils import construct_csv
from soar_sdk.SiemplifyAction import SiemplifyAction

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.constants import QUERY_ACTION_SCRIPT_NAME


def main():
    # Configuration.
    siemplify = SiemplifyAction()

    siemplify.script_name = QUERY_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # Parameters.
    incident_id = siemplify.parameters.get("Incident ID")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    xdr_manager = create_api_client(siemplify)
    alerts = []
    result_value = 0
    incident_extra_data = xdr_manager.get_extra_incident_data(incident_id)

    if incident_extra_data:
        # create csv table of incident alerts
        alerts = incident_extra_data.get("alerts", {}).get("data", [])
        if alerts:
            csv_output = construct_csv(alerts)
            siemplify.result.add_data_table(
                f"Incident {incident_id} Alerts", csv_output
            )

    if incident_extra_data and alerts:
        output_message = f"Successfully fetched incident information for incident with ID: {incident_id} (Including the alerts, network artifacts, and file artifacts)"
        result_value = len(alerts)
    else:
        output_message = f"Not found data for incident with ID: {incident_id}."

    siemplify.result.add_result_json(incident_extra_data)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
