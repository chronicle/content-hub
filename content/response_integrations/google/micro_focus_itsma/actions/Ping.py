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

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

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

    result_value = itsma_manager.get_token()

    output_message = (
        "Successfully connected to the Micro Focus ITSMA server."
        if result_value
        else "Failed to connect to the Micro Focus ITSMA server."
    )

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
