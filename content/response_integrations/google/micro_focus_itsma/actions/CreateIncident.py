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
from ..core.MicroFocusITSMAManager import MicroFocusITSMAManager


ITSMA_PROVIDER = "MicroFocusITSMA"


@output_handler
def main():
    # Configuration
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(ITSMA_PROVIDER)
    itsma_manager = MicroFocusITSMAManager(
        conf["API Root"],
        conf["Username"],
        conf["Password"],
        conf["Tenant ID"],
        conf["External System"],
        conf["External ID"],
        conf["Verify SSL"],
    )

    # Parameters.
    display_label = siemplify.parameters.get("Display Label")
    description = siemplify.parameters.get("Description")
    impact_scope = siemplify.parameters.get("Impact Scope")
    urgency = siemplify.parameters.get("Urgency")
    service_id = siemplify.parameters.get("Service ID")

    incident_id = itsma_manager.create_incident(
        display_label, description, impact_scope, urgency, service_id
    )

    if incident_id:
        output_message = (
            f'An incident with id "{incident_id}" was successfully created.'
        )
    else:
        output_message = "No ticket was created."

    siemplify.end(output_message, incident_id)


if __name__ == "__main__":
    main()
