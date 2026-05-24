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
from ..core.CiscoThreatGridManager import CiscoThreatGridManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "CiscoThreatGrid - GetSubmissions"

    conf = siemplify.get_configuration("CiscoThreatGrid")
    server_addr = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf["Use SSL"].lower() == "true"
    cisco_threat_grid = CiscoThreatGridManager(server_addr, api_key, use_ssl)

    cisco_threat_grid.test_connectivity()

    # If no exception occur - then connection is successful
    output_message = "Successfully connected to the Cisco Threat Grid."
    siemplify.end(output_message, True)



# Standard Ping Messages for Validator
# Successfully connected to the Cisco Threat Grid.
# Failed to connect to the Cisco Threat Grid.

if __name__ == "__main__":
    main()