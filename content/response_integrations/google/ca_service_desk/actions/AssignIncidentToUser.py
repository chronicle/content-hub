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

# Consts
ACTION_SCRIPT_NAME = "Assign Incident To User"


@output_handler
def main():

    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_SCRIPT_NAME

    conf = siemplify.get_configuration("CaServiceDesk")

    api_root = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]

    ca_manager = CaSoapManager(api_root, username, password)

    # Parameters
    ticket_id = siemplify.parameters.get("Ticket ID")
    username = siemplify.parameters.get("Username")

    result_value = ca_manager.assign_incident_to_user(ticket_id, username)

    if result_value:
        output_message = f'Ticket with id "{ticket_id}" assigned to "{str(username).encode("utf-8")}"'
    else:
        output_message = f'Ticket with id "{ticket_id}" was not assigned to "{str(username).encode("utf-8")}"'

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
