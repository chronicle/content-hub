# Copyright 2025 Google LLC
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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()

    workflow_name = siemplify.parameters["Playbook Name"]

    for alert in siemplify.case.alerts:
        alert_identifier = alert.identifier
        success = super(SiemplifyAction, siemplify).attach_workflow_to_case(
            workflow_name,
            siemplify.case_id,
            alert_identifier,
        )
    if str(success) == "True":
        output_message = f"Attached Playbook [{workflow_name}] to all alerts in Case [{siemplify.case_id}]"
    else:
        output_message = f"Failed to attach Playbook [{workflow_name}] to alerts in Case [{siemplify.case_id}]"

    siemplify.end(output_message, str(success))


if __name__ == "__main__":
    main()
