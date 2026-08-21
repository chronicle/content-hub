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
from ..core.SentinelOneManager import (
    SentinelOneManager,
    SentinelOneAgentNotFoundError,
    SentinelOneManagerError,
)
from soar_sdk.SiemplifyUtils import flat_dict_to_csv

# Consts.
SENTINEL_ONE_PROVIDER = "SentinelOne"
ACTION_NAME = "Check Containment Status"

STATUS_MAPPING = {
    "disconnected": "contained",
    "disconnecting": "containment_requested",
    "connecting": "uncontainment_requested",
    "connected": "uncontained",
}


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(SENTINEL_ONE_PROVIDER)
    sentinel_one_manager = SentinelOneManager(
        conf["Api Root"], conf["Username"], conf["Password"]
    )

    agent_id = siemplify.extract_action_param("Agent ID", is_mandatory=True)

    result_value = False
    json_result = {
        "endpoint_containment_status": {
            agent_id: {
                "status": "unknown",
                "reason": None,
            }
        }
    }

    try:
        raw_status = sentinel_one_manager.get_agent_network_status(agent_id)
        containment_status = STATUS_MAPPING.get(raw_status.lower(), "unknown")

        json_result["endpoint_containment_status"][agent_id]["status"] = containment_status

        if containment_status != "unknown":
            result_value = True
            output_message = f"Containment status for agent {agent_id}: {containment_status}"
        else:
            output_message = f"Could not determine containment status for agent {agent_id} (raw status: {raw_status})."

        siemplify.result.add_data_table(
            "Containment Statuses",
            flat_dict_to_csv({agent_id: containment_status}),
        )

    except Exception as err:
        output_message = f"Error executing action '{ACTION_NAME}'. Reason: {err}"
        json_result["endpoint_containment_status"][agent_id]["status"] = "unknown"
        json_result["endpoint_containment_status"][agent_id]["reason"] = str(err)
        siemplify.result.add_data_table(
            "Unsuccessful Attempts",
            flat_dict_to_csv({agent_id: str(err)}),
        )

    siemplify.result.add_result_json(json_result)
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
