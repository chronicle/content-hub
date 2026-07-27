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
from ..core.CaSoapManager import CaSoapManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("CaServiceDesk")
    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    ca_manager = CaSoapManager(api_root, username, password)

    ticket_id = siemplify.parameters["Ticket ID"]
    close_reason = siemplify.parameters["Close Reason"]

    incident_id = ca_manager.close_incident(ticket_id, close_reason)

    if incident_id:
        output_message = f"Incident {ticket_id} closed successfully."
        result_value = "true"

    else:
        output_message = f"There was a problem closing ticket number {ticket_id}."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
