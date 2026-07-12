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
from ..core.SymantecICDXManager import SymantecICDXManager


PROVIDER = "SymantecICDX"
ACTION_NAME = "SymantecICDX - Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    icdx_manager = SymantecICDXManager(
        api_root=conf.get("Api Root"),
        api_key=conf.get("Api Token"),
        verify_ssl=verify_ssl,
    )

    icdx_manager.test_connectivity()
    siemplify.end("Connection Established", True)


if __name__ == "__main__":
    main()
