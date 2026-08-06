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
from ..core.Area1Manager import Area1Manager
import time

ACTION_NAME = "Area1_Get Recent Indicators"
INDICATORS_TABLE_HEADER = "Recent Indicators"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    configurations = siemplify.get_configuration("Area1")
    server_addr = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]

    verify_ssl = configurations.get("Verify SSL", "false").lower() == "true"

    area1_manager = Area1Manager(server_addr, username, password, verify_ssl)

    # Send simple request to check connectivity.
    area1_manager.get_recent_indicators(since=int(time.time()) - 1)

    siemplify.end("Connection Established", True)


if __name__ == "__main__":
    main()
