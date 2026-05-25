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
from ..core.RSAArcherManager import RSAArcherManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("RSAArcher")
    server_address = conf["Api Root"]
    username = conf["Username"]
    password = conf["Password"]
    instance_name = conf["Instance Name"]
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    try:
        archer_manager = RSAArcherManager(
            server_address, username, password, instance_name, verify_ssl, siemplify.LOGGER
        )
        siemplify.end("Successfully connected to the RSA Archer.", True)
    except Exception as e:
        siemplify.end(f"Failed to connect to the RSA Archer. Error: {e}", False)


if __name__ == "__main__":
    main()


