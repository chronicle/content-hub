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

# Imports
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.ZendeskManager import ZendeskManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Zendesk")
    user_email = conf["User Email Address"]
    api_token = conf["Api Token"]
    server_address = conf["Server Address"]
    zendesk = ZendeskManager(user_email, api_token, server_address)

    # Execute Test Connectivity.
    result = zendesk.test_connectivity()

    if result:
        output_message = "Connection Established."
        result_value = "true"
    else:
        output_message = "Connection Failed."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
