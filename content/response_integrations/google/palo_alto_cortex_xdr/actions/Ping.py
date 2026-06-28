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

from palo_alto_cortex_xdr.core.action_init import create_api_client
from palo_alto_cortex_xdr.core.constants import PING_ACTION_SCRIPT_NAME


def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = PING_ACTION_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    create_api_client(siemplify)

    output_message = "Successfully connected to Palo Alto Cortex XDR"
    result_value = "true"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
