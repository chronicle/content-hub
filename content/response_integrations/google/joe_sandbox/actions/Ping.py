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
from ..core.JoeSandboxManager import JoeSandboxManager
from soar_sdk.SiemplifyAction import SiemplifyAction


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "JoeSandbox - Detonate file"

    conf = siemplify.get_configuration("JoeSandbox")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf["Use SSL"].lower() == "true"
    joe = JoeSandboxManager(api_root, api_key, use_ssl)

    if joe.test_connectivity():
        output_message = "Connected successfully to JoeSandbox."
        result_value = "true"
    else:
        output_message = "Joe Sandbox is in maintenance mode. Please turn it on."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
