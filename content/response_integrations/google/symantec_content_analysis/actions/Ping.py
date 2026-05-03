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
from ..core.SymantecContentAnalysisManager import SymantecContentAnalysisManager

INTEGRATION_PROVIDER = "SymantecContentAnalysis"
ACTION_NAME = "SymantecContentAnalysis_Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)

    # CR: verify_ssl = conf.get('Verify SSL').lower() == 'true'
    verify_ssl = True if conf.get("Verify SSL").lower() == "true" else False
    symantec_manager = SymantecContentAnalysisManager(
        conf.get("API Root"), conf.get("API Key"), verify_ssl
    )

    connected = symantec_manager.ping()

    if connected:
        output_message = "Connection Established."
    else:
        output_message = "Connection Failed"

    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
