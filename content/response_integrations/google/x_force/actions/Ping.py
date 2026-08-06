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
from ..core.XForceManager import XForceManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("XForce")
    address = conf["Address"]
    api_key = conf["Api Key"]
    api_password = conf["Api Password"]
    verify_ssl = conf["Verify SSL"].lower() == "true"
    xforce_manager = XForceManager(
        api_key, api_password, address, verify_ssl=verify_ssl
    )

    connectivity = xforce_manager.test_connectivity()
    output_message = "Connected Successfully"
    siemplify.end(output_message, connectivity)


if __name__ == "__main__":
    main()
