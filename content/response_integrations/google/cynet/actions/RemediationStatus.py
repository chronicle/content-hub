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
import json
from ..core.CynetManager import CynetManager
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Cynet"


@output_handler
def main():
    siemplify = SiemplifyAction()
    hash_report = {}
    remediation_status_dict = {}

    # Configuration.
    conf = siemplify.get_configuration("Cynet")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )
    cynet_manager = CynetManager(api_root, username, password, verify_ssl)

    remediation_id = siemplify.parameters.get("Remediation Id")
    remidaition_status = cynet_manager.get_remediation_status(remediation_id)

    if remidaition_status:
        status_message = ""
        for key, val in list(remidaition_status.items()):
            status_message += f"{key}: {val}, "
        output_message = f"Remidiation status \n{status_message[:-1]}"
        result_value = "true"
    else:
        output_message = "Could not find results."
        result_value = "false"

    siemplify.result.add_result_json(json.dumps(remidaition_status))
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
